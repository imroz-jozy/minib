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


def calculate_price(list_price, discount_text, quantity=1):
    """
    Calculate final price after applying discount(s).
    
    Discount formats:
    - "X+Y+Z": percentage1 + percentage2 + amount (e.g., "5+2+20")
    - "X+Y": percentage1 + percentage2 (both are percentages, e.g., "5+2")
    - "X": single percentage or amount (e.g., "10" or "10%")
    
    Examples:
    - "5+2+20" with quantity=2: 5% discount, then 2% discount on per-unit price, 
      then 20 amount discount on total (qty × price)
    - "5+2" means: 5% discount, then 2% discount (both percentages)
    - "5+0+20" means: 5% discount, then 0% discount, then 20 amount discount on total
    - "0+0+20" means: just 20 amount discount from absolute total (qty × price)
    
    Args:
        list_price: Original list price (can be string or number)
        discount_text: Discount string (e.g., "5+2+20", "5+2", "10")
        quantity: Quantity for flat amount discount calculation (default: 1)
    
    Returns:
        float: Final per-unit price after discounts, rounded to 2 decimal places
    """
    try:
        price = float(list_price) if list_price else 0.0
        qty = float(quantity) if quantity else 1.0
    except (ValueError, TypeError):
        return 0.0
    
    if not discount_text or not discount_text.strip():
        return round(price, 2)
    
    parts = discount_text.strip().split("+")
    
    # Expected format:
    # - 3 parts: X+Y+Z (percentage1 + percentage2 + amount)
    # - 2 parts: X+Y (percentage1 + percentage2, both are percentages)
    # - 1 part: X (single percentage or amount)
    if len(parts) >= 3:
        # Format: X+Y+Z (percentage1 + percentage2 + amount)
        try:
            percent1 = float(parts[0].strip()) if parts[0].strip() else 0.0
            percent2 = float(parts[1].strip()) if parts[1].strip() else 0.0
            amount = float(parts[2].strip()) if parts[2].strip() else 0.0
            
            # Apply first percentage discount
            if percent1 > 0:
                price -= price * (percent1 / 100)
            
            # Apply second percentage discount
            if percent2 > 0:
                price -= price * (percent2 / 100)
            
            # Apply flat amount discount on absolute total (qty × price)
            # Then divide back to get per-unit price
            if amount > 0:
                total = price * qty
                total -= amount
                price = total / qty if qty > 0 else 0.0
            
        except (ValueError, TypeError):
            # If parsing fails, return original price
            return round(price, 2)
    elif len(parts) == 2:
        # Format: X+Y (percentage1 + percentage2, both are percentages)
        try:
            percent1 = float(parts[0].strip()) if parts[0].strip() else 0.0
            percent2 = float(parts[1].strip()) if parts[1].strip() else 0.0
            
            # Apply first percentage discount
            if percent1 > 0:
                price -= price * (percent1 / 100)
            
            # Apply second percentage discount
            if percent2 > 0:
                price -= price * (percent2 / 100)
            
        except (ValueError, TypeError):
            pass
    else:
        # Single value: try as percentage first, then amount
        part = parts[0].strip()
        if not part:
            return round(price, 2)
        
        try:
            if part.endswith("%"):
                percent = float(part.replace("%", "").strip())
                price -= price * (percent / 100)
            else:
                # For single amount discount, apply on absolute total
                amount = float(part)
                total = price * qty
                total -= amount
                price = total / qty if qty > 0 else 0.0
        except (ValueError, TypeError):
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