# backend/app.py
import os
import uuid
import traceback
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import cv2

from PIL import Image
from google.cloud import storage  # new

from model.scoring import compute_score
from model.download_haarcascade import download_haarcascade

# -----------------------
# Config
# -----------------------
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
LOCAL_CASCADE = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")

# GCS config
GCS_BUCKET = os.environ.get("GCS_BUCKET")  # required
GCS_BASE = os.environ.get("GCS_BASE_URL", "https://storage.googleapis.com")

if not GCS_BUCKET:
    raise RuntimeError("GCS_BUCKET environment variable not set")

# Ensure model dir exists
os.makedirs(MODEL_DIR, exist_ok=True)

# If local cascade missing, try your download helper (keeps your existing behavior)
if not os.path.exists(LOCAL_CASCADE):
    print("Local Haarcascade not found at", LOCAL_CASCADE, "— attempting download...", flush=True)
    try:
        download_haarcascade(dest_dir=MODEL_DIR)
    except Exception as e:
        print("download_haarcascade failed:", e, flush=True)

# Determine cascade path: prefer local model, otherwise fall back to OpenCV's builtin cascades
cascade_path_candidates = []
if os.path.exists(LOCAL_CASCADE):
    cascade_path_candidates.append(LOCAL_CASCADE)

# cv2.data.haarcascades is provided by the OpenCV wheel; try it next
try:
    opencv_builtin = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    cascade_path_candidates.append(opencv_builtin)
except Exception as e:
    print("cv2.data.haarcascades not available:", e, flush=True)

# Try each candidate until we get a non-empty CascadeClassifier
face_cascade = None
last_error = None
for p in cascade_path_candidates:
    try:
        print("Trying cascade:", p, flush=True)
        c = cv2.CascadeClassifier(p)
        if not c.empty():
            face_cascade = c
            print("Loaded cascade from:", p, flush=True)
            break
        else:
            print("Cascade at", p, "was empty.", flush=True)
    except Exception as e:
        last_error = e
        print("Error loading cascade at", p, ":", e, flush=True)

if face_cascade is None:
    # Final fallback: attempt to download again and try the local file once more
    try:
        print("Final attempt: download cascade to", MODEL_DIR, flush=True)
        download_haarcascade(dest_dir=MODEL_DIR)
        if os.path.exists(LOCAL_CASCADE):
            c = cv2.CascadeClassifier(LOCAL_CASCADE)
            if not c.empty():
                face_cascade = c
                print("Loaded cascade after download:", LOCAL_CASCADE, flush=True)
    except Exception as e:
        print("Final download attempt failed:", e, flush=True)

if face_cascade is None:
    # Clear, actionable runtime error
    raise RuntimeError(
        "Failed to load Haarcascade XML. Tried candidates: "
        + ", ".join(cascade_path_candidates)
        + (f". Last error: {last_error}" if last_error else "")
    )

# Initialize GCS client
gcs_client = storage.Client()
gcs_bucket = gcs_client.bucket(GCS_BUCKET)

app = FastAPI(title="FramePickr AI - Scoring API")

# CORS (open in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# helpers: compress + safe scoring
# -----------------------
def compress_image_bytes_if_needed(image_bytes: bytes, max_kb: int = 700) -> bytes:
    try:
        size_kb = len(image_bytes) / 1024
        if size_kb <= max_kb:
            return image_bytes
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        quality = 85
        last_data = image_bytes
        while quality >= 30:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            last_data = data
            if len(data) / 1024 <= max_kb:
                return data
            quality -= 10
        return last_data
    except Exception:
        return image_bytes

def safe_compute_score(image_bytes: bytes):
    try:
        return compute_score(image_bytes, face_cascade)
    except Exception as e:
        traceback.print_exc()
        return {"error": "scoring_failed", "detail": str(e)}

def upload_bytes_to_gcs(bytes_data: bytes, dest_name: str, content_type: str = "image/jpeg") -> str:
    blob = gcs_bucket.blob(dest_name)
    blob.upload_from_string(bytes_data, content_type=content_type)
    try:
        blob.make_public()
    except Exception as e:
        print("Warning: blob.make_public() failed:", e)
    public_url = f"{GCS_BASE.rstrip('/')}/{GCS_BUCKET}/{dest_name}"
    return public_url

# -----------------------
# Endpoints
# -----------------------
@app.post("/score_and_save")
async def score_and_save(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    results = []
    file_bytes_list = []

    # Step 1: read files and compute scores (possibly compressed for scoring)
    for f in files:
        contents = await f.read()
        file_bytes_list.append((f.filename, contents))
        scoring_bytes = compress_image_bytes_if_needed(contents, max_kb=700)
        res = safe_compute_score(scoring_bytes)
        if isinstance(res, dict):
            res["filename"] = f.filename
        results.append(res)

    # Step 2: sort by score
    scored = [r for r in results if isinstance(r, dict) and "score" in r]
    sorted_results = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]

    # Step 3: save top images to GCS and return absolute URLs
    saved = []
    for item in top:
        match = next((b for (name, b) in file_bytes_list if name == item.get("filename")), None)
        if match is None:
            continue
        ext = os.path.splitext(item.get("filename", ""))[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        try:
            public_url = upload_bytes_to_gcs(match, unique_name, content_type="image/jpeg")
        except Exception as e:
            traceback.print_exc()
            continue
        item["url"] = public_url
        saved.append({
            "filename": item.get("filename"),
            "saved_as": unique_name,
            "url": public_url,
            "score": item.get("score")
        })

    return JSONResponse({"count": len(results), "top": top, "all": results, "saved": saved})

# Keep the /score endpoint too if you need, similar to above but not saving.

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
