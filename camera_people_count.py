import cv2
import time
import requests
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import torch

# ─── Configuration ───────────────────────────────────────────
MODEL_WEIGHTS = "runs/detect/train2/weights/best.pt"  # Your trained model path
USE_CAMERA     = True
OUTPUT_PATH    = None  # Optional: set to path like "output.mp4" to save video
WEBHOOK_URL    = "https://webhook.site/9c5e82ec-4ecc-433b-a176-c56955ea74b0"
WEBHOOK_INTERVAL = 5.0  # seconds between webhook sends
RESIZE_WIDTH   = 1280
CONF_THRESHOLD = 0.5
# ─────────────────────────────────────────────────────────────

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[✓] Running on {device.upper()}")

# Load YOLO model
model = YOLO(MODEL_WEIGHTS)

# DeepSort tracker
tracker = DeepSort(
    max_age=15,
    n_init=5,
    max_iou_distance=0.6,
    embedder="mobilenet",
    half=True,
    bgr=True,
    embedder_gpu=True,
)

# Webhook cooldown
last_webhook_time = 0
def send_people_count(count):
    global last_webhook_time
    now = time.time()
    if now - last_webhook_time < WEBHOOK_INTERVAL:
        return
    payload = {
        "detection_type": "person",
        "count": count
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=0.5)
        last_webhook_time = now
    except Exception as e:
        print(f"[!] Webhook send failed: {e}")

# Open webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Could not open camera")

orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS) or 30
scale = RESIZE_WIDTH / orig_w
resized_h = int(orig_h * scale)

# Optional output writer
if OUTPUT_PATH:
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (RESIZE_WIDTH, resized_h))

frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_resized = cv2.resize(frame, (RESIZE_WIDTH, resized_h))
    results = model(frame_resized, verbose=False)

    detections = []
    for r in results:
        for box in r.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            conf = float(box.conf[0])

            if class_name == "person" and conf > CONF_THRESHOLD:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w, h = x2 - x1, y2 - y1
                if w < 30 or h < 60:
                    continue
                detections.append(([x1, y1, w, h], conf, class_name))

    # DeepSort tracking
    tracks = tracker.update_tracks(detections, frame=frame_resized)
    person_count = 0

    for track in tracks:
        if not track.is_confirmed():
            continue
        l, t, r, b = map(int, track.to_ltrb())
        track_id = track.track_id
        person_count += 1

        cv2.rectangle(frame_resized, (l, t), (r, b), (255, 0, 0), 2)
        cv2.putText(frame_resized, f"ID: {track_id}", (l, t - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Show count and FPS
    elapsed = time.time() - start_time
    fps_display = frame_count / elapsed if elapsed > 0 else 0
    cv2.putText(frame_resized, f'People: {person_count}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(frame_resized, f'FPS: {fps_display:.1f}', (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    send_people_count(person_count)

    if OUTPUT_PATH:
        out.write(frame_resized)

    cv2.imshow("Real-time Person Tracker", frame_resized)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    frame_count += 1

# Cleanup
cap.release()
if OUTPUT_PATH:
    out.release()
cv2.destroyAllWindows()
print("[✓] Finished.")
