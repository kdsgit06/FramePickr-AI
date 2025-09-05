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

app = FastAPI(title="FramePickr AI - Scoring API (defensive)")

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

# --- small helpers ---
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit per file (adjust if needed)

def log_exception(e: Exception):
    # print full traceback to stdout so Render logs show it
    print("Exception:", str(e), file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

# endpoints
@app.post("/score")
async def score_images(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    try:
        results = []
        for f in files:
            contents = await f.read()
            if len(contents) > MAX_UPLOAD_BYTES:
                return JSONResponse({"error": "file_too_large", "detail": f"{f.filename} exceeds {MAX_UPLOAD_BYTES} bytes"}, status_code=413)
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
    """
    Defensive: validate sizes, log exceptions, return helpful error messages.
    """
    try:
        results = []
        file_bytes_list = []

        for f in files:
            contents = await f.read()
            if len(contents) > MAX_UPLOAD_BYTES:
                return JSONResponse({"error": "file_too_large", "detail": f"{f.filename} exceeds {MAX_UPLOAD_BYTES} bytes"}, status_code=413)
            file_bytes_list.append((f.filename, contents))
            # compute_score may raise — we'll catch below
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
        # include short message but avoid leaking internals
        return JSONResponse({"error": "internal_server_error", "detail": str(e)}, status_code=500)

@app.get("/uploads/{file_name}")
async def serve_upload(file_name: str):
    try:
        path = os.path.join(UPLOADS_DIR, file_name)
        if not os.path.exists(path):
            return JSONResponse({"error": "file_not_found"}, status_code=404)
        # FileResponse will be returned; middleware will attach CORS headers
        return FileResponse(path)
    except Exception as e:
        log_exception(e)
        return JSONResponse({"error": "internal_server_error"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
