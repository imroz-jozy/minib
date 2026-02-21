import tkinter as tk
from tkinter import ttk, messagebox
from database.db import create_tables
from utils.busy_utils import upload_party_to_busy

create_tables()

_parent_window = None

def set_parent_window(window):
    global _parent_window
    _parent_window = window

def open_add_party(callback=None, initial_party_name="", initial_gstin_no="", initial_address=""):
    """
    Open Add Party window. Uses Busy AddMaster(2) - opens Busy Add Party form.
    callback receives (party_name, gstin_no, address) - gstin_no/address may be empty.
    """
    if _parent_window is None:
        root = tk._default_root
        if root is None:
            win = tk.Toplevel()
        else:
            win = tk.Toplevel(root)
            win.transient(root)
    else:
        win = tk.Toplevel(_parent_window)
        win.transient(_parent_window)

    try:
        win.attributes('-toolwindow', True)
    except:
        pass

    win.title("Add Party")
    win.geometry("350x120")
    win.resizable(False, False)

    ttk.Label(win, text="Add party via Busy Add Master form.").pack(pady=15, padx=20)

    def add_in_busy():
        busy_success, busy_message, name = upload_party_to_busy()
        if busy_success and name:
            if callback:
                callback(name, "", "")
            messagebox.showinfo("Success", f"Party added: {name}")
            win.destroy()
        elif busy_success:
            messagebox.showinfo("Cancelled", "Add Master cancelled.")
        else:
            messagebox.showerror("Failed", busy_message)

    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=10)

    ttk.Button(btn_frame, text="Add in Busy", width=15, command=add_in_busy).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", width=15, command=win.destroy).pack(side="left", padx=5)
