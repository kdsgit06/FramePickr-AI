# backend/model/scoring.py
import cv2
import numpy as np
from io import BytesIO

# thresholds / weights (tune later)
SHARPNESS_WEIGHT = 1.0
BRIGHTNESS_WEIGHT = 0.005
FACES_WEIGHT = 1.0
EYES_OPEN_WEIGHT = 1.5
SMILE_WEIGHT = 2.0

# keep these filenames relative to backend/model/
EYE_CASCADE = "haarcascade_eye.xml"
SMILE_CASCADE = "haarcascade_smile.xml"

def _load_cascade(path):
    c = cv2.CascadeClassifier(path)
    if c.empty():
        raise RuntimeError(f"Failed to load cascade: {path}")
    return c

def compute_sharpness(gray):
    # variance of Laplacian
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())

def compute_brightness(img):
    # brightness as mean of grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))

def detect_faces_and_features(img, face_cascade, model_dir):
    """
    Returns:
      faces: list of (x,y,w,h)
      eyes_open_count: integer approximate count of eyes open across faces
      smile_count: integer approximate number of smiles detected
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))

    # load cascades for eyes and smile (per call is fine; caching possible)
    eye_path = f"{model_dir}/{EYE_CASCADE}"
    smile_path = f"{model_dir}/{SMILE_CASCADE}"
    eye_cascade = _load_cascade(eye_path)
    smile_cascade = _load_cascade(smile_path)

    eyes_open = 0
    smiles = 0

    for (x, y, w, h) in faces:
        # region-of-interest for the face
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = img[y:y+h, x:x+w]

        # eyes detection (two eyes -> more confident open)
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(10,10))
        # simple heuristic: if eyes found inside face region, count them
        eyes_open += len(eyes)

        # smile detection — note: cascade smile is noisy; tune minNeighbors
        smiles_found = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.7, minNeighbors=22, minSize=(15,15))
        smiles += len(smiles_found)

    return list(faces), eyes_open, smiles

def compute_score(image_bytes, face_cascade, model_dir=None):
    """
    image_bytes: raw bytes of JPEG/PNG
    face_cascade: cv2.CascadeClassifier for faces
    model_dir: path to model directory (so we can load eye/smile cascades)
    returns dict with score, breakdown
    """
    if model_dir is None:
        # assume cascade in project structure: backend/model
        import os
        model_dir = os.path.join(os.path.dirname(__file__))

    # decode
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "cannot_decode_image"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    sharpness = compute_sharpness(gray)  # bigger is sharper
    brightness = compute_brightness(img) # mean brightness

    # faces + eyes + smiles
    faces, eyes_open, smiles = detect_faces_and_features(img, face_cascade, model_dir)

    # Normalize / combine to a single score with weights
    # Note: scales differ; normalize using simple heuristics.
    norm_sharp = sharpness / (sharpness + 50.0)  # smooth fraction
    norm_brightness = 1.0 / (1.0 + np.exp(-0.02*(brightness-100)))  # sigmoid around 100
    face_count = len(faces)

    score = 0.0
    # base components
    score += SHARPNESS_WEIGHT * norm_sharp
    score += BRIGHTNESS_WEIGHT * norm_brightness * 100.0  # scale back
    score += FACES_WEIGHT * face_count
    # expression bonuses
    score += EYES_OPEN_WEIGHT * (eyes_open / 2.0)  # two eyes per face roughly
    score += SMILE_WEIGHT * smiles

    # return readable floats
    return {
        "score": round(float(score), 3),
        "sharpness": round(float(sharpness), 3),
        "brightness": round(float(brightness), 3),
        "faces": face_count,
        "eyes_open": int(eyes_open),
        "smiles": int(smiles),
    }
