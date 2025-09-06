import tkinter as tk
from tkinter import StringVar, Label, Entry, Button, Toplevel
import sqlite3
import cv2
import easyocr
import datetime

# Load YOLO and EasyOCR
net = cv2.dnn.readNet("yolo-obj_last.weights", "yolo-obj.cfg")
layer_names = net.getUnconnectedOutLayersNames()
reader = easyocr.Reader(['en'])

# Database setup
conn = sqlite3.connect("parking_system.db")
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
    plate TEXT PRIMARY KEY,
    name TEXT,
    balance REAL
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS checkins (
    plate TEXT PRIMARY KEY,
    checkin_time TEXT,
    admin TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
    plate TEXT,
    name TEXT,
    checkin TEXT,
    checkout TEXT,
    duration INTEGER,
    fee REAL,
    admin TEXT
)''')
conn.commit()

current_plate = None
checkin_time = None
admin_user = None

# Admin login screen
def login_screen():
    login = tk.Tk()
    login.title("Admin Login")
    login.geometry("600x400")

    tk.Label(login, text="Admin Login", font=("Segoe UI", 18, "bold"), fg="#333", bg="white").pack(pady=10)
    
    uname = StringVar()
    pwd = StringVar()

    # Username input field
    tk.Label(login, text="Username", font=("Segoe UI", 12), bg="white").pack(pady=5)
    tk.Entry(login, textvariable=uname, font=("Segoe UI", 12), width=30).pack(pady=5)

    # Password input field
    tk.Label(login, text="Password", font=("Segoe UI", 12), bg="white").pack(pady=5)
    tk.Entry(login, textvariable=pwd, show='*', font=("Segoe UI", 12), width=30).pack(pady=5)

    # Login button
    def do_login():
        global admin_user
        cursor.execute("SELECT * FROM admins WHERE username=? AND password=?", (uname.get(), pwd.get()))
        if cursor.fetchone():
            admin_user = uname.get()
            login.destroy()
            main_app()
        else:
            tk.Label(login, text="Invalid login", fg="red", bg="white").pack()

    tk.Button(login, text="Login", font=("Segoe UI", 14), bg="#4CAF50", fg="white", command=do_login, width=20, height=2).pack(pady=20)

    login.mainloop()

# GUI main app
def main_app():
    app = tk.Tk()
    app.title("Smart Parking System")
    app.geometry("600x600")

    # Set background color and layout
    app.configure(bg="#f0f0f0")
    
    # Display admin info
    tk.Label(app, text=f"🅿️ Logged in as: {admin_user}", font=("Segoe UI", 10, "italic"), bg="#f0f0f0").pack()
    tk.Label(app, text="Smart Parking App", font=("Segoe UI", 16, "bold"), bg="#f0f0f0").pack(pady=10)

    # Create message display box
    status_text = tk.Text(app, height=10, width=50, font=("Segoe UI", 12), wrap=tk.WORD, state=tk.DISABLED)
    status_text.pack(pady=10)

    def show_message(msg):
        status_text.config(state=tk.NORMAL)
        status_text.insert(tk.END, f"{msg}\n")
        status_text.see(tk.END)
        status_text.config(state=tk.DISABLED)

    def detect_plate():
        global current_plate, checkin_time

        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            show_message("Error: Failed to capture image.")
            return

        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        outputs = net.forward(layer_names)

        for output in outputs:
            for detection in output:
                scores = detection[5:]
                confidence = max(scores)
                if confidence > 0.3:
                    center_x, center_y, w, h = (detection[0:4] * [width, height, width, height]).astype("int")
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    plate_img = frame[y:y+h, x:x+w]

                    if plate_img.size == 0:
                        continue

                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    cv2.imwrite("detected.jpg", gray)

                    result = reader.readtext("detected.jpg")
                    if result:
                        text = ''.join([r[1] for r in result])
                        plate = ''.join(filter(str.isalnum, text.upper()))
                        current_plate = plate

                        cursor.execute("SELECT * FROM vehicles WHERE plate = ?", (plate,))
                        row = cursor.fetchone()

                        if not row:
                            register_user(plate)
                            return

                        checkin_time = datetime.datetime.now()

                        cursor.execute("INSERT OR REPLACE INTO checkins VALUES (?, ?, ?)", (plate, checkin_time.isoformat(), admin_user))
                        conn.commit()
                        show_message(f"✅ Vehicle {plate} entered at {checkin_time.strftime('%H:%M:%S')} by {admin_user}")
                        return

        
        
        show_message("⚠️ No plate detected.")

    def register_user(plate):
        def save_info():
            name = name_var.get()
            try:
                amt = float(balance_var.get())
            except:
                show_message("⚠️ Invalid amount.")
                return

            cursor.execute("INSERT INTO vehicles VALUES (?, ?, ?)", (plate, name, amt))
            conn.commit()
            win.destroy()
            checkin_time_now = datetime.datetime.now()
            cursor.execute("INSERT OR REPLACE INTO checkins VALUES (?, ?, ?)", (plate, checkin_time_now.isoformat(), admin_user))
            conn.commit()
            show_message(f"✅ Vehicle {plate} registered and entered at {checkin_time_now.strftime('%H:%M:%S')} by {admin_user}")

        win = Toplevel(app)
        win.title("Register Vehicle")
        win.geometry("300x200")
        name_var = StringVar()
        balance_var = StringVar()

        Label(win, text=f"New Vehicle Detected\nPlate: {plate}", font=("Segoe UI", 12)).pack(pady=10)
        Label(win, text="Owner Name").pack()
        Entry(win, textvariable=name_var).pack()
        Label(win, text="Recharge Amount").pack()
        Entry(win, textvariable=balance_var).pack()
        Button(win, text="Register", command=save_info).pack(pady=10)

    def checkout():
        global current_plate, checkin_time

        if not current_plate:
            show_message("⚠️ Please detect a vehicle first.")
            return

        cursor.execute("SELECT checkin_time, admin FROM checkins WHERE plate = ?", (current_plate,))
        row = cursor.fetchone()
        if not row:
            show_message("⚠️ No check-in time found.")
            return

        checkin_time = datetime.datetime.fromisoformat(row[0])
        checkin_admin = row[1]
        checkout_time = datetime.datetime.now()
        duration = int((checkout_time - checkin_time).total_seconds())
        fee = duration * 1

        cursor.execute("SELECT balance, name FROM vehicles WHERE plate = ?", (current_plate,))
        balance_row = cursor.fetchone()

        if balance_row[0] < fee:
            show_message("❌ Not enough balance.")
            return

        new_balance = balance_row[0] - fee
        cursor.execute("UPDATE vehicles SET balance = ? WHERE plate = ?", (new_balance, current_plate))
        cursor.execute("DELETE FROM checkins WHERE plate = ?", (current_plate,))
        cursor.execute("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)", (
            current_plate, balance_row[1], checkin_time.isoformat(),
            checkout_time.isoformat(), duration, fee, admin_user
        ))
        conn.commit()

        show_message(f"✅ Checkout for {current_plate} completed.\n"
                     f"Owner: {balance_row[1]} | Duration: {duration}s | Fee: ₹{fee} | Balance: ₹{new_balance}")

        current_plate = None
        checkin_time = None

    def show_logs():
        win = Toplevel(app)
        win.title("Logs")
        win.geometry("500x300")

        logs_frame = tk.Frame(win)
        logs_frame.pack(fill="both", expand=True)

        cursor.execute("SELECT * FROM logs ORDER BY checkout DESC LIMIT 10")
        logs = cursor.fetchall()
        for log in logs:
            Label(logs_frame, text=f"{log[0]} | {log[2][11:19]} - {log[3][11:19]} | ₹{log[5]} | By: {log[6]}", anchor="w").pack()

    Button(app, text="🚗 Detect Vehicle", width=30, bg="#2196F3", fg="white", font=("Segoe UI", 11), command=detect_plate).pack(pady=5)
    Button(app, text="🏁 Checkout", width=30, bg="#4CAF50", fg="white", font=("Segoe UI", 11), command=checkout).pack(pady=5)
    Button(app, text="📋 Show Logs", width=30, bg="#9E9E9E", fg="white", font=("Segoe UI", 11), command=show_logs).pack(pady=5)
    Button(app, text="❌ Exit", width=30, bg="#F44336", fg="white", font=("Segoe UI", 11), command=app.quit).pack(pady=20)
    def recharge_balance():
        win = Toplevel(app)
        win.title("Recharge Wallet")
        win.geometry("300x200")

        plate_var = StringVar()
        amount_var = StringVar()

        Label(win, text="Plate Number").pack(pady=5)
        Entry(win, textvariable=plate_var).pack()

        Label(win, text="Recharge Amount").pack(pady=5)
        Entry(win, textvariable=amount_var).pack()

        def do_recharge():
            plate = plate_var.get().upper()
            try:
                amount = float(amount_var.get())
            except:
                show_message("⚠️ Invalid amount.")
                return

            cursor.execute("SELECT balance FROM vehicles WHERE plate = ?", (plate,))
            row = cursor.fetchone()
            if row:
                new_balance = row[0] + amount
                cursor.execute("UPDATE vehicles SET balance = ? WHERE plate = ?", (new_balance, plate))
                conn.commit()
                show_message(f"💰 Recharge successful. New balance for {plate} is ₹{new_balance}")
                win.destroy()
            else:
                show_message("⚠️ Plate not found.")

        Button(win, text="Recharge", command=do_recharge).pack(pady=10)

    def show_registered_vehicles():
        win = Toplevel(app)
        win.title("Registered Vehicles")
        win.geometry("400x300")

        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()

        for plate, name, balance in vehicles:
            Label(win, text=f"🚗 {plate} | {name} | ₹{balance:.2f}", anchor="w").pack()

    def monthly_report():
        win = Toplevel(app)
        win.title("Monthly Report")
        win.geometry("600x400")

        Label(win, text="Last 30 Days Report", font=("Segoe UI", 14, "bold")).pack(pady=10)

        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
        cursor.execute("SELECT plate, name, checkin, checkout, duration, fee, admin FROM logs WHERE checkout >= ?", (thirty_days_ago,))
        rows = cursor.fetchall()

        total_vehicles = len(rows)
        total_revenue = sum(r[5] for r in rows)

        Label(win, text=f"📦 Total Vehicles: {total_vehicles}", font=("Segoe UI", 12)).pack(pady=5)
        Label(win, text=f"💸 Total Revenue: ₹{total_revenue}", font=("Segoe UI", 12)).pack(pady=5)

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True)

        for r in rows:
            Label(frame, text=f"{r[0]} | ₹{r[5]} | {r[6]} | {r[3][5:16]}", anchor="w").pack()
    Button(app, text="💰 Recharge Balance", width=30, bg="#FFC107", fg="black", font=("Segoe UI", 11), command=recharge_balance).pack(pady=5)
    Button(app, text="📖 Show All Vehicles", width=30, bg="#607D8B", fg="white", font=("Segoe UI", 11), command=show_registered_vehicles).pack(pady=5)
    Button(app, text="📊 Monthly Report", width=30, bg="#3F51B5", fg="white", font=("Segoe UI", 11), command=monthly_report).pack(pady=5)

    app.mainloop()

login_screen()
