"""
Calculation functions for Purchase Voucher.
All calculations are centralized here and can be extended based on purchase type.
"""

def calculate_amount(qty, price):
    """
    Calculate amount from quantity and price.
    
    Args:
        qty: Quantity (can be string or number)
        price: Price (can be string or number)
    
    Returns:
        float: Calculated amount (qty * price), or 0 if invalid inputs
    """
    try:
        qty_float = float(qty) if qty else 0
        price_float = float(price) if price else 0
        return qty_float * price_float
    except (ValueError, TypeError):
        return 0.0


def calculate_amount_with_tax(qty, price, tax_text, purchase_type):
    """
    Calculate amount including tax for itemwise purchase types.
    If purchase_type contains "itemwise" (local/central), tax is applied.
    """
    base = calculate_amount(qty, price)

    try:
        pt = purchase_type.lower() if purchase_type else ""
    except AttributeError:
        pt = ""

    # Apply tax only for itemwise purchase types
    if "itemwise" in pt:
        tax_str = (tax_text or "").strip()
        if tax_str.endswith("%"):
            tax_str = tax_str[:-1]
        try:
            tax_rate = float(tax_str) if tax_str else 0.0
        except (ValueError, TypeError):
            tax_rate = 0.0
        base += base * (tax_rate / 100.0)

    return round(base, 2)


def calculate_price(list_price, discount_text, quantity=1, is_simple_discount=False):
    """
    Calculate final price after applying discount(s).
    
    Args:
        list_price: Original list price (can be string or number)
        discount_text: Discount string
        quantity: Quantity for flat amount discount calculation (default: 1)
        is_simple_discount: Boolean, if True use Simple Discount logic
    
    Returns:
        float: Final per-unit price after discounts
    """
    try:
        price = float(list_price) if list_price else 0.0
        qty = float(quantity) if quantity else 1.0
    except (ValueError, TypeError):
        return 0.0
    
    if not discount_text or not discount_text.strip():
        return round(price, 2)
    
    discount_text = discount_text.strip()
    
    if is_simple_discount:
        # Simple Discount Logic:
        # - "5" -> 5% discount
        # - "0+5" -> 5 amount discount (flat off per unit? or total? usually per unit in simple disc context or flattened)
        # User said: "if i enter 5 then 5 percent less"
        # "if ia add 0+5 then value 5 is less from list price simple" -> Implies flat amount off LIST PRICE (per unit)
        
        if "+" in discount_text:
            # Check for amount pattern "0+X"
            parts = discount_text.split("+")
            if len(parts) == 2 and parts[0].strip() == "0":
                try:
                    amount = float(parts[1].strip())
                    price -= amount
                except ValueError:
                    pass
            elif len(parts) >= 2:
                 # Fallback for "5+0" or other? Assuming only "0+X" triggers amount for now based on user request.
                 # User said "0+5".
                 # If user enters "5+5" in simple mode, what happens? 
                 # User said "simple discount percentage OR amount". 
                 # So likely only one or the other.
                 pass
        else:
            # Percentage
            try:
                # Remove % if present
                val_str = discount_text.replace("%", "").strip()
                percent = float(val_str)
                price -= price * (percent / 100)
            except ValueError:
                pass
            
        return round(price, 2)

    else:
        # Compound Discount (P+P+A) Logic
        # Existing logic handles X+Y+Z, X+Y, X
        
        parts = discount_text.split("+")
        
        if len(parts) >= 3:
            # Format: X+Y+Z
            try:
                percent1 = float(parts[0].strip()) if parts[0].strip() else 0.0
                percent2 = float(parts[1].strip()) if parts[1].strip() else 0.0
                amount = float(parts[2].strip()) if parts[2].strip() else 0.0
                
                if percent1 > 0:
                    price -= price * (percent1 / 100)
                if percent2 > 0:
                    price -= price * (percent2 / 100)
                
                # compound amount is usually on total, but user said "Compound Discount(P+P+A)"
                # My existing logic did amount on TOTAL (qty*price).
                # User's simple logic did amount on PRICE ("value 5 is less from list price").
                # Let's keep existing compound logic as is since user said "use current structure".
                if amount > 0:
                    total = price * qty
                    total -= amount
                    price = total / qty if qty > 0 else 0.0
            except ValueError:
                pass
        elif len(parts) == 2:
             # Format: X+Y (both percent)
            try:
                percent1 = float(parts[0].strip()) if parts[0].strip() else 0.0
                percent2 = float(parts[1].strip()) if parts[1].strip() else 0.0
                
                if percent1 > 0:
                    price -= price * (percent1 / 100)
                if percent2 > 0:
                    price -= price * (percent2 / 100)
            except ValueError:
                pass
        else:
             # Single value -> treat as percent
             try:
                val_str = discount_text.replace("%", "").strip()
                percent = float(val_str)
                price -= price * (percent / 100)
             except ValueError:
                pass

        return round(price, 2)


