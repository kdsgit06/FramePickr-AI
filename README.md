# FramePickr AI — Intelligent Frame Selection

**FramePickr AI** automatically scores and ranks photos to help photographers and editors pick the best frames quickly. It computes simple, explainable image metrics (sharpness, brightness, face count) and ranks images so you can pick the top frames from a batch in seconds.

---

## Why I built this
Photographers often shoot hundreds of images per session. Manually reviewing all of them is slow and error-prone. FramePickr applies a lightweight, deterministic scoring pipeline to highlight the best candidates — a useful time-saver during culls and quick-turn edits.

---

## Features
- Upload multiple images at once
- Compute per-image metrics: sharpness, brightness, face count
- Rank images by a combined score
- Save and serve top selected images
- Simple React UI for preview and download
- Safe defaults for remote deployment (compresses large uploads to avoid crashes)

---

## Tech stack
- **Frontend**: React (Vite), Axios
- **Backend**: FastAPI, Uvicorn
- **Image processing**: OpenCV, Pillow
- **Storage**: Local uploads folder (can swap to cloud storage)
- **Deploy**: Render / Vercel tested

---

## Quick start (local)

1. Clone:
```bash
git clone https://github.com/kdsgit06/FramePickr-AI.git
cd FramePickr-AI
Backend (Python):

bash
Copy code
cd backend
python -m venv .venv
# Activate the venv (PowerShell):
# .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
Frontend:

bash
Copy code
cd ../frontend
npm install
# optionally create .env with VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
Open http://localhost:5173 to use the UI.

Deploy notes
Backend: Render or similar; make sure the model/haarcascade_frontalface_default.xml is present or let the server download it on first run.

Frontend: Vercel or Netlify. Set VITE_API_BASE_URL to your backend URL in production.

Troubleshooting & tips
CORS errors: The backend includes permissive CORS for development. If you see No 'Access-Control-Allow-Origin' header, confirm the correct backend is called and the backend is deployed with the latest code.

502 / memory issues on Render: Large uploads can cause timeouts or memory spikes. Use small images for testing (under ~1MB), or raise instance size. The backend compresses large uploads before scoring to reduce risk.

No previews: Backend must return url for saved files. Confirm /uploads/<filename> returns 200 in the browser.

Next improvements (ideas)
Better face / expression detection (deep learning model)

Smart sampling for burst photos / video frame selection

Cloud storage (S3, Cloudinary) for saved images

User accounts & annotations

Contact
I built this as a practical demo of building a compact ML + web app pipeline. If you want to try improvements or help with UI polishing, open an issue or submit a PR.