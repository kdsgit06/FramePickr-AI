# backend/app.py
import os
import uuid
import traceback
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import cv2
from PIL import Image

from model.scoring import compute_score
from model.download_haarcascade import download_haarcascade

# ------- paths -------
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
CASCADE_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")  # project_root/uploads

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ------- ensure cascade -------
if not os.path.exists(CASCADE_PATH):
    print("Haarcascade not found locally. Downloading now...", flush=True)
    try:
        download_haarcascade(dest_dir=MODEL_DIR)
    except Exception as e:
        print("Error downloading Haarcascade:", e, flush=True)
    if not os.path.exists(CASCADE_PATH):
        raise FileNotFoundError(f"Haarcascade not found and download failed. Expected at: {CASCADE_PATH}")

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise RuntimeError(f"Failed to load Haarcascade XML from {CASCADE_PATH}")

# ------- app -------
app = FastAPI(title="FramePickr AI - Scoring API")

# DEV: open CORS for local/frontend testing. Restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------- helpers -------
def compress_image_bytes_if_needed(image_bytes: bytes, max_kb: int = 700) -> bytes:
    """
    If image size (in KB) is larger than max_kb, compress by lowering JPEG quality.
    Returns bytes (possibly unchanged).
    """
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
        # on any error, fallback to original bytes
        return image_bytes

def safe_compute_score(image_bytes: bytes):
    """
    Wrap compute_score and return structured error if something goes wrong.
    IMPORTANT: compute_score signature expected: compute_score(image_bytes, face_cascade)
    """
    try:
        return compute_score(image_bytes, face_cascade)
    except Exception as e:
        traceback.print_exc()
        return {"error": "scoring_failed", "detail": str(e)}

# ------- endpoints -------
@app.post("/score")
async def score_images(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    results = []
    for f in files:
        contents = await f.read()
        # compress for scoring to avoid timeouts/memory spikes
        scoring_bytes = compress_image_bytes_if_needed(contents, max_kb=700)
        res = safe_compute_score(scoring_bytes)
        if isinstance(res, dict):
            res["filename"] = f.filename
        results.append(res)

    scored = [r for r in results if isinstance(r, dict) and "score" in r]
    sorted_results = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]
    return JSONResponse({"count": len(results), "top": top, "all": results})


@app.post("/score_and_save")
async def score_and_save(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    results = []
    file_bytes_list = []  # keep raw bytes to save later

    for f in files:
        contents = await f.read()
        file_bytes_list.append((f.filename, contents))
        scoring_bytes = compress_image_bytes_if_needed(contents, max_kb=700)
        res = safe_compute_score(scoring_bytes)
        if isinstance(res, dict):
            res["filename"] = f.filename
        results.append(res)

    scored = [r for r in results if isinstance(r, dict) and "score" in r]
    sorted_results = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]

    # Save top images (use original bytes for best quality)
    saved = []
    for item in top:
        match = next((b for (name, b) in file_bytes_list if name == item.get("filename")), None)
        if match is None:
            continue
        ext = os.path.splitext(item.get("filename", ""))[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOADS_DIR, unique_name)
        try:
            with open(save_path, "wb") as out:
                out.write(match)
        except Exception as e:
            traceback.print_exc()
            continue
        item["url"] = f"/uploads/{unique_name}"
        saved.append({
            "filename": item.get("filename"),
            "saved_as": unique_name,
            "url": item["url"],
            "score": item.get("score")
        })

    return JSONResponse({"count": len(results), "top": top, "all": results, "saved": saved})


@app.get("/uploads/{file_name}")
async def serve_upload(file_name: str):
    path = os.path.join(UPLOADS_DIR, file_name)
    if not os.path.exists(path):
        return JSONResponse({"error": "file_not_found"}, status_code=404)
    return FileResponse(path)

# dev runner
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
