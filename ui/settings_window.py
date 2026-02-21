import tkinter as tk
from tkinter import ttk, messagebox
from database.db import get_connection
from utils.setting_keys import SETTING_MRP_WISE, SETTING_SRNO_WISE, SETTING_ACTIVE_DISCOUNT_STRUCT

class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Settings")
        self.window.geometry("400x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # UI Variables
        self.var_mrp_wise = tk.BooleanVar()
        self.var_srno_wise = tk.BooleanVar()
        
        # Fixed Structures
        self.structures = ["Simple Discount", "Compound Discount(P+P+A)"]
        self.selected_structure = None

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)

        # --- General Options ---
        options_frame = ttk.LabelFrame(main_frame, text="General Options", padding=10)
        options_frame.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(options_frame, text="Enable MRP Wise", variable=self.var_mrp_wise).pack(anchor="w", pady=2)
        ttk.Checkbutton(options_frame, text="Enable SrNo Wise", variable=self.var_srno_wise).pack(anchor="w", pady=2)

        # --- Discount Structures ---
        disc_frame = ttk.LabelFrame(main_frame, text="Discount Structure Selection", padding=10)
        disc_frame.pack(fill="both", expand=True, pady=(0, 10))

        ttk.Label(disc_frame, text="Select Active Discount Structure:").pack(anchor="w", pady=(0, 5))

        # List Area
        self.disc_listbox = tk.Listbox(disc_frame, height=5, selectmode=tk.SINGLE)
        self.disc_listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        for struct in self.structures:
            self.disc_listbox.insert(tk.END, struct)

        # --- Footer Buttons ---
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x")

        ttk.Button(footer_frame, text="Save", command=self._save_settings).pack(side="right", padx=5)
        ttk.Button(footer_frame, text="Cancel", command=self.window.destroy).pack(side="right")

    def _load_settings(self):
        conn = get_connection()
        cur = conn.cursor()
        
        # Load MRP Wise
        cur.execute("SELECT value FROM settings WHERE key=?", (SETTING_MRP_WISE,))
        row = cur.fetchone()
        self.var_mrp_wise.set(row[0] == "1" if row else False)

        # Load SrNo Wise
        cur.execute("SELECT value FROM settings WHERE key=?", (SETTING_SRNO_WISE,))
        row = cur.fetchone()
        self.var_srno_wise.set(row[0] == "1" if row else False)

        # Load Active Structure
        cur.execute("SELECT value FROM settings WHERE key=?", (SETTING_ACTIVE_DISCOUNT_STRUCT,))
        row = cur.fetchone()
        active_struct = row[0] if row else "Simple Discount"
        
        # Select in Listbox
        try:
            idx = self.structures.index(active_struct)
            self.disc_listbox.selection_set(idx)
            self.disc_listbox.activate(idx)
        except ValueError:
            # Default to first if unknown
            self.disc_listbox.selection_set(0)

        conn.close()

    def _save_settings(self):
        conn = get_connection()
        cur = conn.cursor()

        # Save MRP Wise
        cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", 
                   (SETTING_MRP_WISE, "1" if self.var_mrp_wise.get() else "0"))
        
        # Save SrNo Wise
        cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", 
                   (SETTING_SRNO_WISE, "1" if self.var_srno_wise.get() else "0"))
        
        # Save Active Structure
        sel = self.disc_listbox.curselection()
        if sel:
            selected_struct = self.structures[sel[0]]
            cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", 
                       (SETTING_ACTIVE_DISCOUNT_STRUCT, selected_struct))
        
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", "Settings saved successfully", parent=self.window)
        self.window.destroy()

def open_settings_window(root):
    SettingsWindow(root)
