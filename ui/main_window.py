import tkinter as tk
import sys
from ui.sql_config import open_sql_config, set_main_window
from ui.purchase_voucher import open_purchase_voucher, set_main_window as set_main_window_pv
from ui.api_config import open_api_config, set_main_window as set_main_window_api

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

        btn_frame = tk.Frame(root)
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="Purchase Voucher",
            width=20,
            command=open_purchase_voucher
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            btn_frame,
            text="SQL Config",
            width=20,
            command=open_sql_config
        ).grid(row=0, column=1, padx=10)

        tk.Button(
            btn_frame,
            text="API Config",
            width=20,
            command=open_api_config
        ).grid(row=1, column=0, padx=10, pady=10)
