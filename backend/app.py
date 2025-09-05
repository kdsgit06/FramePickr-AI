import os
import uuid
import traceback
import sys
from fastapi import FastAPI, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
import uvicorn
from model.scoring import compute_score
import cv2

# new imports for compression
from io import BytesIO
from PIL import Image

# downloader helper
from model.download_haarcascade import download_haarcascade

BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
CASCADE_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")  # project_root/uploads

os.makedirs(UPLOADS_DIR, exist_ok=True)

# ensure cascade is available
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

app = FastAPI(title="FramePickr AI - Scoring API (defensive + compress)")

# standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fallback middleware to ensure CORS headers always present
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "*, Authorization, Content-Type",
        }
        return Response(status_code=200, headers=headers)
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    return response

# --- helpers ---
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit per file (hard limit)
TARGET_BYTES = int(1.5 * 1024 * 1024)  # compress to ~1.5 MB target if bigger
MAX_WIDTH = 2048  # if image is wider than this, resize proportionally

def log_exception(e: Exception):
    print("Exception:", str(e), file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

def compress_image_bytes(img_bytes: bytes, target_bytes: int = TARGET_BYTES, max_width: int = MAX_WIDTH) -> bytes:
    """
    Compress image bytes using Pillow:
      - open bytes, convert to RGB (if needed),
      - if width > max_width, resize proportionally,
      - save as JPEG with decreasing quality until under target_bytes or quality reaches 30.
    Returns compressed bytes (or original if compression not needed/failed).
    """
    try:
        # quick check: if already small, return as-is
        if len(img_bytes) <= target_bytes:
            return img_bytes

        im = Image.open(BytesIO(img_bytes))
        # convert to RGB to guarantee JPEG compatibility
        if im.mode in ("RGBA", "LA"):
            # drop alpha or convert to white background
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.split()[-1])
            im = background
        else:
            im = im.convert("RGB")

        # resize if very wide
        w, h = im.size
        if w > max_width:
            new_h = int(max_width * (h / w))
            im = im.resize((max_width, new_h), Image.LANCZOS)

        # try quality loop
        quality = 85
        while quality >= 30:
            bio = BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            data = bio.getvalue()
            if len(data) <= target_bytes:
                return data
            quality -= 10

        # if we exit loop, return best we have (last attempt)
        return data
    except Exception as e:
        # if compression fails, log and return original bytes so scoring still runs
        print("Compression failed:", e, file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return img_bytes

# endpoints (defensive)
@app.post("/score")
async def score_images(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    try:
        results = []
        for f in files:
            contents = await f.read()
            # if file too large to accept at all, reject
            if len(contents) > (3 * MAX_UPLOAD_BYTES):
                return JSONResponse({"error": "file_too_large", "detail": f"{f.filename} exceeds absolute limit"}, status_code=413)

            # compress if bigger than target threshold
            if len(contents) > TARGET_BYTES:
                contents = compress_image_bytes(contents)

            # still reject if it's larger than hard limit after compression
            if len(contents) > MAX_UPLOAD_BYTES:
                return JSONResponse({"error": "file_too_large_after_compression", "detail": f"{f.filename} too large"}, status_code=413)

            res = compute_score(contents, face_cascade)
            res["filename"] = f.filename
            results.append(res)

        sorted_results = sorted([r for r in results if "score" in r], key=lambda x: x["score"], reverse=True)
        top = sorted_results[:top_n]
        return JSONResponse({"count": len(results), "top": top, "all": results})
    except Exception as e:
        log_exception(e)
        return JSONResponse({"error": "internal_server_error", "detail": str(e)}, status_code=500)

@app.post("/score_and_save")
async def score_and_save(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    try:
        results = []
        file_bytes_list = []

        for f in files:
            contents = await f.read()
            # absolute reject for massive files
            if len(contents) > (3 * MAX_UPLOAD_BYTES):
                return JSONResponse({"error": "file_too_large", "detail": f"{f.filename} exceeds absolute limit"}, status_code=413)

            # compress if bigger than target
            if len(contents) > TARGET_BYTES:
                contents = compress_image_bytes(contents)

            # reject if still too big
            if len(contents) > MAX_UPLOAD_BYTES:
                return JSONResponse({"error": "file_too_large_after_compression", "detail": f"{f.filename} too large"}, status_code=413)

            file_bytes_list.append((f.filename, contents))
            res = compute_score(contents, face_cascade)
            res["filename"] = f.filename
            results.append(res)

        sorted_results = sorted([r for r in results if "score" in r], key=lambda x: x["score"], reverse=True)
        top = sorted_results[:top_n]

        saved = []
        for item in top:
            match = next((b for (name, b) in file_bytes_list if name == item["filename"]), None)
            if match is None:
                continue
            ext = os.path.splitext(item["filename"])[1] or ".jpg"
            unique_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(UPLOADS_DIR, unique_name)
            with open(save_path, "wb") as out:
                out.write(match)
            item["url"] = f"/uploads/{unique_name}"
            saved.append({"filename": item["filename"], "saved_as": unique_name, "url": item["url"], "score": item["score"]})

        return JSONResponse({"count": len(results), "top": top, "all": results, "saved": saved})
    except Exception as e:
        log_exception(e)
        return JSONResponse({"error": "internal_server_error", "detail": str(e)}, status_code=500)

@app.get("/uploads/{file_name}")
async def serve_upload(file_name: str):
    try:
        path = os.path.join(UPLOADS_DIR, file_name)
        if not os.path.exists(path):
            return JSONResponse({"error": "file_not_found"}, status_code=404)
        return FileResponse(path)
    except Exception as e:
        log_exception(e)
        return JSONResponse({"error": "internal_server_error"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
