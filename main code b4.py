import customtkinter as ctk
import sqlite3
import os
import cv2
import numpy as np
from PIL import Image, ImageTk
import pyttsx3
import threading
import serial
import time

# ── Text-to-Speech ────────────────────────────────────────────────────────────
def speak(text):
    def run():
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=run, daemon=True).start()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "voting.db")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODEL_PATH = os.path.join(BASE_DIR, "model.yml")

os.makedirs(DATASET_DIR, exist_ok=True)

# ── Authority Password ────────────────────────────────────────────────────────
AUTHORITY_PASSWORD = "1234"

# ── Arduino Connection ────────────────────────────────────────────────────────
arduino = None

def connect_arduino():
    global arduino
    try:
        arduino = serial.Serial("COM3", 9600, timeout=1)
        time.sleep(2)
        print("Arduino connected on COM3")
    except Exception as e:
        print(f"Arduino not connected: {e}")
        arduino = None

def send_to_arduino(msg):
    if arduino and arduino.is_open:
        try:
            arduino.write((msg + "\n").encode())
            arduino.flush()
            print(f"Sent to Arduino: {msg}")
        except Exception as e:
            print(f"Arduino send error: {e}")
connect_arduino()

# ── Share arduino with fingerprint.py ────────────────────────────────────────
import fingerprint as fp_module
fp_module.set_arduino(arduino)

