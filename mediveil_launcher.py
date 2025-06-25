import tkinter as tk
import subprocess
import requests
import json
import psutil
import pickle
import os
from tkinter import simpledialog, messagebox

# ─── Webhook.site API Setup ───────────────────────────────
API_TOKEN = "083ff613-961c-4da0-9df2-59805368af6f"
WEBHOOK_ID = "9c5e82ec-4ecc-433b-a176-c56955ea74b0"
API_URL = f"https://webhook.site/token/{WEBHOOK_ID}/requests?sorting=newest"
ENCODINGS_PATH = "face_encodings_v2.pkl"

headers = {
    "api-key": API_TOKEN,
    "Accept": "application/json"
}

# ─── Process Management ────────────────────────────────────
processes = []

def run_script(script_path):
    print(f"[Launching] {script_path}")
    p = subprocess.Popen(["python", script_path], shell=True)
    processes.append(p)

def run_blood():
    run_script("C:\\Users\\fongj\\OneDrive\\Desktop\\idp\\scripts\\final\\camera_blood.py")

def run_face():
    run_script("C:\\Users\\fongj\\OneDrive\\Desktop\\idp\\scripts\\final\\faster_face.py")

def run_people():
    run_script("C:\\Users\\fongj\\OneDrive\\Desktop\\idp\\scripts\\final\\camera_people_count.py")

def run_combined():
    run_script("C:\\Users\\fongj\\OneDrive\\Desktop\\idp\\scripts\\final\\combined_people_face.py")

def run_register():
    run_script("C:\\Users\\fongj\\OneDrive\\Desktop\\idp\\scripts\\final\\gmail_photo_watch.py")

def stop_all():
    for p in processes:
        try:
            parent = psutil.Process(p.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except Exception as e:
            print(f"[!] Error stopping process: {e}")
    processes.clear()
    print("[✓] All subprocesses forcefully terminated.")

def on_close():
    stop_all()
    window.destroy()

# ─── Fetch Notifications from Webhook API ─────────────────
def fetch_notifications():
    notif_box.delete("1.0", tk.END)
    try:
        response = requests.get(API_URL, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            requests_data = data.get("data", [])[:20]
            for req in requests_data:
                ts = req.get("created_at", "no-time")
                content = req.get("content", "")
                try:
                    parsed = json.loads(content)
                    formatted = json.dumps(parsed, indent=2)
                except:
                    formatted = content
                notif_box.insert(tk.END, f"[{ts}]\n{formatted}\n\n")
        else:
            notif_box.insert(tk.END, f"❌ Failed to fetch (Status: {response.status_code})")
    except Exception as e:
        notif_box.insert(tk.END, f"❌ Error: {str(e)}")

# ─── Load Registered Users from Pickle ─────────────────────
def load_registered_users():
    user_box.delete("1.0", tk.END)
    if not os.path.exists(ENCODINGS_PATH):
        user_box.insert(tk.END, "No encoding file found.")
        return
    try:
        with open(ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)
            user_box.insert(tk.END, "\n".join(data.keys()))
    except Exception as e:
        user_box.insert(tk.END, f"Failed to load: {e}")

# ─── Delete Selected User ──────────────────────────────────
def delete_user():
    name = simpledialog.askstring("Delete User", "Enter user name to delete:")
    if not name:
        return

    if not os.path.exists(ENCODINGS_PATH):
        messagebox.showerror("Error", "Encoding file not found.")
        return

    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)

    if name not in data:
        messagebox.showwarning("Not Found", f"'{name}' not found in encodings.")
        return

    del data[name]
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump(data, f)

    messagebox.showinfo("Deleted", f"User '{name}' deleted.")
    load_registered_users()

# ─── Show Logs and Users ──────────────────────────────────
def show_log_and_users():
    fetch_notifications()
    load_registered_users()

# ─── Password Verification ────────────────────────────────
def check_password():
    if pw_entry.get() == "mediveil":
        login_window.destroy()
        launch_main_gui()
    else:
        login_status.config(text="❌ Incorrect password")

# ─── GUI Main App ─────────────────────────────────────────
def launch_main_gui():
    global window, notif_box, user_box
    window = tk.Tk()
    window.title("MEDIVEIL — Hospital Surveillance System")
    window.geometry("600x1080")
    window.configure(bg="#f0faff")

    tk.Label(window, text="MEDIVEIL", font=("Arial Black", 24, "bold"), fg="#007acc", bg="#f0faff").pack(pady=10)
    tk.Label(window, text="Hospital Surveillance Control Panel", font=("Arial", 14), bg="#f0faff").pack(pady=5)

    button_style = {"font": ("Arial", 12), "width": 40, "height": 2}
    tk.Button(window, text="🩸 Bloodstain Detection", command=run_blood, **button_style).pack(pady=5)
    tk.Button(window, text="👤 Face Recognition", command=run_face, **button_style).pack(pady=5)
    tk.Button(window, text="👣 People Flow Tracking", command=run_people, **button_style).pack(pady=5)
    tk.Button(window, text="🧠 Combined: People Flow + Face Recognition", command=run_combined, **button_style).pack(pady=10)
    tk.Button(window, text="📸 Register New User (Gmail Watcher)", command=run_register, **button_style).pack(pady=5)
    tk.Button(window, text="⏹️ Stop All Modules", command=stop_all, bg="#ff5555", fg="white", font=("Arial", 12), width=40, height=2).pack(pady=10)

    tk.Button(window, text="🔍 Show Logs & Registered Users", command=show_log_and_users, font=("Arial", 11), bg="#007acc", fg="white", width=40).pack(pady=5)
    tk.Button(window, text="🗑️ Delete Registered User", command=delete_user, font=("Arial", 11), bg="#cc0000", fg="white", width=40).pack(pady=5)

    tk.Label(window, text="🔔 Notifications", bg="#f0faff", font=("Arial", 12, "bold")).pack()
    notif_box = tk.Text(window, height=10, width=70, font=("Consolas", 10))
    notif_box.pack(pady=5)

    tk.Label(window, text="✅ Registered Users", bg="#f0faff", font=("Arial", 12, "bold")).pack()
    user_box = tk.Text(window, height=8, width=70, font=("Consolas", 10))
    user_box.pack(pady=5)

    tk.Button(window, text="🔄 Refresh Notifications", command=fetch_notifications,
              font=("Arial", 11), bg="#007acc", fg="white", width=30).pack(pady=5)

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

# ─── Login Window ─────────────────────────────────────────
login_window = tk.Tk()
login_window.title("MEDIVEIL Login")
login_window.geometry("300x600")
login_window.configure(bg="#f0faff")

pw_label = tk.Label(login_window, text="Enter Password:", font=("Arial", 12), bg="#f0faff")
pw_label.pack(pady=10)
pw_entry = tk.Entry(login_window, show="*", font=("Arial", 12), width=25)
pw_entry.pack()

login_status = tk.Label(login_window, text="", font=("Arial", 10), fg="red", bg="#f0faff")
login_status.pack()

tk.Button(login_window, text="Login", command=check_password, font=("Arial", 12), bg="#007acc", fg="white").pack(pady=10)

login_window.mainloop()
