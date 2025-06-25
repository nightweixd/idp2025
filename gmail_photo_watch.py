import os
import time
import imapclient
import pyzmail
import zipfile
import cv2
import pickle
import numpy as np
from datetime import datetime, timedelta, timezone
from insightface.app import FaceAnalysis
import tkinter as tk
from tkinter import simpledialog, messagebox

# ─── Configuration ─────────────────────────────
EMAIL_ADDRESS = "sarayyyyfyp@gmail.com" 
EMAIL_PASSWORD = "bjtlgplccyourrco"
IMAP_SERVER = "imap.gmail.com"
SAVE_FOLDER = "C:/Users/fongj/OneDrive/Desktop/idp/new_faces"
ENCODING_PKL_PATH = "face_encodings_v2.pkl"
CHECK_INTERVAL = 30  # seconds
# ───────────────────────────────────────────────

os.makedirs(SAVE_FOLDER, exist_ok=True)

def download_and_extract_zip(zip_bytes, extract_to):
    temp_zip_path = os.path.join(SAVE_FOLDER, "temp.zip")
    with open(temp_zip_path, "wb") as f:
        f.write(zip_bytes)

    with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(temp_zip_path)
    print(f"[✓] Extracted zip to {extract_to}")

def download_new_photos():
    extracted_paths = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    with imapclient.IMAPClient(IMAP_SERVER, ssl=True) as client:
        client.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        client.select_folder("INBOX")

        messages = client.search(["UNSEEN"])
        print(f"[✓] {len(messages)} unseen email(s) found")

        for uid in messages:
            envelope = client.fetch([uid], ["ENVELOPE"])[uid][b"ENVELOPE"]
            email_datetime = envelope.date
            if email_datetime.tzinfo is None:
                email_datetime = email_datetime.replace(tzinfo=timezone.utc)
            if email_datetime < cutoff_time:
                continue

            raw_msg = client.fetch([uid], ["BODY[]", "FLAGS"])[uid][b"BODY[]"]
            msg = pyzmail.PyzMessage.factory(raw_msg)

            # Ask for user name only once
            root = tk.Tk()
            root.withdraw()
            user_name = simpledialog.askstring("Face Registration", "Enter name for the new face:")
            root.destroy()
            if not user_name:
                messagebox.showerror("Error", "No name entered.")
                return []

            user_dir = os.path.join(SAVE_FOLDER, user_name)
            os.makedirs(user_dir, exist_ok=True)

            for part in msg.walk():
                filename = part.get_filename()
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)

                if not filename or payload is None:
                    continue

                if filename.lower().endswith(".zip"):
                    download_and_extract_zip(payload, user_dir)
                elif filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ext = filename.split(".")[-1]
                    filepath = os.path.join(user_dir, f"{ts}.{ext}")
                    with open(filepath, "wb") as f:
                        f.write(payload)
                    extracted_paths.append(filepath)
                    print(f"[✓] Saved: {filepath}")

            # Mark as seen
            client.add_flags(uid, [imapclient.SEEN])
        client.logout()

    # List all image paths from folder
    return [os.path.join(user_dir, f) for f in os.listdir(user_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))]

def encode_faces(photo_paths):
    if not photo_paths:
        print("No new face photos found.")
        return

    # Get name from folder path
    person_name = os.path.basename(os.path.dirname(photo_paths[0]))
    face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
    face_app.prepare(ctx_id=0)

    embedding_list = []
    for path in photo_paths:
        img = cv2.imread(path)
        faces = face_app.get(img)
        if faces:
            embedding_list.append(faces[0].embedding)
            print(f"[✓] Encoded: {os.path.basename(path)}")
        else:
            print(f"[x] No face found in: {os.path.basename(path)}")

    if not embedding_list:
        messagebox.showerror("No Faces", "No encodable faces were found.")
        return

    # Load existing data
    if os.path.exists(ENCODING_PKL_PATH):
        with open(ENCODING_PKL_PATH, "rb") as f:
            encoding_dict = pickle.load(f)
    else:
        encoding_dict = {}

    encoding_dict.setdefault(person_name, []).extend(embedding_list)

    with open(ENCODING_PKL_PATH, "wb") as f:
        pickle.dump(encoding_dict, f)

    messagebox.showinfo("Success", f"{len(embedding_list)} faces saved for {person_name}")

# ─── Main Loop ──────────────────────────────────
if __name__ == "__main__":
    print("📬 Watching Gmail for new face photos... (CTRL+C to stop)")
    try:
        while True:
            new_files = download_new_photos()
            if new_files:
                encode_faces(new_files)
            else:
                print("[…] No new photos.")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