# ── Database Setup ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        aadhaar TEXT UNIQUE NOT NULL,
        voter_no TEXT UNIQUE NOT NULL,
        has_voted INTEGER DEFAULT 0,
        fingerprint_id INTEGER UNIQUE
    )''')
    try:
        c.execute("ALTER TABLE voters ADD COLUMN fingerprint_id INTEGER UNIQUE")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

# ── Face Recognizer ───────────────────────────────────────────────────────────
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
recognizer = cv2.face.LBPHFaceRecognizer_create()

def train_model():
    faces, ids = [], []
    for filename in os.listdir(DATASET_DIR):
        if not filename.endswith(".jpg"):
            continue
        img_path = os.path.join(DATASET_DIR, filename)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        voter_id = int(filename.split("_")[1])
        faces.append(img)
        ids.append(voter_id)
    if faces:
        recognizer.train(faces, np.array(ids))
        recognizer.save(MODEL_PATH)

if os.path.exists(MODEL_PATH):
    recognizer.read(MODEL_PATH)

# ── App Theme ─────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Main Window ───────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title("Smart Voting System")
app.geometry("800x620")
app.resizable(False, False)

# ── Helpers ───────────────────────────────────────────────────────────────────
def clear():
    for widget in app.winfo_children():
        widget.destroy()

def make_header(subtitle="Secure · Transparent · Digital"):
    header = ctk.CTkFrame(app, fg_color="#0f3460", corner_radius=0, height=100)
    header.pack(fill="x")
    header.pack_propagate(False)
    ctk.CTkLabel(header, text="🗳️  SMART VOTING SYSTEM",
                 font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
                 text_color="#e0e0e0").place(relx=0.5, rely=0.4, anchor="center")
    ctk.CTkLabel(header, text=subtitle,
                 font=ctk.CTkFont(family="Arial", size=13),
                 text_color="#7ec8e3").place(relx=0.5, rely=0.75, anchor="center")

def make_footer():
    ctk.CTkLabel(app, text="Developed by Sounak  |  Smart Voting System v1.0",
                 font=ctk.CTkFont(family="Arial", size=10),
                 text_color="#444444").pack(pady=6)

def show_password_dialog(on_success):
    dialog = ctk.CTkToplevel(app)
    dialog.title("Authority Access")
    dialog.geometry("340x220")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus()

    ctk.CTkLabel(dialog, text="🔒  Authority Access",
                 font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(25, 5))
    ctk.CTkLabel(dialog, text="Enter password to continue",
                 font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack()

    pwd_entry = ctk.CTkEntry(dialog, width=220, height=40, show="*",
                              placeholder_text="Password", corner_radius=10)
    pwd_entry.pack(pady=15)

    msg = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=12), text_color="#cc3333")
    msg.pack()

    def check():
        if pwd_entry.get() == AUTHORITY_PASSWORD:
            dialog.destroy()
            on_success()
        else:
            msg.configure(text="❌ Wrong password")

    ctk.CTkButton(dialog, text="Enter", width=120, height=38,
                  corner_radius=10, command=check).pack(pady=10)

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════
def show_main_menu():
    clear()
    make_header()

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="Select an Option",
                 font=ctk.CTkFont(family="Arial", size=16),
                 text_color="#aaaaaa").pack(pady=(20, 15))

    btn_config = {
        "width": 320, "height": 50, "corner_radius": 12,
        "font": ctk.CTkFont(family="Arial", size=15, weight="bold"),
        "cursor": "hand2"
    }

    ctk.CTkButton(content, text="🗳️   VOTE", fg_color="#1a6b3c", hover_color="#145230",
                  **btn_config, command=show_vote).pack(pady=7)
    ctk.CTkButton(content, text="✅   CHECK ELIGIBILITY", fg_color="#1a4a7a", hover_color="#133a61",
                  **btn_config, command=show_eligibility).pack(pady=7)
    ctk.CTkButton(content, text="👤   REGISTER VOTER", fg_color="#5a3e8a", hover_color="#472f6e",
                  **btn_config, command=lambda: show_password_dialog(show_register)).pack(pady=7)
    ctk.CTkButton(content, text="🔧   MANAGE VOTERS", fg_color="#2a5a6a", hover_color="#1e4555",
                  **btn_config, command=lambda: show_password_dialog(show_manage_voters)).pack(pady=7)
    ctk.CTkButton(content, text="📊   VOTER LIST", fg_color="#7a4a1a", hover_color="#5e3814",
                  **btn_config, command=lambda: show_password_dialog(show_voter_list)).pack(pady=7)
    ctk.CTkButton(content, text="🔄   RESET ELECTION", fg_color="#7a1a1a", hover_color="#5e1414",
                  **btn_config, command=lambda: show_password_dialog(show_reset)).pack(pady=7)

    make_footer()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — CHECK ELIGIBILITY
# ══════════════════════════════════════════════════════════════════════════════
def show_eligibility():
    clear()
    make_header("Check Voter Eligibility")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="Enter Your Aadhaar Number",
                 font=ctk.CTkFont(size=16), text_color="#aaaaaa").pack(pady=(40, 10))

    aadhaar_entry = ctk.CTkEntry(content, width=300, height=45,
                                  placeholder_text="12-digit Aadhaar Number",
                                  font=ctk.CTkFont(size=14), corner_radius=10)
    aadhaar_entry.pack(pady=10)

    result_label = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=15, weight="bold"))
    result_label.pack(pady=10)

    info_frame = ctk.CTkFrame(content, fg_color="#1e1e2e", corner_radius=12, width=400, height=120)
    info_frame.pack(pady=5)
    info_frame.pack_propagate(False)

    def check():
        aadhaar = aadhaar_entry.get().strip()
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            result_label.configure(text="⚠️  Enter a valid 12-digit Aadhaar number", text_color="#ffaa00")
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, voter_no, has_voted FROM voters WHERE aadhaar = ?", (aadhaar,))
        row = c.fetchone()
        conn.close()
        for w in info_frame.winfo_children():
            w.destroy()
        if row:
            name, voter_no, has_voted = row
            result_label.configure(text="✅  Voter Found — Eligible", text_color="#00cc66")
            ctk.CTkLabel(info_frame, text=f"Name      :  {name}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=20, pady=(15, 4))
            ctk.CTkLabel(info_frame, text=f"Voter No  :  {voter_no}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=20, pady=4)
            voted_text = "Already Voted ❌" if has_voted else "Not Yet Voted ✅"
            voted_color = "#cc3333" if has_voted else "#00cc66"
            ctk.CTkLabel(info_frame, text=f"Status    :  {voted_text}", font=ctk.CTkFont(size=13, weight="bold"), text_color=voted_color).pack(anchor="w", padx=20, pady=4)
        else:
            result_label.configure(text="❌  Not Registered", text_color="#cc3333")
            ctk.CTkLabel(info_frame, text="This Aadhaar number is not in the system.",
                         font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(expand=True)

    ctk.CTkButton(content, text="🔍   Check Eligibility", width=220, height=45, corner_radius=10,
                  font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1a4a7a", hover_color="#133a61",
                  cursor="hand2", command=check).pack(pady=10)
    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=5)

    make_footer()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — REGISTER VOTER
# ══════════════════════════════════════════════════════════════════════════════
def show_register():
    clear()
    make_header("Register New Voter")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    form = ctk.CTkFrame(content, fg_color="#1e1e2e", corner_radius=14, width=500, height=340)
    form.pack(pady=20)
    form.pack_propagate(False)

    ctk.CTkLabel(form, text="Voter Registration Form",
                 font=ctk.CTkFont(size=16, weight="bold"), text_color="#7ec8e3").pack(pady=(18, 10))

    name_entry = ctk.CTkEntry(form, width=380, height=40, placeholder_text="Full Name", corner_radius=10)
    name_entry.pack(pady=6)
    aadhaar_entry = ctk.CTkEntry(form, width=380, height=40, placeholder_text="12-digit Aadhaar Number", corner_radius=10)
    aadhaar_entry.pack(pady=6)
    voter_entry = ctk.CTkEntry(form, width=380, height=40, placeholder_text="Voter ID Number", corner_radius=10)
    voter_entry.pack(pady=6)

    msg_label = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=12))
    msg_label.pack(pady=5)

    def start_enroll():
        name = name_entry.get().strip()
        aadhaar = aadhaar_entry.get().strip()
        voter_no = voter_entry.get().strip()

        if not name:
            msg_label.configure(text="⚠️  Please enter name", text_color="#ffaa00"); return
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            msg_label.configure(text="⚠️  Enter valid 12-digit Aadhaar", text_color="#ffaa00"); return
        if not voter_no:
            msg_label.configure(text="⚠️  Please enter Voter ID", text_color="#ffaa00"); return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM voters WHERE aadhaar = ?", (aadhaar,))
        if c.fetchone():
            conn.close()
            msg_label.configure(text="❌  Aadhaar already registered", text_color="#cc3333"); return
        c.execute("SELECT id FROM voters WHERE voter_no = ?", (voter_no,))
        if c.fetchone():
            conn.close()
            msg_label.configure(text="❌  Voter ID already registered", text_color="#cc3333"); return
        conn.close()

        # Go to fingerprint enrollment screen
        show_fingerprint_enroll(name, aadhaar, voter_no)

    ctk.CTkButton(form, text="👆   Scan Fingerprint & Register", width=300, height=42, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#5a3e8a", hover_color="#472f6e",
                  cursor="hand2", command=start_enroll).pack(pady=8)

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=5)

    make_footer()

# ── Fingerprint Enrollment Screen ─────────────────────────────────────────────
def show_fingerprint_enroll(name, aadhaar, voter_no):
    clear()
    make_header(f"Fingerprint Enrollment — {name}")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="👆", font=ctk.CTkFont(size=60)).pack(pady=(30, 5))
    ctk.CTkLabel(content, text="Enrolling Fingerprint",
                 font=ctk.CTkFont(size=18, weight="bold"), text_color="#e0e0e0").pack(pady=5)

    status_label = ctk.CTkLabel(content, text="Starting enrollment...",
                                 font=ctk.CTkFont(size=14), text_color="#aaaaaa")
    status_label.pack(pady=15)

    fp_id_result = [None]

    def on_status(msg):
        app.after(0, lambda: status_label.configure(text=msg))

    def do_enroll():
        fp_id = fp_module.enroll_fingerprint(on_status)
        fp_id_result[0] = fp_id

        if fp_id is not None:
            # Save voter to DB with fingerprint ID
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO voters (name, aadhaar, voter_no, fingerprint_id) VALUES (?, ?, ?, ?)",
                      (name, aadhaar, voter_no, fp_id))
            voter_id = c.lastrowid
            conn.commit()
            conn.close()
            app.after(0, lambda: show_face_capture(voter_id, name))
        else:
            # Arduino not connected — ask for manual ID
            app.after(0, lambda: show_manual_fp_entry(name, aadhaar, voter_no, on_status))

    threading.Thread(target=do_enroll, daemon=True).start()

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_register).pack(pady=10)

    make_footer()

# ── Manual fingerprint ID entry (fallback if Arduino not connected) ────────────
def show_manual_fp_entry(name, aadhaar, voter_no, on_status):
    clear()
    make_header(f"Register — {name}")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="⚠️  Arduino not connected",
                 font=ctk.CTkFont(size=15, weight="bold"), text_color="#ffaa00").pack(pady=(40, 10))
    ctk.CTkLabel(content, text="Enter fingerprint ID manually to continue:",
                 font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(pady=5)

    fp_entry = ctk.CTkEntry(content, width=200, height=45,
                             placeholder_text="Fingerprint ID (e.g. 1)",
                             font=ctk.CTkFont(size=14), corner_radius=10)
    fp_entry.pack(pady=10)

    msg_label = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=12))
    msg_label.pack(pady=5)

    def proceed():
        fp_id = fp_entry.get().strip()
        if not fp_id.isdigit():
            msg_label.configure(text="⚠️  Enter a valid number", text_color="#ffaa00"); return

        fp_id = int(fp_id)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM voters WHERE fingerprint_id = ?", (fp_id,))
        if c.fetchone():
            conn.close()
            msg_label.configure(text="❌  ID already assigned to another voter", text_color="#cc3333"); return
        c.execute("INSERT INTO voters (name, aadhaar, voter_no, fingerprint_id) VALUES (?, ?, ?, ?)",
                  (name, aadhaar, voter_no, fp_id))
        voter_id = c.lastrowid
        conn.commit()
        conn.close()
        show_face_capture(voter_id, name)

    ctk.CTkButton(content, text="➡️  Continue to Face Capture", width=280, height=45, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#5a3e8a", hover_color="#472f6e",
                  cursor="hand2", command=proceed).pack(pady=10)

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_register).pack(pady=5)

    make_footer()

# ── Face Capture ──────────────────────────────────────────────────────────────
def show_face_capture(voter_id, name):
    clear()
    make_header(f"Face Capture — {name}")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    info_label = ctk.CTkLabel(content, text="Look at the camera. Press SPACE to capture (need 20 photos)",
                               font=ctk.CTkFont(size=13), text_color="#aaaaaa")
    info_label.pack(pady=(10, 5))

    count_label = ctk.CTkLabel(content, text="Photos captured: 0 / 20",
                                font=ctk.CTkFont(size=14, weight="bold"), text_color="#7ec8e3")
    count_label.pack(pady=5)

    video_label = ctk.CTkLabel(content, text="")
    video_label.pack(pady=5)

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    count = [0]
    running = [True]

    def update():
        if not running[0]:
            return
        ret, frame = cam.read()
        if not ret:
            content.after(30, update)
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 200, 0), 2)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb).resize((500, 320))
        imgtk = ImageTk.PhotoImage(image=img_pil)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
        content.after(15, update)

    def on_space(event):
        if count[0] >= 20:
            return
        ret, frame = cam.read()
        if not ret:
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
        if len(faces) == 0:
            info_label.configure(text="⚠️  No face detected! Try again.", text_color="#ffaa00")
            return
        if len(faces) > 1:
            info_label.configure(text="⚠️  Multiple faces! Only one person in frame.", text_color="#ffaa00")
            return
        (x, y, w, h) = faces[0]
        face_img = gray[y:y+h, x:x+w]
        path = os.path.join(DATASET_DIR, f"voter_{voter_id}_{count[0]+1}.jpg")
        cv2.imwrite(path, face_img)
        count[0] += 1
        count_label.configure(text=f"Photos captured: {count[0]} / 20")
        info_label.configure(text="✅  Captured! Keep going...", text_color="#00cc66")
        if count[0] >= 20:
            running[0] = False
            cam.release()
            info_label.configure(text="✅  All photos captured! Training model...", text_color="#00cc66")
            app.after(500, lambda: finish_registration(voter_id, name))

    app.bind("<space>", on_space)
    update()

def finish_registration(voter_id, name):
    app.unbind("<space>")
    train_model()
    clear()
    make_header("Registration Complete")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="✅", font=ctk.CTkFont(size=60)).pack(pady=(50, 10))
    ctk.CTkLabel(content, text=f"{name} has been registered successfully!",
                 font=ctk.CTkFont(size=16, weight="bold"), text_color="#00cc66").pack(pady=10)
    ctk.CTkLabel(content, text="Fingerprint + Face data saved.",
                 font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack()

    ctk.CTkButton(content, text="Register Another Voter", width=220, height=45, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#5a3e8a", hover_color="#472f6e",
                  cursor="hand2", command=show_register).pack(pady=20)
    ctk.CTkButton(content, text="← Main Menu", width=160, height=38, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack()

    make_footer()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — MANAGE VOTERS
# ══════════════════════════════════════════════════════════════════════════════
def show_manage_voters():
    clear()
    make_header("Manage Voters")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="Search Voter by Aadhaar Number",
                 font=ctk.CTkFont(size=16), text_color="#aaaaaa").pack(pady=(25, 8))

    aadhaar_entry = ctk.CTkEntry(content, width=300, height=45,
                                  placeholder_text="12-digit Aadhaar Number",
                                  font=ctk.CTkFont(size=14), corner_radius=10)
    aadhaar_entry.pack(pady=6)

    msg_label = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=12))
    msg_label.pack(pady=3)

    result_frame = ctk.CTkFrame(content, fg_color="#1e1e2e", corner_radius=12)
    result_frame.pack(fill="x", padx=60, pady=4)

    def search():
        aadhaar = aadhaar_entry.get().strip()
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            msg_label.configure(text="⚠️  Enter valid 12-digit Aadhaar", text_color="#ffaa00")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, aadhaar, voter_no, has_voted, fingerprint_id FROM voters WHERE aadhaar = ?", (aadhaar,))
        row = c.fetchone()
        conn.close()

        for w in result_frame.winfo_children():
            w.destroy()

        if not row:
            msg_label.configure(text="❌  Voter not found", text_color="#cc3333")
            return

        msg_label.configure(text="✅  Voter found", text_color="#00cc66")
        voter_id, name, aadhaar_db, voter_no, has_voted, fp_id = row

        ctk.CTkLabel(result_frame, text=f"Name           :  {name}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=25, pady=(15, 4))
        ctk.CTkLabel(result_frame, text=f"Aadhaar        :  {aadhaar_db}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=25, pady=4)
        ctk.CTkLabel(result_frame, text=f"Voter No       :  {voter_no}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=25, pady=4)
        ctk.CTkLabel(result_frame, text=f"Fingerprint ID :  {fp_id if fp_id else 'Not assigned'}", font=ctk.CTkFont(size=13), text_color="#e0e0e0").pack(anchor="w", padx=25, pady=4)
        voted_text = "Already Voted ❌" if has_voted else "Not Yet Voted ✅"
        voted_color = "#cc3333" if has_voted else "#00cc66"
        ctk.CTkLabel(result_frame, text=f"Status         :  {voted_text}", font=ctk.CTkFont(size=13, weight="bold"), text_color=voted_color).pack(anchor="w", padx=25, pady=4)

        btn_row = ctk.CTkFrame(result_frame, fg_color="transparent")
        btn_row.pack(pady=12)

        ctk.CTkButton(btn_row, text="✏️  Edit", width=130, height=38, corner_radius=10,
                      font=ctk.CTkFont(size=12, weight="bold"), fg_color="#1a4a7a", hover_color="#133a61",
                      cursor="hand2", command=lambda: show_edit_voter(row)).pack(side="left", padx=12)

        ctk.CTkButton(btn_row, text="🗑️  Delete", width=130, height=38, corner_radius=10,
                      font=ctk.CTkFont(size=12, weight="bold"), fg_color="#7a1a1a", hover_color="#5e1414",
                      cursor="hand2", command=lambda: confirm_delete(voter_id, name, fp_id)).pack(side="left", padx=12)

    ctk.CTkButton(content, text="🔍   Search", width=180, height=42, corner_radius=10,
                  font=ctk.CTkFont(size=14, weight="bold"), fg_color="#2a5a6a", hover_color="#1e4555",
                  cursor="hand2", command=search).pack(pady=6)

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=8)

    make_footer()

# ── Edit Voter ────────────────────────────────────────────────────────────────
def show_edit_voter(row):
    voter_id, name, aadhaar, voter_no, has_voted, fp_id = row

    dialog = ctk.CTkToplevel(app)
    dialog.title("Edit Voter")
    dialog.geometry("420x320")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus()

    ctk.CTkLabel(dialog, text="✏️  Edit Voter Details",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 15))

    name_entry = ctk.CTkEntry(dialog, width=320, height=40, corner_radius=10)
    name_entry.insert(0, name)
    name_entry.pack(pady=6)

    aadhaar_entry = ctk.CTkEntry(dialog, width=320, height=40, corner_radius=10)
    aadhaar_entry.insert(0, aadhaar)
    aadhaar_entry.pack(pady=6)

    voter_entry = ctk.CTkEntry(dialog, width=320, height=40, corner_radius=10)
    voter_entry.insert(0, voter_no)
    voter_entry.pack(pady=6)

    msg = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=12))
    msg.pack(pady=5)

    def save_changes():
        new_name = name_entry.get().strip()
        new_aadhaar = aadhaar_entry.get().strip()
        new_voter_no = voter_entry.get().strip()

        if not new_name:
            msg.configure(text="⚠️  Name cannot be empty", text_color="#ffaa00"); return
        if len(new_aadhaar) != 12 or not new_aadhaar.isdigit():
            msg.configure(text="⚠️  Invalid Aadhaar number", text_color="#ffaa00"); return
        if not new_voter_no:
            msg.configure(text="⚠️  Voter ID cannot be empty", text_color="#ffaa00"); return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE voters SET name=?, aadhaar=?, voter_no=? WHERE id=?",
                  (new_name, new_aadhaar, new_voter_no, voter_id))
        conn.commit()
        conn.close()
        msg.configure(text="✅  Updated successfully!", text_color="#00cc66")
        dialog.after(1000, dialog.destroy)

    ctk.CTkButton(dialog, text="💾  Save Changes", width=180, height=40, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1a6b3c", hover_color="#145230",
                  cursor="hand2", command=save_changes).pack(pady=5)

# ── Confirm Delete ────────────────────────────────────────────────────────────
def confirm_delete(voter_id, name, fp_id):
    dialog = ctk.CTkToplevel(app)
    dialog.title("Confirm Delete")
    dialog.geometry("360x200")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus()

    ctk.CTkLabel(dialog, text="⚠️  Confirm Delete",
                 font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffaa00").pack(pady=(25, 10))
    ctk.CTkLabel(dialog, text=f"Are you sure you want to delete\n{name} from the system?",
                 font=ctk.CTkFont(size=13), text_color="#aaaaaa", justify="center").pack(pady=5)

    btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_row.pack(pady=15)

    def do_delete():
        # Delete face images
        for f in os.listdir(DATASET_DIR):
            if f.startswith(f"voter_{voter_id}_"):
                os.remove(os.path.join(DATASET_DIR, f))
        # Delete from DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM voters WHERE id = ?", (voter_id,))
        conn.commit()
        conn.close()
        # Delete fingerprint from Arduino sensor
        if fp_id:
            fp_module.delete_fingerprint(fp_id)
        train_model()
        dialog.destroy()
        show_manage_voters()

    ctk.CTkButton(btn_row, text="Yes, Delete", width=130, height=38, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#7a1a1a", hover_color="#5e1414",
                  cursor="hand2", command=do_delete).pack(side="left", padx=10)

    ctk.CTkButton(btn_row, text="Cancel", width=100, height=38, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=dialog.destroy).pack(side="left", padx=10)

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — VOTE
# ══════════════════════════════════════════════════════════════════════════════
def show_vote():
    clear()
    make_header("Cast Your Vote")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="Enter Your Aadhaar Number",
                 font=ctk.CTkFont(size=16), text_color="#aaaaaa").pack(pady=(40, 10))

    aadhaar_entry = ctk.CTkEntry(content, width=300, height=45,
                                  placeholder_text="12-digit Aadhaar Number",
                                  font=ctk.CTkFont(size=14), corner_radius=10)
    aadhaar_entry.pack(pady=10)

    msg_label = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=13))
    msg_label.pack(pady=8)

    def proceed():
        aadhaar = aadhaar_entry.get().strip()
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            msg_label.configure(text="⚠️  Enter valid 12-digit Aadhaar", text_color="#ffaa00"); return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, has_voted, fingerprint_id FROM voters WHERE aadhaar = ?", (aadhaar,))
        row = c.fetchone()
        conn.close()
        if not row:
            msg_label.configure(text="❌  Not registered. Please register first.", text_color="#cc3333"); return
        voter_id, name, has_voted, fp_id = row
        if has_voted:
            msg_label.configure(text=f"❌  {name} has already voted!", text_color="#cc3333"); return
        msg_label.configure(text=f"✅  Welcome {name}! Proceeding to fingerprint...", text_color="#00cc66")
        app.after(1000, lambda: show_fingerprint_verify(voter_id, name, aadhaar, fp_id))

    ctk.CTkButton(content, text="➡️   Proceed", width=200, height=45, corner_radius=10,
                  font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1a6b3c", hover_color="#145230",
                  cursor="hand2", command=proceed).pack(pady=10)
    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=5)

    make_footer()

# ── Fingerprint Verification Screen ──────────────────────────────────────────
def show_fingerprint_verify(voter_id, name, aadhaar, fp_id):
    clear()
    make_header(f"Fingerprint Verification — {name}")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="👆", font=ctk.CTkFont(size=60)).pack(pady=(40, 10))
    ctk.CTkLabel(content, text="Place your finger on the sensor",
                 font=ctk.CTkFont(size=16, weight="bold"), text_color="#e0e0e0").pack(pady=5)

    status_label = ctk.CTkLabel(content, text="Waiting...",
                                 font=ctk.CTkFont(size=14), text_color="#aaaaaa")
    status_label.pack(pady=15)

    def on_status(msg):
        app.after(0, lambda: status_label.configure(text=msg))

    def do_verify():
        scanned_id = fp_module.verify_fingerprint(on_status)

        if scanned_id is None:
            # Arduino not connected — use simulate button
            app.after(0, lambda: status_label.configure(
                text="⚠️  Arduino not connected. Use simulate button.", text_color="#ffaa00"))
            return

        if scanned_id != fp_id:
            app.after(0, lambda: status_label.configure(
                text="❌  Fingerprint does not match this voter!", text_color="#cc3333"))
            return

        app.after(0, lambda: status_label.configure(text="✅  Fingerprint Matched!", text_color="#00cc66"))
        app.after(800, lambda: show_face_verify(voter_id, name, aadhaar))

    threading.Thread(target=do_verify, daemon=True).start()

    # Simulate button for testing without Arduino
    ctk.CTkButton(content, text="🔬  Simulate Fingerprint (Test Only)", width=280, height=42,
                  corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
                  fg_color="#2a5a6a", hover_color="#1e4555", cursor="hand2",
                  command=lambda: [
                      status_label.configure(text="✅  Fingerprint Matched!", text_color="#00cc66"),
                      app.after(800, lambda: show_face_verify(voter_id, name, aadhaar))
                  ]).pack(pady=8)

    ctk.CTkLabel(content, text="⚠️  Simulate button is for testing only.",
                 font=ctk.CTkFont(size=11), text_color="#555555").pack(pady=2)

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=8)

    make_footer()

# ── Face Verification ─────────────────────────────────────────────────────────
def show_face_verify(voter_id, name, aadhaar):
    clear()
    make_header(f"Face Verification — {name}")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    status_label = ctk.CTkLabel(content, text="Please look at the camera — only one person allowed",
                                 font=ctk.CTkFont(size=14), text_color="#aaaaaa")
    status_label.pack(pady=(10, 5))

    video_label = ctk.CTkLabel(content, text="")
    video_label.pack(pady=5)

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    running = [True]
    verified = [False]

    def update():
        if not running[0]:
            return
        ret, frame = cam.read()
        if not ret:
            content.after(30, update)
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))

        if len(faces) > 1:
            status_label.configure(
                text="⚠️  Multiple faces detected! Only the voter can be in frame.",
                text_color="#ffaa00"
            )
            send_to_arduino("FACE:0")
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 200), 2)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb).resize((500, 300))
            imgtk = ImageTk.PhotoImage(image=img_pil)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
            content.after(15, update)
            return

        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            try:
                pred_id, confidence = recognizer.predict(face_roi)
            except:
                continue
            if pred_id == voter_id and confidence < 70:
                if not verified[0]:
                    verified[0] = True
                    running[0] = False
                    cam.release()
                    send_to_arduino("FACE:1")
                    status_label.configure(text="✅  Face Verified!", text_color="#00cc66")
                    app.after(800, lambda: show_voting_screen(voter_id, name, aadhaar))
                color = (0, 200, 0)
                label_text = "Verified"
            else:
                color = (0, 0, 200)
                label_text = "Not Matched"
                status_label.configure(
                    text="Please look at the camera — only one person allowed",
                    text_color="#aaaaaa"
                )
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb).resize((500, 300))
        imgtk = ImageTk.PhotoImage(image=img_pil)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
        content.after(15, update)

    update()

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=lambda: [running.__setitem__(0, False), cam.release(),
                                   send_to_arduino("FACE:0"), show_main_menu()]).pack(pady=8)

    make_footer()

# ── Voting Screen ─────────────────────────────────────────────────────────────
def show_voting_screen(voter_id, name, aadhaar):
    clear()
    make_header("Cast Your Vote")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text=f"Welcome, {name}",
                 font=ctk.CTkFont(size=18, weight="bold"), text_color="#e0e0e0").pack(pady=(25, 5))
    ctk.CTkLabel(content, text="Select your party to cast your vote",
                 font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(pady=(0, 20))

    parties = [
        ("TMC",    "#1a6b3c", "#145230"),
        ("BJP",    "#7a1a1a", "#5e1414"),
        ("AJP",    "#1a4a7a", "#133a61"),
        ("NIRDAL", "#5a3e8a", "#472f6e"),
    ]

    def cast_vote(party):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE voters SET has_voted = 1 WHERE id = ?", (voter_id,))
        conn.commit()
        conn.close()
        show_vote_success(name, party)

    for party, fg, hover in parties:
        ctk.CTkButton(content, text=f"🗳️   {party}", width=300, height=52, corner_radius=12,
                      font=ctk.CTkFont(size=16, weight="bold"), fg_color=fg, hover_color=hover,
                      cursor="hand2", command=lambda p=party: cast_vote(p)).pack(pady=7)

    make_footer()

# ── Vote Success ──────────────────────────────────────────────────────────────
def show_vote_success(name, party):
    speak("Voting done successfully")
    clear()
    make_header("Vote Submitted")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="✅", font=ctk.CTkFont(size=70)).pack(pady=(40, 10))
    ctk.CTkLabel(content, text="Vote Submitted Successfully!",
                 font=ctk.CTkFont(size=20, weight="bold"), text_color="#00cc66").pack(pady=5)
    ctk.CTkLabel(content, text=f"{name} voted for {party}",
                 font=ctk.CTkFont(size=14), text_color="#aaaaaa").pack(pady=5)
    ctk.CTkLabel(content, text="Thank you for participating in the democratic process.",
                 font=ctk.CTkFont(size=12), text_color="#555577").pack(pady=5)

    ctk.CTkButton(content, text="← Main Menu", width=180, height=42, corner_radius=10,
                  font=ctk.CTkFont(size=13, weight="bold"), fg_color="#2a2a2a", hover_color="#3a3a3a",
                  cursor="hand2", command=show_main_menu).pack(pady=25)

    make_footer()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 6 — VOTER LIST
# ══════════════════════════════════════════════════════════════════════════════
def show_voter_list():
    clear()
    make_header("Voter List")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, aadhaar, voter_no, has_voted FROM voters ORDER BY id")
    rows = c.fetchall()
    conn.close()

    total = len(rows)
    voted = sum(1 for r in rows if r[3])

    summary = ctk.CTkFrame(content, fg_color="#1e1e2e", corner_radius=10, height=45)
    summary.pack(fill="x", padx=20, pady=(15, 8))
    summary.pack_propagate(False)
    ctk.CTkLabel(summary, text=f"Total Voters: {total}   |   Voted: {voted}   |   Pending: {total - voted}",
                 font=ctk.CTkFont(size=13, weight="bold"), text_color="#7ec8e3").pack(expand=True)

    header_row = ctk.CTkFrame(content, fg_color="#0f3460", corner_radius=8, height=36)
    header_row.pack(fill="x", padx=20, pady=(0, 4))
    header_row.pack_propagate(False)
    for col, w in [("Name", 200), ("Aadhaar", 160), ("Voter No", 140), ("Status", 100)]:
        ctk.CTkLabel(header_row, text=col, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#e0e0e0", width=w).pack(side="left", padx=5)

    scroll = ctk.CTkScrollableFrame(content, fg_color="#121212", height=260)
    scroll.pack(fill="both", expand=True, padx=20, pady=4)

    for row in rows:
        name, aadhaar, voter_no, has_voted = row
        row_frame = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8, height=36)
        row_frame.pack(fill="x", pady=2)
        row_frame.pack_propagate(False)
        masked = "XXXX-XXXX-" + aadhaar[-4:]
        status = "Voted ✅" if has_voted else "Pending"
        status_color = "#00cc66" if has_voted else "#aaaaaa"
        ctk.CTkLabel(row_frame, text=name, width=200, font=ctk.CTkFont(size=12), text_color="#e0e0e0").pack(side="left", padx=5)
        ctk.CTkLabel(row_frame, text=masked, width=160, font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(side="left", padx=5)
        ctk.CTkLabel(row_frame, text=voter_no, width=140, font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(side="left", padx=5)
        ctk.CTkLabel(row_frame, text=status, width=100, font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(side="left", padx=5)

    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack(pady=8)

    make_footer()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 7 — RESET ELECTION
# ══════════════════════════════════════════════════════════════════════════════
def show_reset():
    clear()
    make_header("Reset Election")

    content = ctk.CTkFrame(app, fg_color="#121212", corner_radius=0)
    content.pack(fill="both", expand=True)

    ctk.CTkLabel(content, text="⚠️", font=ctk.CTkFont(size=60)).pack(pady=(40, 10))
    ctk.CTkLabel(content, text="Reset Election",
                 font=ctk.CTkFont(size=20, weight="bold"), text_color="#ffaa00").pack(pady=5)
    ctk.CTkLabel(content, text="This will clear all voting records.\nVoter registrations will be kept intact.\nAll voters will be able to vote again.",
                 font=ctk.CTkFont(size=13), text_color="#aaaaaa", justify="center").pack(pady=10)

    msg_label = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=13))
    msg_label.pack(pady=5)

    def do_reset():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE voters SET has_voted = 0")
        conn.commit()
        conn.close()
        msg_label.configure(text="✅  Election reset! All voters can vote again.", text_color="#00cc66")

    ctk.CTkButton(content, text="🔄   Confirm Reset", width=220, height=48, corner_radius=12,
                  font=ctk.CTkFont(size=14, weight="bold"), fg_color="#7a1a1a", hover_color="#5e1414",
                  cursor="hand2", command=do_reset).pack(pady=15)
    ctk.CTkButton(content, text="← Back", width=120, height=35, corner_radius=10,
                  fg_color="#2a2a2a", hover_color="#3a3a3a", cursor="hand2",
                  command=show_main_menu).pack()

    make_footer()

# ── Start ─────────────────────────────────────────────────────────────────────
show_main_menu()
def on_closing():
    global arduino
    if arduino and arduino.is_open:
        arduino.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()