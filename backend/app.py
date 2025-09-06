# backend/app.py
import os
import uuid
import traceback
from io import BytesIO
from pathlib import Path
import requests
import time

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import cv2
from PIL import Image

# optional: only import google storage if available / GCS configured
try:
    from google.cloud import storage
    _GCS_AVAILABLE = True
except Exception:
    _GCS_AVAILABLE = False

# -----------------------
# Config
# -----------------------
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Which cascade files we need in the model dir
REQUIRED_CASCADES = {
    "face": "haarcascade_frontalface_default.xml",
    "eye": "haarcascade_eye.xml",
    "smile": "haarcascade_smile.xml",
}

# GCS config (from environment)
GCS_BUCKET = os.environ.get("GCS_BUCKET")  # optional now
GCS_BASE = os.environ.get("GCS_BASE_URL", "https://storage.googleapis.com")

# -----------------------
# Helpers: download cascade if missing
# -----------------------
# Raw file URLs for OpenCV cascades (raw from GitHub). These are small XML files.
OPENCV_CASCADE_RAW_BASE = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades"

def download_cascade_if_missing(filename: str, dest_dir: Path, tries: int = 3):
    dest = dest_dir / filename
    if dest.exists() and dest.stat().st_size > 0:
        print(f"{filename} already exists at {dest}", flush=True)
        return True

    url = f"{OPENCV_CASCADE_RAW_BASE}/{filename}"
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            print(f"Downloading cascade {filename} (attempt {attempt}) from {url}", flush=True)
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and resp.content:
                dest.write_bytes(resp.content)
                print(f"Saved cascade to {dest}", flush=True)
                return True
            else:
                last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = e
        time.sleep(1)
    print(f"Failed to download {filename}: {last_err}", flush=True)
    return False

# Ensure required cascades present
for name, fname in REQUIRED_CASCADES.items():
    if not download_cascade_if_missing(fname, MODEL_DIR):
        print(f"Warning: Could not ensure cascade {fname}. Some features may fail.", flush=True)

# -----------------------
# Load cascades (prefer packaged files)
# -----------------------
cascade_path_candidates = []
# local model dir
for fname in REQUIRED_CASCADES.values():
    p = str(MODEL_DIR / fname)
    if Path(p).exists():
        cascade_path_candidates.append(p)

# try cv2 builtins as fallback
try:
    builtin_dir = cv2.data.haarcascades
    for fname in REQUIRED_CASCADES.values():
        p = os.path.join(builtin_dir, fname)
        cascade_path_candidates.append(p)
except Exception as e:
    print("cv2.data.haarcascades not available:", e, flush=True)

# load each cascade into a dict
cascades = {}
for key, fname in REQUIRED_CASCADES.items():
    loaded = None
    last_err = None
    for candidate in cascade_path_candidates:
        # candidate might be the exact file or other names; match by file name
        if candidate.endswith(fname):
            try:
                c = cv2.CascadeClassifier(candidate)
                if not c.empty():
                    loaded = c
                    print(f"Loaded {fname} from {candidate}", flush=True)
                    break
                else:
                    print(f"Cascade at {candidate} was empty", flush=True)
            except Exception as e:
                last_err = e
    if loaded is None:
        print(f"ERROR: Could not load cascade {fname}. Last error: {last_err}", flush=True)
    cascades[key] = loaded

# If face cascade missing, abort early (we can't score without face detection)
if cascades.get("face") is None:
    raise RuntimeError("Failed to load face Haarcascade. Cannot continue. Check model files in /app/model.")

# -----------------------
# GCS client (optional)
# -----------------------
gcs_client = None
gcs_bucket = None
if GCS_BUCKET:
    if not _GCS_AVAILABLE:
        print("google-cloud-storage library not available; GCS upload disabled", flush=True)
        GCS_BUCKET = None
    else:
        try:
            gcs_client = storage.Client()
            gcs_bucket = gcs_client.bucket(GCS_BUCKET)
            # don't assume public by default
            print(f"GCS client initialized for bucket: {GCS_BUCKET}", flush=True)
        except Exception as e:
            print("Failed to initialize GCS client:", e, flush=True)
            gcs_client = None
            gcs_bucket = None
else:
    print("GCS_BUCKET not set. Uploads to GCS will be disabled.", flush=True)

# -----------------------
# Application
# -----------------------
app = FastAPI(title="FramePickr AI - Scoring API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Scoring implementation import (if you have a separate module)
# If your project already has model/scoring.py with compute_score(image_bytes, face_cascade),
# we will import it; otherwise we will provide a simple fallback compute_score that returns basic info.
# -----------------------
try:
    from model.scoring import compute_score  # your existing scoring
except Exception as e:
    print("Could not import model.scoring; using fallback compute_score:", e, flush=True)

    def compute_score(image_bytes: bytes, face_cascade):
        # fallback: detect face count and return as score
        nparr = np.frombuffer(image_bytes, dtype="uint8")
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "invalid_image"}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
        score = float(len(faces))
        return {"score": score, "faces": int(len(faces))}

# -----------------------
# helpers: compress + safe scoring + upload
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
        return compute_score(image_bytes, cascades.get("face"))
    except Exception as e:
        traceback.print_exc()
        return {"error": "scoring_failed", "detail": str(e)}

def upload_bytes_to_gcs(bytes_data: bytes, dest_name: str, content_type: str = "image/jpeg") -> str:
    if gcs_bucket is None:
        raise RuntimeError("GCS bucket not configured or client not initialized")
    blob = gcs_bucket.blob(dest_name)
    blob.upload_from_string(bytes_data, content_type=content_type)
    # attempt to make public (may fail under uniform bucket-level access)
    try:
        blob.make_public()
    except Exception as e:
        print("Warning: blob.make_public() failed:", e, flush=True)
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

    # Step 3: save top images to GCS and return absolute URLs (if configured)
    saved = []
    for item in top:
        match = next((b for (name, b) in file_bytes_list if name == item.get("filename")), None)
        if match is None:
            continue
        ext = os.path.splitext(item.get("filename", ""))[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        public_url = None
        try:
            if gcs_bucket is not None:
                public_url = upload_bytes_to_gcs(match, unique_name, content_type="image/jpeg")
            else:
                print("Skipping upload: GCS not configured", flush=True)
        except Exception as e:
            traceback.print_exc()
            public_url = None
        item["url"] = public_url
        saved.append({
            "filename": item.get("filename"),
            "saved_as": unique_name if public_url else None,
            "url": public_url,
            "score": item.get("score")
        })

    return JSONResponse({"count": len(results), "top": top, "all": results, "saved": saved})

# -----------------------
# Run (for local dev)
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
