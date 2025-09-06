import tkinter as tk
from tkinter import messagebox
import sqlite3
import subprocess

# DB setup
conn = sqlite3.connect("parking_system.db")
cursor = conn.cursor()

# Create admin table
cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
)''')
conn.commit()

def register_admin():
    def save_admin():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter all fields.")
            return

        try:
            cursor.execute("INSERT INTO admins VALUES (?, ?)", (username, password))
            conn.commit()
            messagebox.showinfo("Success", "Admin registered successfully.")
            reg_window.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

    reg_window = tk.Toplevel()
    reg_window.title("Register Admin")
    reg_window.geometry("300x200")

    tk.Label(reg_window, text="Username").pack(pady=5)
    username_entry = tk.Entry(reg_window)
    username_entry.pack()

    tk.Label(reg_window, text="Password").pack(pady=5)
    password_entry = tk.Entry(reg_window, show="*")
    password_entry.pack()

    tk.Button(reg_window, text="Register", command=save_admin).pack(pady=15)

def login_admin():
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
    if cursor.fetchone():
        messagebox.showinfo("Login Success", f"Welcome, {username}")
        root.destroy()
        subprocess.Popen(["python", "parking_app.py", username])  # pass username to app
    else:
        messagebox.showerror("Login Failed", "Invalid username or password")

# GUI for login
root = tk.Tk()
root.title("Admin Login")
root.geometry("300x250")

tk.Label(root, text="Admin Login", font=("Segoe UI", 14, "bold")).pack(pady=10)

tk.Label(root, text="Username").pack()
username_entry = tk.Entry(root)
username_entry.pack()

tk.Label(root, text="Password").pack()
password_entry = tk.Entry(root, show="*")
password_entry.pack()

tk.Button(root, text="Login", command=login_admin).pack(pady=10)
tk.Button(root, text="Register", command=register_admin).pack()

root.mainloop()
