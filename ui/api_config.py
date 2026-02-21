import tkinter as tk
from tkinter import messagebox
import json
import os
from database.db import get_connection, create_tables
from database.api_config import get_api_config, test_api_connection


create_tables()

# Store reference to main window
_main_window = None

def set_main_window(root):
    """Set the main window reference for child windows."""
    global _main_window
    _main_window = root

def get_api_key():
    """
    Get API key from database (app_config table first, then api_config table)
    Falls back to config.json if database doesn't have a valid key
    Maintains backward compatibility with purchase_voucher.py
    """
    # First try app_config table (new location for OpenAI API key)
    try:
        from database.app_config import get_app_config
        config = get_app_config()
        if config and config[0] and config[0].strip() and config[0].strip() != '0':
            return config[0].strip()
    except Exception as e:
        print(f"Error reading app_config: {e}")
    
    # Second try api_config table (old location, kept for compatibility)
    config = get_api_config()
    if config and config[2] and config[2].strip() and config[2].strip() != '0':  # config[2] is password field
        return config[2].strip()
    
    # Fall back to config.json for backward compatibility
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
                api_key = config_data.get("openai_api_key")
                if api_key and api_key.strip():
                    return api_key.strip()
        except Exception as e:
            print(f"Error reading config.json: {e}")
    
    return None

def open_api_config():
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
    
    win.title("API Configuration")
    win.geometry("380x250")
    win.resizable(False, False)

    labels = ["URL", "Username", "Password"]
    entries = {}

    for i, label in enumerate(labels):
        tk.Label(win, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
        ent = tk.Entry(win, show="*" if label == "Password" else "", width=30)
        ent.grid(row=i, column=1, padx=10, pady=8)
        entries[label] = ent

    # ---------------- LOAD SAVED CONFIG ---------------- 
    saved = get_api_config()
    if saved:
        entries["URL"].insert(0, saved[0] or "")
        entries["Username"].insert(0, saved[1] or "")
        entries["Password"].insert(0, saved[2] or "")

    # ---------------- CHECK CONNECTION ---------------- 
    def check_connection():
        ok, msg = test_api_connection(
            entries["URL"].get(),
            entries["Username"].get(),
            entries["Password"].get()
        )

        if ok:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Failed", msg)

    # ---------------- SAVE CONFIG ---------------- 
    def save_config():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM api_config")

        cur.execute("""
            INSERT INTO api_config
            (id, url, username, password)
            VALUES (1, ?, ?, ?)
        """, (
            entries["URL"].get(),
            entries["Username"].get(),
            entries["Password"].get()
        ))

        conn.commit()
        conn.close()

        messagebox.showinfo("Saved", "API configuration saved successfully")
        win.destroy()

    # ---------------- BUTTONS ---------------- 
    btn_frame = tk.Frame(win)
    btn_frame.grid(row=len(labels), columnspan=2, pady=20)

    tk.Button(btn_frame, text="Check Connection", width=16,
              command=check_connection).grid(row=0, column=0, padx=5)

    tk.Button(btn_frame, text="Save", width=16,
              command=save_config).grid(row=0, column=1, padx=5)
