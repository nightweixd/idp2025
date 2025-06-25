import cv2
import pickle
import requests
import numpy as np
from collections import deque, Counter
from insightface.app import FaceAnalysis
import time

# ─── Configuration ────────────────────────────────────────────────
ENCODINGS_PATH = "face_encodings_v2.pkl"
CAM_INDEX = 0
TOLERANCE = 0.5  # Lower = stricter matching
BUFFER_SIZE = 4  # Smoothing buffer size
WEBHOOK_URL = "https://webhook.site/9c5e82ec-4ecc-433b-a176-c56955ea74b0"
# ──────────────────────────────────────────────────────────────────

# Load InsightFace model on GPU
face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
face_app.prepare(ctx_id=0)

# Load saved face encodings
with open(ENCODINGS_PATH, "rb") as f:
    encoding_dict = pickle.load(f)

known_names, known_embeddings = [], []
for name, emb_list in encoding_dict.items():
    for emb in emb_list:
        known_names.append(name)
        known_embeddings.append(emb)
known_embeddings = np.array(known_embeddings)

# Recognition smoothing buffer
recognition_buffer = deque(maxlen=BUFFER_SIZE)

# Start video capture
cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect faces directly from full frame
    faces = face_app.get(frame)

    for face in faces:
        emb = face.embedding
        l, t, r, b = face.bbox.astype(int)

        name = "Unauthorized"
        color = (0, 0, 255)
        similarity = 0

        if known_embeddings.shape[0] > 0:
            sims = np.dot(known_embeddings, emb) / (np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(emb))
            best_idx = np.argmax(sims)
            similarity = sims[best_idx]
            if similarity > 1 - TOLERANCE:
                name = known_names[best_idx]
                color = (0, 255, 0)

        recognition_buffer.append(name)
        top_name = Counter(recognition_buffer).most_common(1)[0][0]

        # Draw face bounding box and label
        cv2.rectangle(frame, (l, t), (r, b), color, 2)
        label = f"{name}" if name == "Unauthorized" else f"{name} ({similarity:.2f})"
        cv2.putText(frame, label, (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Send webhook for unauthorized detection
        if name == "Unauthorized":
            try:
                flipped_top = frame.shape[0] - b
                flipped_bottom = frame.shape[0] - t
                requests.post(WEBHOOK_URL, json={
                    "detection_type": "unauthorised",
                    "confidence": float(similarity),
                    "coordinates": [int(l), int(flipped_top), int(r), int(flipped_bottom)]
                }, timeout=1)
            except Exception as e:
                print(f"[!] Webhook failed: {e}")

    # FPS display
    frame_count += 1
    elapsed = time.time() - start_time
    fps_display = frame_count / elapsed if elapsed > 0 else 0
    cv2.putText(frame, f"FPS: {fps_display:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)

    cv2.imshow("Face Recognition Only (InsightFace)", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Real-time face-only recognition finished.")
