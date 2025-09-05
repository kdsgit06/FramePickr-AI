import cv2
import numpy as np
from typing import Dict

def read_image(file_bytes: bytes):
    array = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    return img

def sharpness_score(img_bgr) -> float:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())

def brightness_score(img_bgr) -> float:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    return float(v.mean())

def face_count(img_bgr, cascade) -> int:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return int(len(faces))

def compute_score(file_bytes: bytes, face_cascade) -> Dict:
    img = read_image(file_bytes)
    if img is None:
        return {"error": "cannot_read_image", "score": 0}

    sharp = sharpness_score(img)
    bright = brightness_score(img)
    faces = face_count(img, face_cascade)

    # heuristic weighted sum
    score = 0.0
    score += min(sharp / 100.0, 3.0)   # sharpness contribution (max +3)
    if 80 <= bright <= 180:
        score += 1.0
    elif 50 <= bright < 80 or 180 < bright <= 220:
        score += 0.5
    score += faces * 1.0

    return {
        "score": round(float(score), 3),
        "sharpness": round(float(sharp), 3),
        "brightness": round(float(bright), 3),
        "faces": int(faces)
    }
