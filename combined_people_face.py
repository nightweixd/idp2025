import cv2
import pickle
import requests
import numpy as np
from collections import deque, Counter
from ultralytics import YOLO
from insightface.app import FaceAnalysis
import time

# --- Configuration ---
YOLO_MODEL_PATH = "yolov8n.pt"
ENCODINGS_PATH = "face_encodings_v2.pkl"
CAM_INDEX = 0
TOLERANCE = 0.45
YOLO_CONFIDENCE = 0.7
BUFFER_SIZE = 5
WEBHOOK_URL = "https://webhook.site/9c5e82ec-4ecc-433b-a176-c56955ea74b0"
FACE_INTERVAL = 2
PEOPLE_INTERVAL = 1
# ----------------------

# Load YOLOv8
yolo = YOLO(YOLO_MODEL_PATH)
yolo.to("cuda")

# Load InsightFace
face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
face_app.prepare(ctx_id=0)

# Load encodings
with open(ENCODINGS_PATH, "rb") as f:
    encoding_dict = pickle.load(f)

known_names, known_embeddings = [], []
for name, emb_list in encoding_dict.items():
    for emb in emb_list:
        known_names.append(name)
        known_embeddings.append(emb)
known_embeddings = np.array(known_embeddings)

recognition_buffer = deque(maxlen=BUFFER_SIZE)
cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Time trackers
last_face_sent = 0
last_people_sent = 0
frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = yolo(frame, classes=[0], conf=YOLO_CONFIDENCE)
    people_count = 0

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        people_count += 1

        person_roi = frame[y1:y2, x1:x2]
        faces = face_app.get(person_roi)

        for face in faces:
            emb = face.embedding
            l, t, r, b = face.bbox.astype(int)
            l += x1
            r += x1
            t += y1
            b += y1

            name = "Unauthorized"
            color = (0, 0, 255)
            sim = 0

            if known_embeddings.shape[0] > 0:
                sims = np.dot(known_embeddings, emb) / (
                    np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(emb)
                )
                idx = int(np.argmax(sims))
                sim = float(sims[idx])
                if sim > 1 - TOLERANCE:
                    name = known_names[idx]
                    color = (0, 255, 0)

            recognition_buffer.append(name)
            top_name = Counter(recognition_buffer).most_common(1)[0][0]

            # Draw
            cv2.rectangle(frame, (l, t), (r, b), color, 2)
            label = f"{name} ({sim:.2f})" if name != "Unauthorized" else name
            cv2.putText(frame, label, (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # Webhook for unauthorized only
            now = time.time()
            if name == "Unauthorized" and now - last_face_sent > FACE_INTERVAL:
                flipped_top = int(frame_height - b)
                flipped_bottom = int(frame_height - t)
                payload = {
                    "detection_type": "unauthorised",
                    "confidence": sim,
                    "coordinates": [int(l), flipped_top, int(r), flipped_bottom]
                }
                try:
                    requests.post(WEBHOOK_URL, json=payload, timeout=1)
                    last_face_sent = now
                except Exception as e:
                    print(f"[!] Webhook failed: {e}")

    # Webhook for people count
    now = time.time()
    if now - last_people_sent > PEOPLE_INTERVAL:
        try:
            requests.post(WEBHOOK_URL, json={
                "detection_type": "person",
                "count": int(people_count)
            }, timeout=1)
            last_people_sent = now
        except Exception as e:
            print(f"[!] People count webhook failed: {e}")

    # Show FPS
    frame_count += 1
    elapsed = time.time() - start_time
    fps = frame_count / elapsed if elapsed > 0 else 0
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)

    cv2.imshow("People + Face Surveillance", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Monitoring session ended.")
