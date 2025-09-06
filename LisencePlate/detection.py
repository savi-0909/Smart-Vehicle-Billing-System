import tkinter as tk
from tkinter import messagebox, StringVar, Label, Button, Entry, Toplevel
import cv2
import easyocr
import sqlite3
import numpy as np
import datetime
from PIL import Image, ImageTk

# -------------------- DATABASE SETUP --------------------
conn = sqlite3.connect('parking_system.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (plate_number TEXT PRIMARY KEY, balance REAL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS logs (plate_number TEXT, timestamp TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
conn.commit()

# -------------------- LOAD MODELS --------------------
net = cv2.dnn.readNet("yolo-obj_last.weights", "yolo-obj.cfg")
layer_names = net.getUnconnectedOutLayersNames()
reader = easyocr.Reader(['en'])

# -------------------- MAIN APP FUNCTION --------------------
def open_main_app():
    app = tk.Tk()
    app.title("🅿️ Parking Detection System")
    app.geometry("420x480")
    app.configure(bg="#f4f4f4")

    current_plate = None
    plate_var = StringVar()
    balance_var = StringVar()

    try:
        img = Image.open("logo.png")
        img = img.resize((80, 80))
        logo = ImageTk.PhotoImage(img)
        tk.Label(app, image=logo, bg="#f4f4f4").pack(pady=(10, 5))
    except:
        pass

    tk.Label(app, text="Vehicle Parking System", font=("Segoe UI", 16, "bold"), bg="#f4f4f4", fg="#333").pack(pady=15)

    frame_info = tk.Frame(app, bg="#f4f4f4")
    frame_info.pack()
    tk.Label(frame_info, textvariable=plate_var, font=("Segoe UI", 14), bg="#f4f4f4", fg="#444").pack(pady=5)
    tk.Label(frame_info, textvariable=balance_var, font=("Segoe UI", 14, "bold"), bg="#f4f4f4", fg="#2E7D32").pack(pady=5)
    def show_plate_image(img_path):
        try:
            top = Toplevel()
            top.title("Detected Plate Image")

            img = Image.open(img_path)
            img = img.resize((350, 100))  # Resize to fit nicely
            photo = ImageTk.PhotoImage(img)

            label = Label(top, image=photo)
            label.image = photo  # Keep a reference
            label.pack(padx=10, pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to show image: {e}")

    # --- BUTTON FUNCTIONS ---
    def detect_plate():
        nonlocal current_plate
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Unable to access the camera.")
            return

        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("Error", "Failed to capture image from camera.")
            return

        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (320, 320), swapRB=True, crop=False)
        net.setInput(blob)
        outputs = net.forward(layer_names)

        plate_found = False
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                confidence = max(scores)
                if confidence > 0.3:
                    x, y, w, h = (detection[0:4] * [width, height, width, height]).astype(int)
                    pad_x = int(w * 0.2)
                    pad_y = int(h * 0.2)
                    x1 = max(0, int(x - w / 2) - pad_x)
                    y1 = max(0, int(y - h / 2) - pad_y)
                    x2 = min(width, int(x + w / 2) + pad_x)
                    y2 = min(height, int(y + h / 2) + pad_y)

                    plate_img = frame[y1:y2, x1:x2]

                    # 🧠 Preprocessing
                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    blur = cv2.GaussianBlur(gray, (0, 0), 3)
                    sharp = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)
                    cv2.imwrite("detected_plate.jpg", sharp)

                    # 🔍 OCR
                    ocr_results = reader.readtext("detected_plate.jpg")

                    if ocr_results:
                        full_plate = "".join([t[1].upper().replace(" ", "") for t in ocr_results if len(t[1]) > 2])
                        full_plate = ''.join(filter(str.isalnum, full_plate))

                        if full_plate:
                            current_plate = full_plate
                            cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (full_plate,))
                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO vehicles VALUES (?, ?)", (full_plate, 100.0))
                            conn.commit()
                            update_display()
                            plate_found = True

                            # 🔊 Beep Sound
                            print("\a")

                            # 🖼 Show in Tkinter UI
                            show_plate_image("detected_plate.jpg")
                    break
            if plate_found:
                break

        if not plate_found:
            messagebox.showinfo("Result", "No license plate detected.")

    def update_display():
        if current_plate:
            cursor.execute("SELECT balance FROM vehicles WHERE plate_number = ?", (current_plate,))
            row = cursor.fetchone()
            plate_var.set(f"Plate Number: {current_plate}")
            balance_var.set(f"Balance: ₹{row[0]:.2f}")

    def exit_mall():
        if not current_plate:
            messagebox.showwarning("No vehicle", "Detect a vehicle first.")
            return
        cursor.execute("SELECT balance FROM vehicles WHERE plate_number = ?", (current_plate,))
        row = cursor.fetchone()
        if row and row[0] >= 30:
            new_balance = row[0] - 30
            cursor.execute("UPDATE vehicles SET balance = ? WHERE plate_number = ?", (new_balance, current_plate))
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO logs (plate_number, timestamp) VALUES (?, ?)", (current_plate, timestamp))
            conn.commit()
            update_display()
            messagebox.showinfo("Success", f"₹30 deducted. New balance: ₹{new_balance:.2f}")
        else:
            messagebox.showwarning("Low Balance", "Not enough balance. Please recharge.")

    def recharge_wallet():
        if not current_plate:
            messagebox.showwarning("No vehicle", "Detect a vehicle first.")
            return
        win = Toplevel(app)
        win.title("Recharge Wallet")
        win.geometry("280x160")
        win.configure(bg="#ffffff")

        tk.Label(win, text="Recharge Amount:", font=("Segoe UI", 12), bg="#ffffff").pack(pady=10)
        amt_entry = Entry(win, font=("Segoe UI", 12))
        amt_entry.pack()

        def add_money():
            try:
                amt = float(amt_entry.get())
                cursor.execute("SELECT balance FROM vehicles WHERE plate_number = ?", (current_plate,))
                row = cursor.fetchone()
                if row:
                    new_balance = row[0] + amt
                    cursor.execute("UPDATE vehicles SET balance = ? WHERE plate_number = ?", (new_balance, current_plate))
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("INSERT INTO logs (plate_number, timestamp) VALUES (?, ?)", (current_plate, timestamp))
                    conn.commit()
                    update_display()
                    messagebox.showinfo("Recharged", f"New Balance: ₹{new_balance:.2f}")
                    win.destroy()
            except:
                messagebox.showerror("Invalid", "Enter a valid amount.")

        Button(win, text="Recharge", command=add_money, bg="#4CAF50", fg="white", font=("Segoe UI", 11)).pack(pady=15)

    def show_logs():
        win = Toplevel(app)
        win.title("Detection History")
        win.geometry("350x300")
        win.configure(bg="white")

        tk.Label(win, text="Detected Entries", font=("Segoe UI", 14, "bold"), bg="white").pack(pady=10)
        log_frame = tk.Frame(win, bg="white")
        log_frame.pack()

        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10")
        logs = cursor.fetchall()

        for log in logs:
            tk.Label(log_frame, text=f"{log[0]} - {log[1]}", bg="white", font=("Segoe UI", 10)).pack(anchor="w")

    frame_buttons = tk.Frame(app, bg="#f4f4f4")
    frame_buttons.pack(pady=20)

    tk.Button(frame_buttons, text="🚗 Detect Vehicle", width=20, bg="#2196F3", fg="white", font=("Segoe UI", 11), command=detect_plate).pack(pady=8)
    tk.Button(frame_buttons, text="🏁 Exit Mall (₹30)", width=20, bg="#FF5722", fg="white", font=("Segoe UI", 11), command=exit_mall).pack(pady=8)
    tk.Button(frame_buttons, text="💰 Recharge Wallet", width=20, bg="#673AB7", fg="white", font=("Segoe UI", 11), command=recharge_wallet).pack(pady=8)
    tk.Button(frame_buttons, text="📋 Show Log", width=20, bg="#607D8B", fg="white", font=("Segoe UI", 11), command=show_logs).pack(pady=8)
    tk.Button(frame_buttons, text="❌ Exit App", width=20, bg="#9E9E9E", fg="white", font=("Segoe UI", 11), command=app.destroy).pack(pady=8)

    app.mainloop()

