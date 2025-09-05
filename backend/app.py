from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import os
from model.scoring import compute_score
import cv2
import uuid

BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "model")
CASCADE_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")  # project_root/uploads

os.makedirs(UPLOADS_DIR, exist_ok=True)

if not os.path.exists(CASCADE_PATH):
    raise FileNotFoundError(f"Haarcascade not found. Please run model/download_haarcascade.py or place the xml at {CASCADE_PATH}")

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

app = FastAPI(title="FramePickr AI - Scoring API")

# allow local frontend (Vite) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # during development only; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """
    Scores uploaded images, saves the top_n images to uploads/ and returns JSON with local file URLs.
    """
    results = []
    file_bytes_list = []  # keep raw bytes to save later

    for f in files:
        contents = await f.read()
        file_bytes_list.append((f.filename, contents))
        res = compute_score(contents, face_cascade)
        res["filename"] = f.filename
        results.append(res)

    sorted_results = sorted([r for r in results if "score" in r], key=lambda x: x["score"], reverse=True)
    top = sorted_results[:top_n]

    # Save top images
    saved = []
    for item in top:
        # find raw bytes for this filename (first match)
        match = next((b for (name, b) in file_bytes_list if name == item["filename"]), None)
        if match is None:
            continue
        # unique filename to avoid collisions
        ext = os.path.splitext(item["filename"])[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOADS_DIR, unique_name)
        with open(save_path, "wb") as out:
            out.write(match)
        # create a relative URL path (for local dev)
        # e.g., /uploads/<filename> — we'll make a route to serve this
        item["url"] = f"/uploads/{unique_name}"
        saved.append({"filename": item["filename"], "saved_as": unique_name, "url": item["url"], "score": item["score"]})

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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
