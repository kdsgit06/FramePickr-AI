# backend/app.py
import os
import uuid
import traceback
from io import BytesIO
import zipfile

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import uvicorn
import cv2

# compression helper (Pillow)
from PIL import Image

# scoring function (expects compute_score(image_bytes, face_cascade, model_dir=...))
from model.scoring import compute_score

# downloader helper (downloads haarcascade xmls to model/ if needed)
from model.download_haarcascade import download_haarcascade

# -----------------------
# Config / paths
# -----------------------
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
CASCADE_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")  # project_root/uploads

# Create uploads dir
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# -----------------------
# Ensure Haarcascade files exist (face + optional others)
# -----------------------
if not os.path.exists(CASCADE_PATH):
    print("Haarcascade not found locally. Downloading now...", flush=True)
    try:
        download_haarcascade(dest_dir=MODEL_DIR)
    except Exception as e:
        print("Error downloading Haarcascade:", e, flush=True)
    if not os.path.exists(CASCADE_PATH):
        raise FileNotFoundError(f"Haarcascade not found and download failed. Expected at: {CASCADE_PATH}")

# Load face cascade (guard)
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise RuntimeError(f"Failed to load Haarcascade XML from {CASCADE_PATH}")

# -----------------------
# App
# -----------------------
app = FastAPI(title="FramePickr AI - Scoring API")

# CORS - open in dev; restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # during development only; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Utility helpers
# -----------------------
def compress_image_bytes_if_needed(image_bytes: bytes, max_kb: int = 700) -> bytes:
    """
    If image size (in KB) is larger than max_kb, compress by reducing JPEG quality.
    Returns bytes (possibly unchanged).
    """
    try:
        size_kb = len(image_bytes) / 1024
        if size_kb <= max_kb:
            return image_bytes

        # Load into Pillow and recompress progressively
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        # target reduce: keep decreasing quality until under max_kb or quality floor
        quality = 85
        while quality >= 30:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) / 1024 <= max_kb:
                return data
            quality -= 10
        # if we couldn't get smaller enough with reasonable quality, return last attempt
        return data
    except Exception:
        # on any compression error, fallback to original bytes
        return image_bytes

def safe_compute_score(image_bytes: bytes):
    """
    Wrap compute_score so exceptions are handled gracefully.
    """
    try:
        return compute_score(image_bytes, face_cascade, model_dir=MODEL_DIR)
    except Exception as e:
        # include traceback for dev logs, but return structured error for response
        traceback.print_exc()
        return {"error": "scoring_failed", "detail": str(e)}

def log_exception(e: Exception):
    traceback.print_exc()
    print("Exception:", e, flush=True)

# -----------------------
# Endpoints
# -----------------------
@app.post("/score")
async def score_images(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    """
    Score images (no saving). Returns count, top and all results.
    """
    results = []
    for f in files:
        contents = await f.read()
        # compress if large (avoid timeouts/502s)
        contents = compress_image_bytes_if_needed(contents, max_kb=700)
        res = safe_compute_score(contents)
        # attach original filename
        if isinstance(res, dict):
            res["filename"] = f.filename
        results.append(res)

    # sort by score when available
    scored = [r for r in results if isinstance(r, dict) and "score" in r]
    sorted_results = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]
    return JSONResponse({"count": len(results), "top": top, "all": results})


@app.post("/score_and_save")
async def score_and_save(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    """
    Scores uploaded images, saves top_n images to uploads/ and returns JSON
    with local file URLs and saved filenames (saved_as).
    """
    results = []
    file_bytes_list = []  # keep raw bytes to save later

    for f in files:
        contents = await f.read()
        # keep original raw bytes to save (we may save the original or compressed version)
        file_bytes_list.append((f.filename, contents))
        # compress for scoring (so scoring uses smaller image if needed)
        scoring_bytes = compress_image_bytes_if_needed(contents, max_kb=700)
        res = safe_compute_score(scoring_bytes)
        if isinstance(res, dict):
            res["filename"] = f.filename
        results.append(res)

    scored = [r for r in results if isinstance(r, dict) and "score" in r]
    sorted_results = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]

    # Save top images to uploads/ (use original bytes from file_bytes_list for better quality)
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
            log_exception(e)
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
    """
    Serves the saved files from uploads/ so the frontend can fetch them by URL.
    """
    path = os.path.join(UPLOADS_DIR, file_name)
    if not os.path.exists(path):
        return JSONResponse({"error": "file_not_found"}, status_code=404)
    return FileResponse(path)


@app.get("/download_saved")
async def download_saved(filenames: str = Query(..., description="Comma-separated saved filenames (example: uuid1.jpg,uuid2.jpg)")):
    """
    Example: GET /download_saved?filenames=aa.jpg,bb.jpg
    Bundles those files from uploads/ into a zip and returns streaming response.
    """
    try:
        names = [n.strip() for n in filenames.split(",") if n.strip()]
        if not names:
            raise HTTPException(status_code=400, detail="no_files_requested")

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in names:
                path = os.path.join(UPLOADS_DIR, fname)
                if not os.path.exists(path):
                    # skip missing file (could also return error)
                    continue
                # write with the saved filename as archive name
                zf.write(path, arcname=fname)
        buf.seek(0)
        headers = {
            "Content-Disposition": f"attachment; filename=framepickr_selected.zip"
        }
        return StreamingResponse(buf, media_type="application/zip", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        log_exception(e)
        raise HTTPException(status_code=500, detail="internal_server_error")


# -----------------------
# Run (dev)
# -----------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
