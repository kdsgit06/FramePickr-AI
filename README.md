# FramePickr AI 🎞️ -live : https://frame-pickr-ai.vercel.app/
> Upload a batch of photos → get the **best frames ranked automatically** using AI heuristics (sharpness, brightness, faces). Download full-resolution originals instantly.

---

## 🚀 Highlights
- 📸 **Automatic Photo Ranking** — scores images on sharpness, brightness, faces, eyes, smiles.  
- ⚡ **Smart Compression** — compresses for scoring to prevent backend overload.  
- 🗂️ **Originals Preserved** — always downloads full-quality files.  
- 🎨 **Elegant UI** — React + Vite frontend with gold/grey theme, rank badges, clear CTAs.  
- ☁️ **Deployable** — Vercel (frontend) + Cloud Run/Render (backend).  
- 🧰 **Portfolio-Ready** — full-stack, computer vision, deployment.

---

## 📖 Project Overview
Selecting the best shot out of hundreds of photos is tedious.  
**FramePickr AI** solves this by automatically ranking your uploaded images based on visual quality.

I built this project to:
- Learn **full-stack engineering** (React + FastAPI).  
- Implement **computer vision scoring** with OpenCV.  
- Practice **deployment workflows** (Vercel + Cloud Run).  
- Showcase my ability to debug real-world issues and ship a polished MVP.

👉 *Motivation:* I wanted a project that’s both **practical** and **resume-ready**, something a recruiter can try live in 30 seconds.

---

## 🖼️ Visual Demo
<!-- Add your screenshots/GIFs here -->
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/542ac77a-f172-4ddc-ad78-bffdb6fc6a4a" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/93bb1338-c927-487c-8f85-6d45830aee1f" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/1b793f76-8877-4c2d-8ff9-4871267d7a40" />

---

## 🛠️ Tech Stack
- **Frontend:** React + Vite, CSS (custom theme)  
- **Backend:** FastAPI (Python), Uvicorn  
- **Computer Vision:** OpenCV (sharpness, Haar cascades)  
- **Storage:** Local uploads / Google Cloud Storage  
- **Deployment:** Vercel (frontend), Docker + Cloud Run / Render (backend)

---

## ✨ Features
- Upload multiple images at once  
- Automatic scoring (sharpness, brightness, faces, eyes, smiles)  
- Top results displayed with **rank badges (#1, #2, …)**  
- Modal preview with Open / Download links  
- Downloads are always **original quality**  
- Elegant gold/grey UI with logo + CTA instructions  
---

## 🧑‍💻 Installation & Setup

### Prerequisites
- Node.js (>=18) + npm  
- Python 3.10+  
- Git  

### Backend (FastAPI)
```bash
# clone repo and enter backend folder
git clone https://github.com/yourusername/FramePickr-AI.git
cd FramePickr-AI/app

# create virtual env + install deps
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

# run server
uvicorn app.main:app --reload --port 8000
Backend runs at http://127.0.0.1:8000.

Frontend (React + Vite)
bash
Copy code
cd ../frontend
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
Frontend runs at http://127.0.0.1:5173.

📂 Usage
Open frontend in browser.

Select multiple images.

Click Upload & Score.

View ranked results (#1, #2, …).

Open or Download full-quality originals.

🐞 Key Challenges Solved
Bug: downloads were tiny (~150KB).
Fix: save original bytes, compress only for scoring.

Bug: CORS errors on Vercel.
Fix: configured CORSMiddleware with frontend origin.

Bug: syntax error (Unexpected token) in React.
Fix: closed braces correctly in App.jsx.

📊 Future Improvements
Replace Haar cascades with modern detectors (Mediapipe, RetinaFace).

Add ML model for photo aesthetics.

Add drag & drop upload.

Multi-user support with auth.

Track downloads/session metrics.

📜 License
MIT License — free to use and modify.

