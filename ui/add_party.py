import tkinter as tk
from tkinter import ttk, messagebox
from database.db import get_connection, create_tables
from utils.busy_utils import upload_party_to_busy

create_tables()

# Store reference to parent window (Purchase Voucher)
_parent_window = None

def set_parent_window(window):
    """Set the parent window reference for child windows."""
    global _parent_window
    _parent_window = window

def open_add_party(callback=None, initial_party_name="", initial_gstin_no="", initial_address=""):
    """
    Open Add Party window.
    
    Args:
        callback: Optional function to call when party is saved, receives (party_name, gstin_no, address)
        initial_party_name: Initial value for Party Name field
        initial_gstin_no: Initial value for GSTIN No field
        initial_address: Initial value for Address field
    """
    if _parent_window is None:
        # Fallback: try to get root from any existing window
        root = tk._default_root
        if root is None:
            win = tk.Toplevel()
        else:
            win = tk.Toplevel(root)
            win.transient(root)
    else:
        win = tk.Toplevel(_parent_window)
        win.transient(_parent_window)
    
    # On Windows, prevent child window from appearing in taskbar
    try:
        win.attributes('-toolwindow', True)
    except:
        pass
    
    win.title("Add Party")
    win.geometry("450x300")
    win.resizable(False, False)
    
    # Entry fields
    ttk.Label(win, text="Party Name").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    party_name_entry = ttk.Entry(win, width=35)
    party_name_entry.grid(row=0, column=1, padx=10, pady=10)
    if initial_party_name:
        party_name_entry.insert(0, initial_party_name)
    
    ttk.Label(win, text="GSTIN No").grid(row=1, column=0, padx=10, pady=10, sticky="w")
    gstin_entry = ttk.Entry(win, width=35)
    gstin_entry.grid(row=1, column=1, padx=10, pady=10)
    if initial_gstin_no:
        gstin_entry.insert(0, initial_gstin_no)
    
    ttk.Label(win, text="Address").grid(row=2, column=0, padx=10, pady=10, sticky="nw")
    address_text = tk.Text(win, width=35, height=6, wrap=tk.WORD)
    address_text.grid(row=2, column=1, padx=10, pady=10)
    if initial_address:
        address_text.insert("1.0", initial_address)
    
    # Save callback
    save_callback = callback
    
    def save_party():
        """Upload party to BUSY and close window."""
        party_name = party_name_entry.get().strip()
        gstin_no = gstin_entry.get().strip()
        address = address_text.get("1.0", tk.END).strip()
        
        if not party_name:
            messagebox.showerror("Error", "Party Name is required")
            return
        
        # Upload to BUSY (only Name/PrintName/Group)
        busy_success, busy_message, party_code = upload_party_to_busy(party_name)
        
        if busy_success:
            # Call callback if provided (to reflect in parent UI)
            if save_callback:
                save_callback(party_name, gstin_no, address)
            
            messagebox.showinfo("Success", 
                f"Party uploaded to BUSY successfully!\n"
                f"BUSY Party Code: {party_code if party_code else 'N/A'}")
            win.destroy()
        else:
            messagebox.showerror("Upload Failed", 
                f"Failed to upload party to BUSY:\n{busy_message}")
    
    def cancel():
        """Close window without saving."""
        win.destroy()
    
    # Buttons
    btn_frame = ttk.Frame(win)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
    
    ttk.Button(btn_frame, text="Save Party", width=15, command=save_party).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", width=15, command=cancel).pack(side="left", padx=5)
