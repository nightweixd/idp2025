import cv2
import requests
import numpy as np
import time
from ultralytics import YOLO

# ─── Configuration ───────────────────────────────────────────
OUTPUT_VIDEO     = r"C:\Users\fongj\OneDrive\Desktop\idp\blood_output_cam.mp4"
WEBHOOK_URL      = "https://webhook.site/9c5e82ec-4ecc-433b-a176-c56955ea74b0"
MODEL_PATH       = r"C:\Users\fongj\OneDrive\Desktop\idp\runs\detect\stain_detection_v162\weights\best.pt"
WEBHOOK_INTERVAL = 5.0
DOWNSCALE_WIDTH  = 1280
CONF_THRESHOLD   = 0.4  # keep this balanced
IOU_THRESHOLD    = 0.4
MIN_AREA         = 200  # allow very small stains (~14x14 pixels)
MAX_AREA         = 8000  # skip massive boxes if needed
# ─────────────────────────────────────────────────────────────

last_webhook = 0
def send_webhook(event, conf, coords):
    global last_webhook
    now = time.time()
    if now - last_webhook < WEBHOOK_INTERVAL:
        return
    payload = {
        "detection_type": event,
        "confidence": float(conf),
        "coordinates": coords
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=0.5)
        last_webhook = now
    except Exception as e:
        print(f"[!] Webhook failed: {e}")

# Load model
stain_model = YOLO(MODEL_PATH)
stain_model.to("cuda")  # use GPU

# Webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("❌ Cannot open webcam")

fps = cap.get(cv2.CAP_PROP_FPS)
fps = fps if fps > 0 else 30

width_orig = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height_orig = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

scale = DOWNSCALE_WIDTH / width_orig
new_width = DOWNSCALE_WIDTH
new_height = int(height_orig * scale)

# Output writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (new_width, new_height))

frame_idx = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_resized = cv2.resize(frame, (new_width, new_height))
    results = stain_model(frame_resized, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)[0]

    for det in results.boxes:
        x1, y1, x2, y2 = map(int, det.xyxy[0])
        conf = float(det.conf[0])
        area = (x2 - x1) * (y2 - y1)

        # ✅ Allow smaller detections, but skip very large ones
        if area < MIN_AREA or area > MAX_AREA:
            continue

        class_id = int(det.cls[0])
        label = f"{stain_model.names[class_id]} {conf:.2f}"

        # Draw
        cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(frame_resized, label, (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Flip y-coordinates for Webhook
        y1_flipped = new_height - y1
        y2_flipped = new_height - y2
        coords_flipped = [x1, y1_flipped, x2, y2_flipped]
        send_webhook("bloodstain", conf, coords_flipped)

        print(f"[{frame_idx}] Stain {conf:.2f} Area: {area} — Coords: {coords_flipped}")

    # FPS
    frame_idx += 1
    elapsed = time.time() - start_time
    fps_display = frame_idx / elapsed if elapsed > 0 else 0
    cv2.putText(frame_resized, f"FPS: {fps_display:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    out.write(frame_resized)
    cv2.imshow("🩸 Bloodstain Detection — Small Objects Mode", frame_resized)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
print(f"✅ Done — Output saved to: {OUTPUT_VIDEO}")
