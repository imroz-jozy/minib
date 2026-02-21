import tkinter as tk
from tkinter import messagebox
from database.db import get_connection, create_tables
from database.sql_server import get_sql_config, save_sql_config, test_sql_connection

create_tables()

# Store reference to main window
_main_window = None

def set_main_window(root):
    """Set the main window reference for child windows."""
    global _main_window
    _main_window = root

def open_sql_config():
    if _main_window is None:
        root = tk._default_root
        if root is None:
            win = tk.Toplevel()
        else:
            win = tk.Toplevel(root)
            win.transient(root)
    else:
        win = tk.Toplevel(_main_window)
        win.transient(_main_window)
        try:
            win.attributes('-toolwindow', True)
        except:
            pass

    win.title("SQL Server Configuration")
    win.geometry("420x260")
    win.resizable(False, False)

    labels = ["Server", "Database", "Username", "Password"]
    entries = {}

    for i, label in enumerate(labels):
        tk.Label(win, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
        show = "*" if label == "Password" else ""
        ent = tk.Entry(win, width=45, show=show)
        ent.grid(row=i, column=1, padx=10, pady=8)
        entries[label] = ent

    # ---------------- LOAD SAVED CONFIG ----------------
    saved = get_sql_config()
    if saved:
        # saved = (username, password, database_name, server_name)
        entries["Username"].insert(0, saved[0] or "")
        entries["Password"].insert(0, saved[1] or "")
        entries["Database"].insert(0, saved[2] or "")
        entries["Server"].insert(0, saved[3] or "")

    # ---------------- CHECK CONNECTION ----------------
    def check_connection():
        ok, msg = test_sql_connection(
            entries["Username"].get().strip(),
            entries["Password"].get().strip(),
            entries["Database"].get().strip(),
            entries["Server"].get().strip()
        )
        if ok:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Failed", msg)

    # ---------------- SAVE CONFIG ----------------
    def save_config():
        save_sql_config(
            entries["Username"].get().strip(),
            entries["Password"].get().strip(),
            entries["Database"].get().strip(),
            entries["Server"].get().strip()
        )
        messagebox.showinfo("Saved", "SQL Server configuration saved successfully")
        win.destroy()

    # ---------------- BUTTONS ----------------
    btn_frame = tk.Frame(win)
    btn_frame.grid(row=len(labels), columnspan=2, pady=20)

    tk.Button(btn_frame, text="Check Connection", width=16,
              command=check_connection).grid(row=0, column=0, padx=5)

    tk.Button(btn_frame, text="Save", width=16,
              command=save_config).grid(row=0, column=1, padx=5)
