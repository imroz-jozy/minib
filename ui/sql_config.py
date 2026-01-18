import tkinter as tk
from tkinter import messagebox
from database.db import get_connection, create_tables
from database.sql_server import get_sql_config, test_sql_connection

create_tables()

# Store reference to main window
_main_window = None

def set_main_window(root):
    """Set the main window reference for child windows."""
    global _main_window
    _main_window = root

def open_sql_config():
    if _main_window is None:
        # Fallback: try to get root from any existing window
        root = tk._default_root
        if root is None:
            win = tk.Toplevel()
        else:
            win = tk.Toplevel(root)
            win.transient(root)
    else:
        win = tk.Toplevel(_main_window)
        win.transient(_main_window)
        # On Windows, this helps prevent taskbar entry
        try:
            win.attributes('-toolwindow', True)
        except:
            pass  # Not supported on all platforms
    
    win.title("SQL Configuration")
    win.geometry("380x300")
    win.resizable(False, False)

    labels = ["Username", "Password", "Database Name", "Server Name"]
    entries = {}

    for i, label in enumerate(labels):
        tk.Label(win, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
        ent = tk.Entry(win, show="*" if label == "Password" else "")
        ent.grid(row=i, column=1, padx=10, pady=8)
        entries[label] = ent

    # ---------------- LOAD SAVED CONFIG ----------------
    saved = get_sql_config()
    if saved:
        entries["Username"].insert(0, saved[0])
        entries["Password"].insert(0, saved[1])
        entries["Database Name"].insert(0, saved[2])
        entries["Server Name"].insert(0, saved[3])
    else:
        entries["Server Name"].insert(0, "localhost")

    # ---------------- CHECK CONNECTION ----------------
    def check_connection():
        ok, msg = test_sql_connection(
            entries["Username"].get(),
            entries["Password"].get(),
            entries["Database Name"].get(),
            entries["Server Name"].get()
        )

        if ok:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Failed", msg)

    # ---------------- SAVE CONFIG ----------------
    def save_config():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM sql_config")

        cur.execute("""
            INSERT INTO sql_config
            (id, username, password, database_name, server_name)
            VALUES (1, ?, ?, ?, ?)
        """, (
            entries["Username"].get(),
            entries["Password"].get(),
            entries["Database Name"].get(),
            entries["Server Name"].get()
        ))

        conn.commit()
        conn.close()

        messagebox.showinfo("Saved", "SQL configuration saved successfully")
        win.destroy()

    # ---------------- BUTTONS ----------------
    btn_frame = tk.Frame(win)
    btn_frame.grid(row=len(labels), columnspan=2, pady=20)

    tk.Button(btn_frame, text="Check Connection", width=16,
              command=check_connection).grid(row=0, column=0, padx=5)

    tk.Button(btn_frame, text="Save", width=16,
              command=save_config).grid(row=0, column=1, padx=5)