def calculate_total_amount(amounts):
    """
    Calculate total from a list of amount values.
    
    Args:
        amounts: List of amount values (can be strings or numbers)
    
    Returns:
        float: Sum of all amounts, rounded to 2 decimal places
    """
    total = 0.0
    for amount in amounts:
        try:
            total += float(amount) if amount else 0.0
        except (ValueError, TypeError):
            continue
    return round(total, 2)


def calculate_multirate_tax(items, bill_sundries, purchase_type):
    """
    Calculate GST breakup based on items and other bill sundries (freight, discount, etc.).
    
    Logic:
    1. Distribute bill sundries (Additive/Subtractive) to items proportionally to item value.
    2. Calculate taxable value for each item.
    3. Group items by tax rate.
    4. Calculate tax for each rate.
    
    Args:
        items: List of dicts [{'amount': float, 'tax_rate': float}, ...]
        bill_sundries: List of dicts [{'amount': float, 'nature': 'Additive'/'Subtractive'}, ...]
        purchase_type: string containing 'local' or 'central'
        
    Returns:
        List of dicts [{'name': str, 'rate': float, 'amount': float}, ...] representing calculated tax BS entries.
    """
    total_item_value = sum(item['amount'] for item in items)
    
    if total_item_value == 0:
        return []

    # Calculate net bill sundry amount
    # But as per formula, we need to distribute EACH bill sundry or net total?
    # User formula: "ratio = item.value / total_value ... taxable = item.value + freight_share"
    # This implies we distribute the net bill sundry amount.
    
    total_bs_additive = sum(bs['amount'] for bs in bill_sundries if bs['nature'] == 'Additive')
    total_bs_subtractive = sum(bs['amount'] for bs in bill_sundries if bs['nature'] == 'Subtractive')
    net_bs_amount = total_bs_additive - total_bs_subtractive
    
    # Group taxes
    # Key: Rate, Value: {'taxable': float}
    tax_groups = {}
    
    is_local = "local" in purchase_type.lower()
    
    for item in items:
        ratio = item['amount'] / total_item_value
        bs_share = net_bs_amount * ratio
        taxable_value = item['amount'] + bs_share
        
        rate = item['tax_rate']
        if rate not in tax_groups:
            tax_groups[rate] = 0.0
        tax_groups[rate] += taxable_value
        
    generated_bs = []
    
    # Process each rate group
    for rate, taxable in tax_groups.items():
        if rate <= 0:
            continue
            
        if is_local:
            # Split into CGST and SGST
            half_rate = rate / 2
            half_tax = (taxable * half_rate) / 100
            
            # CGST
            generated_bs.append({
                'name': "CGST",
                'rate': half_rate,
                'amount': round(half_tax, 2)
            })
            # SGST
            generated_bs.append({
                'name': "SGST",
                'rate': half_rate,
                'amount': round(half_tax, 2)
            })
        else:
            # IGST
            tax_amt = (taxable * rate) / 100
            generated_bs.append({
                'name': "IGST",
                'rate': rate,
                'amount': round(tax_amt, 2)
            })
            
    return generated_bs