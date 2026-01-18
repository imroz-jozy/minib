import tkinter as tk
from tkinter import ttk, messagebox
from database.db import get_connection, create_tables
from utils.autocomplete import create_item_autocomplete
from utils.busy_utils import upload_item_to_busy

create_tables()

# Store reference to parent window (Purchase Voucher)
_parent_window = None

def set_parent_window(window):
    """Set the parent window reference for child windows."""
    global _parent_window
    _parent_window = window

def open_add_item(callback=None, initial_item_name="", initial_unit="", initial_hsn="", initial_tax_category=""):
    """
    Open Add Item window.
    
    Args:
        callback: Optional function to call when item is saved, receives (item_name, unit, hsn, tax_category)
        initial_item_name: Initial value for Item Name field
        initial_unit: Initial value for Unit field
        initial_hsn: Initial value for HSN field
        initial_tax_category: Initial value for Tax Category field
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
    
    win.title("Add Item")
    win.geometry("400x250")
    win.resizable(False, False)
    
    # Entry fields
    fields = ["Item Name", "Unit", "HSN", "Tax Category"]
    entries = {}
    initial_values = {
        "Item Name": initial_item_name,
        "Unit": initial_unit,
        "HSN": initial_hsn,
        "Tax Category": initial_tax_category
    }
    
    for i, field in enumerate(fields):
        ttk.Label(win, text=field).grid(row=i, column=0, padx=10, pady=10, sticky="w")
        
        # Use autocomplete for Unit (mastertype=8) and Tax Category (mastertype=25)
        if field == "Unit":
            unit_autocomplete = create_item_autocomplete(win, mastertype=8, width=30)
            unit_autocomplete.entry.grid(row=i, column=1, padx=10, pady=10)
            # Pre-fill with initial value if provided
            if initial_values.get(field):
                unit_autocomplete.set(initial_values[field])
            entries[field] = unit_autocomplete.entry
        elif field == "Tax Category":
            tax_autocomplete = create_item_autocomplete(win, mastertype=25, width=30)
            tax_autocomplete.entry.grid(row=i, column=1, padx=10, pady=10)
            # Pre-fill with initial value if provided
            if initial_values.get(field):
                tax_autocomplete.set(initial_values[field])
            entries[field] = tax_autocomplete.entry
        else:
            ent = ttk.Entry(win, width=30)
            ent.grid(row=i, column=1, padx=10, pady=10)
            # Pre-fill with initial value if provided
            if initial_values.get(field):
                ent.insert(0, initial_values[field])
            entries[field] = ent
    
    # Save callback
    save_callback = callback
    
    def save_item():
        """Save item data and upload to BUSY."""
        item_name = entries["Item Name"].get().strip()
        unit = entries["Unit"].get().strip()
        hsn = entries["HSN"].get().strip()
        tax_category = entries["Tax Category"].get().strip()
        
        if not item_name:
            messagebox.showerror("Error", "Item Name is required")
            return
        
        # Upload to BUSY ERP
        busy_success, busy_message, item_code = upload_item_to_busy(item_name, unit, hsn, tax_category)
        
        if busy_success:
            # Call callback if provided (for purchase voucher integration)
            if save_callback:
                save_callback(item_name, unit, hsn, tax_category)
            
            messagebox.showinfo("Success", 
                f"Item uploaded to BUSY successfully!\n"
                f"BUSY Item Code: {item_code if item_code else 'N/A'}")
            win.destroy()
        else:
            messagebox.showerror("Upload Failed", 
                f"Failed to upload item to BUSY:\n{busy_message}")
    
    def cancel():
        """Close window without saving."""
        win.destroy()
    
    # Buttons
    btn_frame = ttk.Frame(win)
    btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
    
    ttk.Button(btn_frame, text="Save Item", width=15, command=save_item).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", width=15, command=cancel).pack(side="left", padx=5)