# -------------------- LOGIN SCREEN --------------------
def login_window():
    def login():
        uname = username.get()
        pwd = password.get()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (uname, pwd))
        if cursor.fetchone():
            messagebox.showinfo("Login Success", f"Welcome, {uname}!")
            root.destroy()
            open_main_app()
        else:
            messagebox.showerror("Error", "Invalid credentials.")

    def open_register():
        root.destroy()
        register_window()

    root = tk.Tk()
    root.title("Login - License Plate App")
    root.geometry("350x300")
    root.configure(bg="#f0f8ff")

    tk.Label(root, text="Login", font=("Segoe UI", 18, "bold"), bg="#f0f8ff").pack(pady=10)
    username = StringVar()
    password = StringVar()

    tk.Label(root, text="Username", font=("Segoe UI", 12), bg="#f0f8ff").pack(pady=(10, 0))
    tk.Entry(root, textvariable=username, font=("Segoe UI", 12)).pack(pady=5)
    tk.Label(root, text="Password", font=("Segoe UI", 12), bg="#f0f8ff").pack(pady=(10, 0))
    tk.Entry(root, textvariable=password, show="*", font=("Segoe UI", 12)).pack(pady=5)

    tk.Button(root, text="Login", font=("Segoe UI", 12), bg="#4CAF50", fg="white", command=login).pack(pady=15)
    tk.Button(root, text="Register", font=("Segoe UI", 12), bg="#FF9800", fg="white", command=open_register).pack(pady=5)

    root.mainloop()

# -------------------- REGISTER SCREEN --------------------
def register_window():
    def register():
        uname = username.get()
        pwd = password.get()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
            conn.commit()
            messagebox.showinfo("Success", "Account created successfully!")
            root.destroy()
            login_window()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

    root = tk.Tk()
    root.title("Register - License Plate App")
    root.geometry("350x300")
    root.configure(bg="#f0f8ff")

    tk.Label(root, text="Register", font=("Segoe UI", 18, "bold"), bg="#f0f8ff").pack(pady=10)
    username = StringVar()
    password = StringVar()

    tk.Label(root, text="Username", font=("Segoe UI", 12), bg="#f0f8ff").pack(pady=(10, 0))
    tk.Entry(root, textvariable=username, font=("Segoe UI", 12)).pack(pady=5)
    tk.Label(root, text="Password", font=("Segoe UI", 12), bg="#f0f8ff").pack(pady=(10, 0))
    tk.Entry(root, textvariable=password, show="*", font=("Segoe UI", 12)).pack(pady=5)

    tk.Button(root, text="Register", font=("Segoe UI", 12), bg="#4CAF50", fg="white", command=register).pack(pady=15)

    root.mainloop()

# -------------------- START APP --------------------
login_window()
