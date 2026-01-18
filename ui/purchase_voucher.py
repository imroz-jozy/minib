import tkinter as tk
from tkinter import ttk, messagebox
from database.db import get_connection, create_tables
import threading
from tkinter import filedialog
import json
import pdfplumber
import re
from utils.autocomplete import create_item_autocomplete
from database.sql_server import get_item_autofill_data
from datetime import datetime
from utils.pdf_utils import extract_text_from_pdf
from utils.ai_utils import parse_with_openai
from ui.add_item import open_add_item, set_parent_window as set_add_item_parent
from ui.add_party import open_add_party, set_parent_window as set_add_party_parent
from utils.calculation import calculate_amount, calculate_price, calculate_total_amount, calculate_amount_with_tax, calculate_multirate_tax
from utils.busy_utils import upload_purchase_voucher_to_busy


create_tables()

# Store reference to main window
_main_window = None

def set_main_window(root):
    """Set the main window reference for child windows."""
    global _main_window
    _main_window = root

def open_purchase_voucher():
    if _main_window is None:
        # Fallback: try to get root from any existing window
        root = tk._default_root
        if root is None:
            pv = tk.Toplevel()
        else:
            pv = tk.Toplevel(root)
            pv.transient(root)
    else:
        pv = tk.Toplevel(_main_window)
        pv.transient(_main_window)
    
    # On Windows, prevent child window from appearing in taskbar
    try:
        pv.attributes('-toolwindow', True)
    except:
        pass  # Not supported on all platforms
    
    pv.title("Purchase Voucher")
    pv.geometry("1350x850")
    
    # Set parent window for Add Item and Add Party windows
    set_add_item_parent(pv)
    set_add_party_parent(pv)

    # ================= HEADER =================
    header = ttk.LabelFrame(pv, text="Voucher Details")
    header.pack(fill="x", padx=10, pady=5)

    fields = ["Date", "Series", "Voucher No", "Purchase Type", "Party Name"]
    header_entries = {}
    
    # Purchase Type dropdown values
    purchase_type_values = [
        "Central-ItemWise",
        "Central-MultiRate",
        "Central-TaxIncl.",
        "Central-Exempt",
        "Local-ItemWise",
        "Local-MultiRate",
        "Local-TaxIncl.",
        "Local-Exempt"
    ]
    
    # Header fields
    for i, field in enumerate(fields):
        ttk.Label(header, text=field).grid(row=0, column=i*2, padx=5, sticky="w")
        
        # Use Combobox for Purchase Type, Entry for others
        if field == "Purchase Type":
            combo = ttk.Combobox(header, width=18, values=purchase_type_values, state="readonly")
            combo.grid(row=0, column=i*2+1, padx=5)
            combo.current(0)  # Set first item as default
            header_entries[field] = combo
        elif field == "Party Name":
            # Use autocomplete for Party Name (mastertype=2)
            party_autocomplete = create_item_autocomplete(header, mastertype=2, width=15)
            party_autocomplete.entry.grid(row=0, column=i*2+1, padx=5)
            header_entries[field] = party_autocomplete.entry
        else:
            ent = ttk.Entry(header, width=15)
            ent.grid(row=0, column=i*2+1, padx=5)
            if field == "Series":
                ent.insert(0, "Main")
            elif field == "Date":
                # Bind FocusOut to parse and format date
                def on_date_focus_out(event):
                    from database.sql_server import parse_smart_date
                    date_val = event.widget.get()
                    yyyy_mm_dd, dd_mm_yyyy = parse_smart_date(date_val)
                    if dd_mm_yyyy:
                        event.widget.delete(0, tk.END)
                        event.widget.insert(0, dd_mm_yyyy)
                ent.bind("<FocusOut>", on_date_focus_out)
            header_entries[field] = ent
    
    # Add Item and Add Party buttons in header (functions defined after entries)
    btn_header_frame = ttk.Frame(header)
    btn_header_frame.grid(row=0, column=len(fields)*2, padx=10, sticky="e")
    
    # Buttons will be created after entries are defined (see below)
    def on_item_saved(item_name, unit, hsn, tax_category):
        """Callback when item is saved - fill Item Name and HSN fields."""
        if "Item Name" in entries:
            entries["Item Name"].delete(0, tk.END)
            entries["Item Name"].insert(0, item_name)
        if "HSN" in entries:
            entries["HSN"].delete(0, tk.END)
            entries["HSN"].insert(0, hsn)
        if "Tax Category" in entries:
            entries["Tax Category"].delete(0, tk.END)
            entries["Tax Category"].insert(0, tax_category)
        if "Unit" in entries:
            entries["Unit"].delete(0, tk.END)
            entries["Unit"].insert(0, unit)
    
    def on_party_saved(party_name, gstin_no, address):
        """Callback when party is saved - fill Party Name field."""
        if "Party Name" in header_entries:
            header_entries["Party Name"].delete(0, tk.END)
            header_entries["Party Name"].insert(0, party_name)

    # ================= ITEM ENTRY =================
    entry_frame = ttk.LabelFrame(pv, text="Item Entry")
    entry_frame.pack(fill="x", padx=10, pady=5)

    labels = ["Item Name", "Tax Category", "HSN", "Qty", "Unit", "List Price", "Discount", "Price"]
    entries = {}
    item_autocomplete = None  # Store autocomplete reference for callback

    for i, lbl in enumerate(labels):
        ttk.Label(entry_frame, text=lbl).grid(row=0, column=i, padx=5)
        
        # Use autocomplete for Item Name, Tax Category, and Unit
        if lbl == "Item Name":
            item_autocomplete = create_item_autocomplete(entry_frame, mastertype=6, width=14)
            item_autocomplete.entry.grid(row=1, column=i, padx=5)
            entries[lbl] = item_autocomplete.entry
        elif lbl == "Tax Category":
            tax_autocomplete = create_item_autocomplete(entry_frame, mastertype=25, width=14)
            tax_autocomplete.entry.grid(row=1, column=i, padx=5)
            entries[lbl] = tax_autocomplete.entry
        elif lbl == "Unit":
            unit_autocomplete = create_item_autocomplete(entry_frame, mastertype=8, width=14)
            unit_autocomplete.entry.grid(row=1, column=i, padx=5)
            entries[lbl] = unit_autocomplete.entry
        elif lbl == "Price":
            # Price field is readonly (auto-calculated from List Price and Discount)
            ent = ttk.Entry(entry_frame, width=14, state="readonly")
            ent.grid(row=1, column=i, padx=5)
            entries[lbl] = ent
        else:
            ent = ttk.Entry(entry_frame, width=14)
            ent.grid(row=1, column=i, padx=5)
            entries[lbl] = ent
    
    # ---------------- AUTO-CALCULATE PRICE FUNCTION ----------------
    def update_price_field(*args):
        """Update Price field when List Price or Discount changes."""
        try:
            list_price_str = entries["List Price"].get().strip()
            discount_str = entries["Discount"].get().strip()
            qty_str = entries["Qty"].get().strip()
            
            if not list_price_str:
                entries["Price"].config(state="normal")
                entries["Price"].delete(0, tk.END)
                entries["Price"].config(state="readonly")
                return
            
            list_price = float(list_price_str)
            # Pass quantity to calculate_price for proper discount calculation
            # Default to 1 if quantity is not provided or invalid
            try:
                quantity = float(qty_str) if qty_str else 1
            except (ValueError, TypeError):
                quantity = 1
            
            final_price = calculate_price(list_price, discount_str, quantity)
            
            entries["Price"].config(state="normal")
            entries["Price"].delete(0, tk.END)
            entries["Price"].insert(0, str(final_price))
            entries["Price"].config(state="readonly")
        except (ValueError, TypeError):
            entries["Price"].config(state="normal")
            entries["Price"].delete(0, tk.END)
            entries["Price"].config(state="readonly")
    
    # Bind List Price, Discount, and Qty fields to update Price automatically
    entries["List Price"].bind("<KeyRelease>", lambda e: update_price_field())
    entries["Discount"].bind("<KeyRelease>", lambda e: update_price_field())
    entries["Qty"].bind("<KeyRelease>", lambda e: update_price_field())
    
    # ---------------- AUTOFILL FUNCTION ----------------
    def autofill_item_fields(item_name):
        """Auto-fill Unit and Tax Category fields when item is selected."""
        from database.sql_server import parse_smart_date
        
        # Get voucher date from header, default to today if not set
        voucher_date_str = header_entries["Date"].get().strip()
        if not voucher_date_str:
            voucher_date_str = datetime.today().strftime("%Y-%m-%d")
        else:
            # Parse using smart date function
            yyyy_mm_dd, _ = parse_smart_date(voucher_date_str)
            if yyyy_mm_dd:
                voucher_date_str = yyyy_mm_dd
            else:
                voucher_date_str = datetime.today().strftime("%Y-%m-%d")
        
        # Fetch autofill data
        data = get_item_autofill_data(item_name, voucher_date_str)
        if not data:
            return
        
        unit_name, tax_rate = data
        
        # Fill Unit field
        if unit_name and "Unit" in entries:
            entries["Unit"].delete(0, tk.END)
            entries["Unit"].insert(0, unit_name)
        
        # Fill Tax Category field (tax rate as percentage)
        if tax_rate is not None and "Tax Category" in entries:
            entries["Tax Category"].delete(0, tk.END)
            entries["Tax Category"].insert(0, str(tax_rate))
    
    # Set up autofill callback for item autocomplete
    if item_autocomplete:
        item_autocomplete.set_on_select_callback(autofill_item_fields)
    
    # ================= ADD ITEM/PARTY BUTTONS (created after entries are defined) =================
    def open_add_item_with_data():
        """Open Add Item window with current field values pre-filled."""
        item_name = entries.get("Item Name", tk.Entry()).get() if "Item Name" in entries else ""
        unit = entries.get("Unit", tk.Entry()).get() if "Unit" in entries else ""
        hsn = entries.get("HSN", tk.Entry()).get() if "HSN" in entries else ""
        tax_category = entries.get("Tax Category", tk.Entry()).get() if "Tax Category" in entries else ""
        
        # Get values from entry widgets
        if hasattr(item_name, 'get'):
            item_name = item_name.get()
        if hasattr(unit, 'get'):
            unit = unit.get()
        if hasattr(hsn, 'get'):
            hsn = hsn.get()
        if hasattr(tax_category, 'get'):
            tax_category = tax_category.get()
        
        open_add_item(on_item_saved, item_name, unit, hsn, tax_category)
    
    def open_add_party_with_data():
        """Open Add Party window with current party name pre-filled."""
        party_name = header_entries.get("Party Name", tk.Entry()).get() if "Party Name" in header_entries else ""
        if hasattr(party_name, 'get'):
            party_name = party_name.get()
        else:
            party_name = str(party_name) if party_name else ""
        
        open_add_party(on_party_saved, party_name, "", "")
    
    # Create buttons now that entries are defined
    ttk.Button(btn_header_frame, text="Add Item", width=12, 
               command=open_add_item_with_data).pack(side="left", padx=2)
    ttk.Button(btn_header_frame, text="Add Party", width=12, 
               command=open_add_party_with_data).pack(side="left", padx=2)

    # ================= MAIN CONTENT =================
    main_frame = ttk.Frame(pv)
    main_frame.pack(fill="both", expand=True, padx=10)

    # ================= LEFT FRAME (2/3 WIDTH) =================
    left_frame = ttk.Frame(main_frame, width=950)
    left_frame.pack(side="left", fill="y")
    left_frame.pack_propagate(False)

    # ================= BUTTONS (TOP) =================
    btn_frame = ttk.Frame(left_frame)
    btn_frame.pack(fill="x", pady=5)

    # ================= TABLE CONTAINER (FIXED HEIGHT) =================
    table_container = ttk.Frame(left_frame, height=390)
    table_container.pack(fill="x", pady=(5, 10))
    table_container.pack_propagate(False)

    columns = ("SNo", "Item", "Tax Category", "HSN", "Qty", "Unit", "List", "Disc", "Price", "Amount")
    table = ttk.Treeview(
        table_container,
        columns=columns,
        show="headings",
        height=7
    )

    widths = [50, 140, 90, 80, 55, 55, 80, 55, 75, 95]
    for col, w in zip(columns, widths):
        table.heading(col, text=col)
        table.column(col, width=w, anchor="center")

    v_scroll = ttk.Scrollbar(
        table_container, orient="vertical", command=table.yview
    )
    h_scroll = ttk.Scrollbar(
        table_container, orient="horizontal", command=table.xview
    )

    table.configure(
        yscrollcommand=v_scroll.set,
        xscrollcommand=h_scroll.set
    )

    table.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")

    table_container.columnconfigure(0, weight=1)
    
    # ================= TOTAL WIDGET BELOW TABLE =================
    total_frame = ttk.Frame(table_container)
    total_frame.grid(row=2, column=0, columnspan=2, sticky="e", padx=0, pady=(5, 0))
    
    # Calculate column positions to align with Amount column
    # Amount is the last column (index 9)
    # Sum of widths before Amount column
    widths_before_amount = sum(widths[:9])  # Sum of first 9 columns
    amount_column_width = widths[9]  # Width of Amount column
    
    # Create label frame for total
    total_label_frame = ttk.Frame(total_frame)
    total_label_frame.pack(side="right")
    
    ttk.Label(total_label_frame, text="Total:", font=("Arial", 9, "bold")).pack(side="left", padx=(0, 5))
    total_amount_label = ttk.Label(total_label_frame, text="0.00", font=("Arial", 9, "bold"), foreground="blue")
    total_amount_label.pack(side="left")
    
    # Variable to track currently selected row for editing
    selected_row_id = None

    # ================= UPDATE TOTAL AMOUNT FUNCTION =================
    def update_total_amount():
        """Update the total amount label by summing all Amount column values."""
        amounts = []
        for row in table.get_children():
            values = table.item(row)["values"]
            # Amount is the last column (index 9)
            amount_value = values[9] if len(values) > 9 else 0
            amounts.append(amount_value)
        
        total = calculate_total_amount(amounts)
        total_amount_label.config(text=f"{total:.2f}")
    
    # Initialize total to 0.00
    update_total_amount()

    # ================= BILL SUNDRY SECTION =================
    # Wrapper to limit width to half (approx 400px since left_frame is 800)
    bs_wrapper = ttk.Frame(left_frame, width=500)
    bs_wrapper.pack(anchor="w", fill="y", padx=0, pady=5)
    # bs_wrapper.pack_propagate(False) # Removed to allow height to fit content

    bs_frame = ttk.LabelFrame(bs_wrapper, text="Bill Sundry")
    bs_frame.pack(fill="x", pady=0)

    # BS Entries
    bs_entries = {}
    bs_nature_store = {} # Store i1 (nature) for current entry: "Subtractive" if i1=0 else "Additive"
    
    # ---------------- BS LOGIC DECLARATIONS ----------------
    def get_current_item_total():
        """sum of all Item Amounts"""
        amounts = []
        for row in table.get_children():
            values = table.item(row)["values"]
            amount_value = values[9] if len(values) > 9 else 0
            amounts.append(float(amount_value))
        return sum(amounts)

    def calculate_bs_amount(*args):
        """Calculate BS Amount based on Percentage if provided."""
        try:
            pct_str = bs_entries["Percentage"].get().strip()
            if pct_str:
                pct = float(pct_str)
                total_item_amt = get_current_item_total()
                amt = (total_item_amt * pct) / 100
                bs_entries["Amount"].delete(0, tk.END)
                bs_entries["Amount"].insert(0, f"{amt:.2f}")
        except ValueError:
            pass

    # ---------------- UI SETUP ----------------
    ttk.Label(bs_frame, text="Name").grid(row=0, column=0, padx=5)
    
    # Autocomplete for Bill Sundry Name (mastertype=9)
    bs_autocomplete = create_item_autocomplete(bs_frame, mastertype=9, width=12)
    bs_autocomplete.entry.grid(row=1, column=0, padx=5)
    bs_entries["Name"] = bs_autocomplete.entry

    ttk.Label(bs_frame, text="Percentage").grid(row=0, column=1, padx=5)
    ent_pct = ttk.Entry(bs_frame, width=10)
    ent_pct.grid(row=1, column=1, padx=5)
    bs_entries["Percentage"] = ent_pct
    ent_pct.bind("<KeyRelease>", calculate_bs_amount)

    ttk.Label(bs_frame, text="Amount").grid(row=0, column=2, padx=5)
    ent_amt = ttk.Entry(bs_frame, width=10)
    ent_amt.grid(row=1, column=2, padx=5)
    bs_entries["Amount"] = ent_amt

    # Autofill Callback
    def autofill_bs_info(name):
        from database.sql_server import get_bill_sundry_info
        info = get_bill_sundry_info(name)
        if info:
            # i1: 0 means Subtractive, others Additive
            nature = "Subtractive" if info['i1'] == 0 else "Additive"
            bs_nature_store["current"] = nature
            # Could also autofill default percentage if stored in DB, but not requested/standard for now.
    
    bs_autocomplete.set_on_select_callback(autofill_bs_info)

    # BS Buttons
    bs_btn_frame = ttk.Frame(bs_frame)
    bs_btn_frame.grid(row=2, column=0, columnspan=4, pady=5, sticky="w", padx=5)

    # BS Table container
    bs_table_frame = ttk.Frame(bs_wrapper, height=150)
    bs_table_frame.pack(fill="x", pady=5)
    bs_table_frame.pack_propagate(False)

    # Hidden Nature column? Or just store in values but don't show?
    # We'll use 5 columns: SNo, Name, Percentage, Amount, Nature
    bs_columns = ("SNo", "Name", "Percentage", "Amount", "Nature")
    bs_table = ttk.Treeview(
            bs_table_frame,
            columns=bs_columns,
            show="headings",
            height=3
    )
    
    # Reduced widths
    bs_widths = [5, 40, 10, 30, 0] # Nature width 0 to hide it
    for col, w in zip(bs_columns, bs_widths):
        bs_table.heading(col, text=col)
        bs_table.column(col, width=w, anchor="center")
    
    bs_table.column("Nature", stretch=False, minwidth=0, width=0) # Hide Nature column

    bs_v_scroll = ttk.Scrollbar(bs_table_frame, orient="vertical", command=bs_table.yview)
    bs_table.configure(yscrollcommand=bs_v_scroll.set)

    bs_table.pack(side="left", fill="both", expand=True)
    bs_v_scroll.pack(side="right", fill="y")
    
    # ================= GRAND TOTAL SECTION =================
    gt_frame = ttk.Frame(bs_wrapper)
    gt_frame.pack(fill="x", pady=5)
    
    ttk.Label(gt_frame, text="Grand Total:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
    grand_total_label = ttk.Label(gt_frame, text="0.00", font=("Arial", 12, "bold"), foreground="green")
    grand_total_label.pack(side="left")

    def calculate_grand_total():
        item_total = get_current_item_total()
        bs_total = 0.0
        
        for row in bs_table.get_children():
            vals = bs_table.item(row)["values"]
            # vals: SNo, Name, Pct, Amt, Nature
            try:
                amt = float(vals[3])
                nature = vals[4]
                if nature == "Subtractive":
                    bs_total -= amt
                else:
                    bs_total += amt
            except (IndexError, ValueError):
                pass
                
        grand_total = item_total + bs_total
        grand_total_label.config(text=f"{grand_total:.2f}")

    # ================= LOGIC =================
    def next_sno():
        return len(table.get_children()) + 1

    def clear_entries():
        for key, e in entries.items():
            if key == "Price":
                # Price field is readonly, just clear it
                e.config(state="normal")
                e.delete(0, tk.END)
                e.config(state="readonly")
            else:
                e.delete(0, tk.END)

    def add_item():
        """Add new item to table."""
        nonlocal selected_row_id
        # Clear any selected row when adding new item
        if selected_row_id:
            table.selection_remove(selected_row_id)
            selected_row_id = None
        
        qty = entries["Qty"].get()
        price = entries["Price"].get()
        purchase_type = header_entries["Purchase Type"].get()
        tax_text = entries["Tax Category"].get()
        amount = calculate_amount_with_tax(qty, price, tax_text, purchase_type)
        
        table.insert("", "end", values=(
            next_sno(),
            entries["Item Name"].get(),
            entries["Tax Category"].get(),
            entries["HSN"].get(),
            qty,
            entries["Unit"].get(),
            entries["List Price"].get(),
            entries["Discount"].get(),
            price,
            amount
        ))
        clear_entries()
        update_total_amount()

    def resequence():
        for i, row in enumerate(table.get_children(), start=1):
            values = list(table.item(row)["values"])
            values[0] = i
            table.item(row, values=values)

    def populate_entries_from_row(row_id):
        """Populate entry fields from selected table row."""
        nonlocal selected_row_id
        selected_row_id = row_id
        values = table.item(row_id)["values"]
        # values: (SNo, Item, Tax Category, HSN, Qty, Unit, List, Disc, Price, Amount)
        # entries keys: ["Item Name", "Tax Category", "HSN", "Qty", "Unit", "List Price", "Discount", "Price"]
        
        # Map table values to entry fields (skip SNo and Amount)
        entry_keys = list(entries.keys())
        table_values = values[1:-1]  # Skip SNo and Amount
        
        for key, val in zip(entry_keys, table_values):
            if key == "Price":
                # Price field is readonly, handle it specially
                entries[key].config(state="normal")
                entries[key].delete(0, tk.END)
                entries[key].insert(0, str(val))
                entries[key].config(state="readonly")
            else:
                entries[key].delete(0, tk.END)
                entries[key].insert(0, str(val))
        
        # Trigger price calculation after populating List Price and Discount
        update_price_field()
    
    def on_table_select(event):
        """Handle table row selection - populate entry fields automatically."""
        selected = table.selection()
        if selected:
            populate_entries_from_row(selected[0])
    
    # Bind table selection event
    table.bind("<<TreeviewSelect>>", on_table_select)

    def edit_item():
        """Edit the selected row with current entry field values."""
        nonlocal selected_row_id
        
        # Use stored selected_row_id if available, otherwise try current selection
        if selected_row_id is None:
            selected = table.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select a row to edit")
                return
            selected_row_id = selected[0]
        
        if selected_row_id not in table.get_children():
            messagebox.showwarning("Invalid Selection", "Selected row no longer exists")
            selected_row_id = None
            return
        
        # Get current values from entry fields
        qty = entries["Qty"].get()
        price = entries["Price"].get()
        purchase_type = header_entries["Purchase Type"].get()
        tax_text = entries["Tax Category"].get()
        amount = calculate_amount_with_tax(qty, price, tax_text, purchase_type)
        
        # Get original SNo from the row being edited
        original_values = table.item(selected_row_id)["values"]
        original_sno = original_values[0]
        
        # Update the row with new values (preserve SNo)
        table.item(selected_row_id, values=(
            original_sno,  # Keep original SNo
            entries["Item Name"].get(),
            entries["Tax Category"].get(),
            entries["HSN"].get(),
            qty,
            entries["Unit"].get(),
            entries["List Price"].get(),
            entries["Discount"].get(),
            price,
            amount
        ))
        
        # Clear selection and entries
        table.selection_remove(selected_row_id)
        selected_row_id = None
        clear_entries()
        update_total_amount()

    def delete_item():
        selected = table.selection()
        if not selected:
            return
        table.delete(selected[0])
        resequence()
        update_total_amount()

    def insert_item():
        selected = table.selection()
        if selected:
            idx = table.index(selected[0])
        else:
            idx = "end"

        # Temp SNo
        qty = entries["Qty"].get()
        price = entries["Price"].get()
        purchase_type = header_entries["Purchase Type"].get()
        tax_text = entries["Tax Category"].get()
        amount = calculate_amount_with_tax(qty, price, tax_text, purchase_type)
        
        table.insert("", idx, values=(
            0,
            entries["Item Name"].get(),
            entries["Tax Category"].get(),
            entries["HSN"].get(),
            qty,
            entries["Unit"].get(),
            entries["List Price"].get(),
            entries["Discount"].get(),
            price,
            amount
        ))
        clear_entries()
        resequence()
        update_total_amount()

    # ================= BS CRUD LOGIC =================
    def add_bill_sundry():
        sno = len(bs_table.get_children()) + 1
        name = bs_entries["Name"].get()
        # If user typed name manually without autocomplete clicking, check DB?
        # For now assume nature is additive if not found, or try fetch
        nature = bs_nature_store.get("current", "Additive")
        if name and not bs_nature_store.get("current"):
             # Fallback fetch if typed manually
             from database.sql_server import get_bill_sundry_info
             info = get_bill_sundry_info(name)
             if info:
                 nature = "Subtractive" if info['i1'] == 0 else "Additive"
        
        bs_table.insert("", "end", values=(
            sno,
            name,
            bs_entries["Percentage"].get(),
            bs_entries["Amount"].get(),
            nature
        ))
        for e in bs_entries.values():
            e.delete(0, tk.END)
        bs_nature_store["current"] = None # Reset
        calculate_grand_total()

    def edit_bill_sundry():
        selected = bs_table.selection()
        if not selected:
            return
        
        values = bs_table.item(selected[0])["values"]
        # values is (SNo, Name, Percentage, Amount, Nature)
        bs_entries["Name"].delete(0, tk.END)
        bs_entries["Name"].insert(0, values[1])
        bs_entries["Percentage"].delete(0, tk.END)
        bs_entries["Percentage"].insert(0, values[2])
        bs_entries["Amount"].delete(0, tk.END)
        bs_entries["Amount"].insert(0, values[3])
        
        # Restore nature to store so if we save again we know it
        if len(values) > 4:
            bs_nature_store["current"] = values[4]

        bs_table.delete(selected[0])
        
        # Resequence Bill Sundry SNo
        for i, row in enumerate(bs_table.get_children(), start=1):
            vals = list(bs_table.item(row)["values"])
            vals[0] = i
            bs_table.item(row, values=vals)
        calculate_grand_total()

    def delete_bill_sundry():
        selected = bs_table.selection()
        if not selected:
            return
        bs_table.delete(selected[0])
        
        # Resequence
        for i, row in enumerate(bs_table.get_children(), start=1):
            vals = list(bs_table.item(row)["values"])
            vals[0] = i
            bs_table.item(row, values=vals)
        calculate_grand_total()

    def insert_bill_sundry():
        # Insert current entries ABOVE the selected row
        selected = bs_table.selection()
        if selected:
            idx = bs_table.index(selected[0])
        else:
            idx = "end"
        
        name = bs_entries["Name"].get()
        nature = bs_nature_store.get("current", "Additive")
        # Fallback fetch
        if name and not bs_nature_store.get("current"):
             from database.sql_server import get_bill_sundry_info
             info = get_bill_sundry_info(name)
             if info:
                 nature = "Subtractive" if info['i1'] == 0 else "Additive"

        # Temporary SNo (will be fixed by resequence)
        bs_table.insert("", idx, values=(
            0,
            name,
            bs_entries["Percentage"].get(),
            bs_entries["Amount"].get(),
            nature
        ))
        for e in bs_entries.values():
            e.delete(0, tk.END)
        bs_nature_store["current"] = None

        # Resequence
        for i, row in enumerate(bs_table.get_children(), start=1):
            vals = list(bs_table.item(row)["values"])
            vals[0] = i
            bs_table.item(row, values=vals)
        calculate_grand_total()
    
    # Hook into Item updates to refresh Grand Total
    # We should call calculate_grand_total whenever items change too.
    # Modified update_total_amount to also call calculate_grand_total
    old_update_total = update_total_amount
    def new_update_total_amount():
        old_update_total()
        calculate_grand_total()
    # Override
    update_total_amount = new_update_total_amount

    def apply_tax():
        """Calculate and apply taxes as Bill Sundries for MultiRate purchase types."""
        purchase_type = header_entries["Purchase Type"].get()
        if "MultiRate" not in purchase_type:
            messagebox.showinfo("Info", "Apply Tax is only available for MultiRate purchase types.")
            return

        # Prepare items for calculation
        items_data = []
        for row in table.get_children():
            # (SNo, Item, Tax Category, HSN, Qty, Unit, List, Disc, Price, Amount)
            vals = table.item(row)["values"]
            try:
                # Amount is at index 9
                if not vals[9]: continue
                amt = float(vals[9])
                
                # Extract Tax Rate from Tax Category (index 2)
                # Assume Tax Category contains number like "GST 18%", "18%", etc.
                tax_cat = str(vals[2])
                match = re.search(r'(\d+(\.\d+)?)', tax_cat)
                rate = float(match.group(1)) if match else 0.0
                
                items_data.append({'amount': amt, 'tax_rate': rate})
            except (ValueError, IndexError):
                continue
        
        if not items_data:
            messagebox.showwarning("Warning", "No valid items found to calculate tax.")
            return

        # Prepare existing Bill Sundries (exclude existing taxes to avoid double counting)
        bs_data = []
        rows_to_delete = []
        
        for row in bs_table.get_children():
            vals = bs_table.item(row)["values"]
            # (SNo, Name, Percentage, Amount, Nature)
            name = str(vals[1])
            try:
                amt = float(vals[3]) if vals[3] else 0.0
                nature = str(vals[4]) if len(vals) > 4 else "Additive"
                
                # Identify tax entries to remove/ignore
                # Heuristic: names containing "GST" are likely taxes
                # Cover both old format "GST @" and new format "IGST", "CGST", etc.
                if "GST" in name:
                    rows_to_delete.append(row)
                else:
                    bs_data.append({'amount': amt, 'nature': nature})
            except ValueError:
                pass
        
        # Calculate new taxes
        new_taxes = calculate_multirate_tax(items_data, bs_data, purchase_type)
        
        if not new_taxes:
            messagebox.showinfo("Info", "No taxes calculated.")
            return
            
        # Delete old tax entries
        for row in rows_to_delete:
            bs_table.delete(row)
            
        # Append new taxes
        start_sno = len(bs_table.get_children()) + 1
        for i, tax in enumerate(new_taxes):
            # Taxes are usually Additive
            bs_table.insert("", "end", values=(
                start_sno + i,
                tax['name'],
                tax['rate'], # Put rate in Percentage column
                tax['amount'],
                "Additive" 
            ))
            
        # Resequence SNo
        for i, row in enumerate(bs_table.get_children(), start=1):
            vals = list(bs_table.item(row)["values"])
            vals[0] = i
            bs_table.item(row, values=vals)
            
        calculate_grand_total()
        messagebox.showinfo("Success", "Tax applied successfully.")

    # Connect BS Buttons
    ttk.Button(bs_btn_frame, text="Add", command=add_bill_sundry).pack(side="left", padx=2)
    ttk.Button(bs_btn_frame, text="Insert", command=insert_bill_sundry).pack(side="left", padx=2)
    ttk.Button(bs_btn_frame, text="Edit", command=edit_bill_sundry).pack(side="left", padx=2)
    ttk.Button(bs_btn_frame, text="Delete", command=delete_bill_sundry).pack(side="left", padx=2)
    ttk.Button(bs_btn_frame, text="Apply Tax", command=apply_tax).pack(side="left", padx=2)




    def fill_voucher_data(data):
        if isinstance(data, str):
            messagebox.showerror("Import Error", data)
            return

        if not data:
             messagebox.showerror("Import Error", "No data returned.")
             return

        # Header
        # Mapping: JSON key -> Entry Widget
        header_map = {
            "party_name": "Party Name",
            "date": "Date",
            "voucher_no": "Voucher No",
            "purchase_type": "Purchase Type"
        }
        
        for k, v in header_map.items():
            if k in data and data[k]:
                value = str(data[k])
                # Handle Combobox differently from Entry
                if isinstance(header_entries[v], ttk.Combobox):
                    # For Combobox, try to set the value
                    if value in purchase_type_values:
                        header_entries[v].set(value)
                    else:
                        # If value not in list, set it anyway (may not work but try)
                        header_entries[v].set(value)
                else:
                    # For Entry widgets
                    header_entries[v].delete(0, tk.END)
                    header_entries[v].insert(0, value)

        # Items
        if "items" in data:
            # Clear existing items? Let's append actually, or clear? User usually wants to fill a blank voucher.
            # Let's clear to be safe if it's a fresh import.
            for item in table.get_children():
                table.delete(item)
                
            for item in data["items"]:
                # Ensure all fields exist
                i_name = item.get("item_name", "")
                tax_cat = item.get("tax_category", "")
                hsn = item.get("hsn", "")
                qty = item.get("qty", 0)
                unit = item.get("unit", "")
                l_price = item.get("list_price", 0)
                disc = item.get("discount", 0)
                price = item.get("price", 0)
                amt = item.get("amount", 0)
                
                # Recalculate if some missing?
                if not amt and qty and price:
                    amt = float(qty) * float(price)

                table.insert("", "end", values=(
                    next_sno(),
                    i_name,
                    tax_cat,
                    hsn,
                    qty,
                    unit,
                    l_price,
                    disc,
                    price,
                    amt
                ))
            resequence()

        # Bill Sundry
        if "bill_sundry" in data:
            for item in bs_table.get_children():
                bs_table.delete(item)
                
            for bs in data["bill_sundry"]:
                name = bs.get("name", "")
                pct = bs.get("percentage", 0)
                amt = bs.get("amount", 0)
                
                # Try to fetch nature
                nature = "Additive"
                if name:
                     try:
                         from database.sql_server import get_bill_sundry_info
                         info = get_bill_sundry_info(name)
                         if info and info['i1'] == 0:
                             nature = "Subtractive"
                     except:
                         pass

                bs_table.insert("", "end", values=(
                    len(bs_table.get_children()) + 1,
                    name,
                    pct,
                    amt,
                    nature
                ))
        
        # Update totals after filling data
        update_total_amount()

        messagebox.showinfo("Success", "Invoice data imported successfully!")

    def import_pdf_invoice():
        pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not pdf_path:
            return

        def task():
            text = extract_text_from_pdf(pdf_path)
            if not text:
                pv.after(0, lambda: messagebox.showwarning(
                    "Warning", "PDF read failed"
                ))
                return

            # ✅ ONLY ONE AI CALL
            data = parse_with_openai(text)

            # ✅ Fill UI on main thread
            pv.after(0, lambda: fill_voucher_data(data))

        threading.Thread(target=task, daemon=True).start()


    def save_items():
        try:
            # Format date to DD-MM-YYYY for BUSY
            date_str = header_entries["Date"].get().strip()
            if date_str:
                # Try to parse and convert date format
                try:
                    # Try parsing common formats
                    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            date_str = dt.strftime("%d-%m-%Y")
                            break
                        except ValueError:
                            continue
                except:
                    pass  # Use date as-is if parsing fails
            
            # Collect voucher data for BUSY upload
            voucher_data = {
                'date': date_str or datetime.today().strftime("%d-%m-%Y"),
                'series': header_entries["Series"].get() or "Main",
                'voucher_no': header_entries["Voucher No"].get(),
                'purchase_type': header_entries["Purchase Type"].get(),
                'party_name': header_entries["Party Name"].get(),
                'items': [],
                'bill_sundries': []
            }
            
            # Collect Purchase Items for BUSY upload
            for row in table.get_children():
                data = table.item(row)["values"]
                # data corresponds to: (SNo, Item, Tax Category, HSN, Qty, Unit, List, Disc, Price, Amount)
                # Extract tax percentage from tax_category (could be "12", "12%", "GST 12%", etc.)
                tax_category = str(data[2] or "").strip()
                st_percent = "0"
                try:
                    # Try to extract numeric value from tax_category
                    tax_match = re.search(r'(\d+(?:\.\d+)?)', tax_category)
                    if tax_match:
                        st_percent = tax_match.group(1)
                except:
                    pass
                
                # Calculate tax amount if possible (amount - (amount / (1 + tax_rate/100)))
                st_amount = "0"
                tax_before_surcharge = "0"
                try:
                    amount_val = float(data[9] or 0)
                    if st_percent and float(st_percent) > 0:
                        # Calculate tax before surcharge (approximate)
                        tax_rate = float(st_percent) / 100
                        tax_before_surcharge_val = amount_val * tax_rate / (1 + tax_rate)
                        st_amount_val = tax_before_surcharge_val
                        tax_before_surcharge = str(round(tax_before_surcharge_val, 2))
                        st_amount = str(round(st_amount_val, 2))
                except:
                    pass
                
                voucher_data['items'].append({
                    'item_name': data[1] or "",
                    'unit_name': data[5] or "",  # Changed from 'unit' to 'unit_name'
                    'qty': str(data[4] or "0"),
                    'list_price': str(data[6] or "0"),
                    'compound_discount': str(data[7] or ""),  # Changed from 'discount' to 'compound_discount'
                    'price': str(data[8] or "0"),
                    'amt': str(data[9] or "0"),  # Changed from 'amount' to 'amt'
                    'st_amount': st_amount,
                    'st_percent': st_percent,
                    'tax_before_surcharge': tax_before_surcharge,
                    'tax_category': tax_category  # Added for MultiRate support
                    # Note: 'mc' (Master/Cost Center) is optional and not included
                })

            # Collect Bill Sundries for BUSY upload
            for row in bs_table.get_children():
                data = bs_table.item(row)["values"]
                # data: (SNo, Name, Percentage, Amount, Nature)
                voucher_data['bill_sundries'].append({
                    'name': data[1] or "",
                    'percent_val': str(data[2] or "0"),  # Changed from 'percentage' to 'percent_val'
                    'amount': str(data[3] or "0")
                })

            # Upload to BUSY ERP via XML
            busy_success, busy_message, voucher_code = upload_purchase_voucher_to_busy(voucher_data)
            
            if busy_success:
                messagebox.showinfo("Success", 
                    f"Voucher uploaded to BUSY successfully!\n"
                    f"BUSY Voucher Code: {voucher_code if voucher_code else 'N/A'}")
            else:
                messagebox.showerror("Upload Failed", 
                    f"Failed to upload voucher to BUSY:\n{busy_message}")
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to upload voucher: {str(e)}")

    # ================= BUTTONS =================
    # ================= BUTTONS =================
    ttk.Button(btn_frame, text="Add", width=10, command=add_item).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Insert", width=10, command=insert_item).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Edit", width=10, command=edit_item).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Delete", width=10, command=delete_item).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Import PDF", width=12, command=lambda: import_pdf_invoice()).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Save", width=10, command=save_items).pack(side="left", padx=5)
