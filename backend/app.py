from fastapi import FastAPI, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
import uvicorn
import os
from model.scoring import compute_score
import cv2
import uuid

# Import the downloader helper to fetch the Haarcascade on-demand
from model.download_haarcascade import download_haarcascade

BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
CASCADE_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")  # project_root/uploads

os.makedirs(UPLOADS_DIR, exist_ok=True)

# If cascade not present, download it
if not os.path.exists(CASCADE_PATH):
    print("Haarcascade not found locally. Downloading now...")
    try:
        download_haarcascade(dest_dir=MODEL_DIR)
    except Exception as e:
        print("Error downloading Haarcascade:", e)
    if not os.path.exists(CASCADE_PATH):
        raise FileNotFoundError(
            f"Haarcascade not found and download failed. Expected at: {CASCADE_PATH}"
        )

# Load cascade after ensuring it's present
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise RuntimeError(f"Failed to load Haarcascade XML from {CASCADE_PATH}")

app = FastAPI(title="FramePickr AI - Scoring API")

# Standard CORSMiddleware (keeps original behavior)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # development/demo: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback middleware: ensures Access-Control headers are always present
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    # Handle preflight OPTIONS early
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "*, Authorization, Content-Type",
        }
        return Response(status_code=200, headers=headers)

    response = await call_next(request)
    # Add CORS headers to every response as a fallback
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*, Authorization, Content-Type"
    return response

@app.post("/score")
async def score_images(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    results = []
    for f in files:
        contents = await f.read()
        res = compute_score(contents, face_cascade)
        res["filename"] = f.filename
        results.append(res)

    sorted_results = sorted([r for r in results if "score" in r], key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]
    return JSONResponse({"count": len(results), "top": top, "all": results})

@app.post("/score_and_save")
async def score_and_save(files: list[UploadFile] = File(...), top_n: int = Query(3, ge=1, le=20)):
    results = []
    file_bytes_list = []
    for f in files:
        contents = await f.read()
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

@app.get("/uploads/{file_name}")
async def serve_upload(file_name: str):
    path = os.path.join(UPLOADS_DIR, file_name)
    if not os.path.exists(path):
        return JSONResponse({"error": "file_not_found"}, status_code=404)
    return FileResponse(path)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
