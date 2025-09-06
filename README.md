# 📸 FramePickr AI

**FramePickr AI** is an AI-powered photo selection tool that automatically **scores, ranks, and saves the best frames** from a batch of images.  
It uses **OpenCV** for scoring (sharpness, brightness, face/eyes/smile detection) and integrates with **Google Cloud Storage** for persistent uploads.  

🚀 **Live Demo:** [https://frame-pickr-ai.vercel.app](https://frame-pickr-ai.vercel.app)  

---

## ✨ Features
- 📂 Upload multiple images at once (drag & drop or file picker)  
- ⚡ AI-based scoring for:
  - Sharpness
  - Brightness
  - Face detection
  - Eye & smile detection  
- 🔝 Automatically selects **top-N ranked images**  
- ☁️ Saves best picks to **Google Cloud Storage** and returns public URLs  
- 🎨 Minimal, dark-themed UI with responsive design  
- 🌍 Full-stack deployment:
  - **Backend:** FastAPI + Uvicorn → Google Cloud Run
  - **Frontend:** React + Vite → Vercel  

---

## 🛠️ Tech Stack
**Frontend:** React (Vite), Custom CSS  
**Backend:** FastAPI (Python), OpenCV, Pillow  
**Storage:** Google Cloud Storage  
**Deployment:** Cloud Run (backend), Vercel (frontend)  

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/FramePickr-AI.git
cd FramePickr-AI
2. Backend Setup
bash
Copy code
cd backend
pip install -r requirements.txt

# Run locally
uvicorn app:app --reload --port 8000
Environment variables required:

bash
Copy code
GCS_BUCKET=<your-bucket-name>
GCS_BASE_URL=https://storage.googleapis.com
3. Frontend Setup
bash
Copy code
cd frontend
npm install
npm run dev
Set .env file:

ini
Copy code
VITE_API_BASE_URL=https://<your-cloud-run-service-url>
4. Deployment
Backend → Google Cloud Build + Cloud Run

Frontend → Vercel (VITE_API_BASE_URL must be set in Vercel Environment Variables)

📷 Screenshots
Add screenshots of your app here for better presentation (upload to docs/screenshots/).

📌 Roadmap
 Drag-and-drop upload UI

 Advanced scoring breakdown (histograms, exposure)

 Authentication for user-specific uploads

 Batch export of top results

🧑‍💻 Author
Built with ❤️ by Subhash K