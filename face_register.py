import cv2
import os
import smtplib
import zipfile
import time
from tkinter import *
from email.message import EmailMessage
from PIL import Image, ImageTk

# 📧 Email config
your_email = "sarayyyyfyp@gmail.com"
your_password = "bjtlgplccyourrco"
receiver_email = "khasvinikannan30@gmail.com"

# 📁 Ensure folder exists
if not os.path.exists('RegisteredFaces'):
    os.makedirs('RegisteredFaces')

# 📤 Email ZIP
def send_email_with_zip(zip_path, person_name):
    msg = EmailMessage()
    msg['Subject'] = f'New Face Registration (10 Full Frames): {person_name}'
    msg['From'] = your_email
    msg['To'] = receiver_email
    msg.set_content(f'{person_name} registered with 10 full-frame webcam images.')

    with open(zip_path, 'rb') as file:
        msg.add_attachment(file.read(), maintype='application', subtype='zip', filename=os.path.basename(zip_path))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(your_email, your_password)
        smtp.send_message(msg)

# 📸 Capture full frames
def register_face():
    name = name_entry.get().strip()
    if not name:
        status_label.config(text="Please enter a name first!")
        return

    folder_path = os.path.join("RegisteredFaces", name)
    os.makedirs(folder_path, exist_ok=True)

    cam = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    status_label.config(text="Capturing 10 full images... Press 'q' to cancel.")

    count = 0
    while count < 10:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            break  # just for visual aid

        img_filename = os.path.join(folder_path, f"{name}_{count+1}.jpg")
        cv2.imwrite(img_filename, frame)
        count += 1
        status_label.config(text=f"Captured image {count}/10")
        time.sleep(0.5)

        cv2.imshow("Register Face (Press 'q' to cancel)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    if count == 10:
        zip_filename = f"{folder_path}.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for img_file in os.listdir(folder_path):
                img_path = os.path.join(folder_path, img_file)
                zipf.write(img_path, arcname=img_file)

        status_label.config(text="Sending full-frame images...")
        send_email_with_zip(zip_filename, name)
        status_label.config(text="Images sent successfully!")
    else:
        status_label.config(text="Canceled or incomplete.")

# 🖼 GUI
root = Tk()
root.title("Face Registration App")
root.geometry("400x200")

Label(root, text="Enter Name:").pack(pady=10)
name_entry = Entry(root, width=30)
name_entry.pack()

Button(root, text="Register Face", command=register_face).pack(pady=20)
status_label = Label(root, text="", fg="blue")
status_label.pack()

root.mainloop()