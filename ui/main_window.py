import tkinter as tk
import sys
from ui.sql_config import open_sql_config, set_main_window
from ui.purchase_voucher import open_purchase_voucher, set_main_window as set_main_window_pv
from ui.api_config import open_api_config, set_main_window as set_main_window_api
from ui.secret_window import open_secret_window
from ui.settings_window import open_settings_window
from utils.license_utils import verify_serial_no
from tkinter import messagebox

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("MiNI b - Accounting")
        self.root.geometry("500x300")
        
        # Set main window reference for child windows
        set_main_window(root)
        set_main_window_pv(root)
        set_main_window_api(root)

        # Load Logo/Icon
        import os
        try:
            # Go up one level from 'ui' to 'minib' root, then 'assets'
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            img_path = os.path.join(base_dir, 'assets', 'logo.png')
            
            self.logo_image = tk.PhotoImage(file=img_path)
            
            # Set Window Icon
            root.iconphoto(False, self.logo_image)
            
            # Set Main Logo (Background visual)
            tk.Label(root, image=self.logo_image).pack(pady=10)
            
        except Exception as e:
            print(f"Failed to load logo: {e}")
            tk.Label(
                root,
                text="MiNI b",
                font=("Arial", 22, "bold")
            ).pack(pady=30)

        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack()

        self.btn_purchase = tk.Button(
            self.btn_frame,
            text="Purchase Voucher",
            width=20,
            command=open_purchase_voucher
        )
        self.btn_purchase.grid(row=0, column=0, padx=10)

        self.btn_sql = tk.Button(
            self.btn_frame,
            text="SQL Config",
            width=20,
            command=open_sql_config
        )
        self.btn_sql.grid(row=0, column=1, padx=10)

        self.btn_api = tk.Button(
            self.btn_frame,
            text="API Config",
            width=20,
            command=open_api_config
        )
        self.btn_api.grid(row=1, column=0, padx=10, pady=10)

        self.btn_settings = tk.Button(
            self.btn_frame,
            text="Settings",
            width=20,
            command=lambda: open_settings_window(root)
        )
        self.btn_settings.grid(row=1, column=1, padx=10, pady=10)

        # Secret Window Shortcut (Ctrl+Shift+I)
        # Use bind_all to ensure it works regardless of focus
        root.bind_all('<Control-I>', lambda e: open_secret_window(root)) # Ctrl+Shift+I maps to Control-I in some contexts?
        root.bind_all('<Control-Shift-I>', lambda e: open_secret_window(root))
        root.bind_all('<Control-Shift-i>', lambda e: open_secret_window(root))

        # Perform License Check
        self.check_license()

    def set_app_state(self, enabled):
        state = "normal" if enabled else "disabled"
        self.btn_purchase.config(state=state)
        # We might want to keep SQL config enabled so they can fix DB connection?
        # But User said "Software not work". 
        # Let's keep SQL Config enabled to allow setup, but disable Purchase Voucher.
        self.btn_purchase.config(state=state)
        # self.btn_sql.config(state=state) # Keep SQL enabled to allow fixing?
        # self.btn_api.config(state=state) # Keep API enabled?
        
        # Actually user said "software not work". Let's disable Purchase Voucher specifically as that's the main function.
        # But if SQL config is wrong, license check fails. So need SQL config openable.
        # Let's disable Purchase Voucher and API Config.
        if not enabled:
             self.btn_purchase.config(state="disabled")
             self.btn_api.config(state="disabled")
        else:
             self.btn_purchase.config(state="normal")
             self.btn_api.config(state="normal")
        

    def check_license(self):
        valid, msg = verify_serial_no()
        if not valid:
            self.set_app_state(False)
            messagebox.showerror("License Error", f"License Verification Failed:\n{msg}\n\nPlease contact support or press Ctrl+Shift+I to configure.")
        else:
            self.set_app_state(True)
