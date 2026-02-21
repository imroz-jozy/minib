
import tkinter as tk
from tkinter import messagebox
from utils.license_utils import get_app_config, save_app_config, verify_serial_no

class SecretWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Secret Configuration")
        self.top.geometry("400x300")
        self.top.transient(parent)
        self.top.grab_set()
        
        self.parent = parent
        self.auth_frame = None
        self.config_frame = None
        
        self.show_password_prompt()

    def show_password_prompt(self):
        self.auth_frame = tk.Frame(self.top, padx=20, pady=20)
        self.auth_frame.pack(fill='both', expand=True)

        tk.Label(self.auth_frame, text="Enter Password:", font=("Arial", 12)).pack(pady=(20, 10))
        
        self.password_var = tk.StringVar()
        self.pass_entry = tk.Entry(self.auth_frame, show="*", textvariable=self.password_var, font=("Arial", 12))
        self.pass_entry.pack(pady=10)
        self.pass_entry.bind('<Return>', lambda e: self.check_password())
        self.pass_entry.focus_set()

        tk.Button(self.auth_frame, text="Unlock", command=self.check_password, width=15).pack(pady=20)

    def check_password(self):
        password = self.password_var.get()
        if password == "Mera.@12345":
            self.auth_frame.destroy()
            self.show_config_ui()
        else:
            messagebox.showerror("Access Denied", "Incorrect Password")
            self.pass_entry.delete(0, tk.END)

    def show_config_ui(self):
        self.config_frame = tk.Frame(self.top, padx=20, pady=20)
        self.config_frame.pack(fill='both', expand=True)
        
        # Load current values from database
        config = get_app_config()
        current_api_key = config.get('openai_api_key', '')
        current_serial = config.get('serial_no', '')

        # API Key Field
        tk.Label(self.config_frame, text="Gemini API Key:").grid(row=0, column=0, sticky='w', pady=5)
        self.api_key_var = tk.StringVar(value=current_api_key)
        tk.Entry(self.config_frame, textvariable=self.api_key_var, width=40).grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # Serial No Field
        tk.Label(self.config_frame, text="License Serial No:").grid(row=2, column=0, sticky='w', pady=5)
        self.serial_var = tk.StringVar(value=current_serial)
        tk.Entry(self.config_frame, textvariable=self.serial_var, width=40).grid(row=3, column=0, columnspan=2, pady=(0, 15))

        # Status Label
        self.status_label = tk.Label(self.config_frame, text="Status: checking...", fg="gray")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)

        # Buttons
        btn_frame = tk.Frame(self.config_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="Save & Verify", command=self.save_and_verify, bg="#DDFFDD").pack(side='left', padx=5)
        tk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side='left', padx=5)

        # Initial Check
        self.verify_current_status()

    def verify_current_status(self):
        valid, msg = verify_serial_no()
        color = "green" if valid else "red"
        self.status_label.config(text=f"Status: {msg}", fg=color)

    def save_and_verify(self):
        new_config = {
            'openai_api_key': self.api_key_var.get().strip(),
            'serial_no': self.serial_var.get().strip()
        }
        
        if save_app_config(new_config):
            valid, msg = verify_serial_no()
            color = "green" if valid else "red"
            self.status_label.config(text=f"Saved. Status: {msg}", fg=color)
            if not valid:
                messagebox.showwarning("License Warning", f"Settings saved but license invalid:\n{msg}")
            else:
                messagebox.showinfo("Success", "Settings saved and License Verified!")
        else:
            messagebox.showerror("Error", "Failed to save configuration.")

def open_secret_window(parent=None):
    # Use active window if parent not provided
    if parent is None:
        parent = tk.Frame() # Dummy fallback
    SecretWindow(parent)
