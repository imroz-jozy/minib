import pyodbc
from database.db import get_connection

def get_sql_config():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT username, password, database_name, server_name
        FROM sql_config WHERE id = 1
    """)
    row = cur.fetchone()
    conn.close()
    return row

def get_sql_connection():
    """
    Get SQL Server connection using saved configuration.
    
    Returns:
        pyodbc.Connection object if successful, None otherwise
    """
    config = get_sql_config()
    if not config:
        return None
    
    username, password, database, server = config
    
    if not all([username, database, server]):
        return None
    
    try:
        conn = pyodbc.connect(
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}",
            timeout=5
        )
        return conn
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        return None

def test_sql_connection(username, password, database, server):
    try:
        conn = pyodbc.connect(
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}",
            timeout=5
        )
        conn.close()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


def get_item_autofill_data(item_name, voucher_date):
    """
    Get autofill data (unit and tax) for an item based on item name and voucher date.
    
    Args:
        item_name: Name of the item
        voucher_date: Date of the voucher (YYYY-MM-DD format)
    
    Returns:
        Tuple of (unit_name, tax_rate) or None if item not found
    """
    conn = get_sql_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Get item master data (code, cm1=unit_code, cm8=tax_code)
        cursor.execute("""
            SELECT code, cm1, cm8
            FROM master1
            WHERE mastertype = 6 AND name = ?
        """, (item_name,))
        
        item = cursor.fetchone()
        if not item:
            cursor.close()
            conn.close()
            return None
        
        item_code, unit_code, tax_code = item
        
        # Get unit name (mastertype = 8 for units)
        unit_name = ""
        if unit_code:
            cursor.execute("""
                SELECT name
                FROM master1
                WHERE mastertype = 8 AND code = ?
            """, (unit_code,))
            unit = cursor.fetchone()
            unit_name = unit.name if unit else ""
        
        # Get tax rate (date-wise from mastersupport)
        tax_rate = 0.0
        if tax_code:
            cursor.execute("""
                SELECT TOP 1 d2
                FROM mastersupport
                WHERE mastercode = ?
                  AND (date IS NULL OR date <= ?)
                ORDER BY
                    CASE WHEN date IS NULL THEN 0 ELSE 1 END,
                    date DESC
            """, (tax_code, voucher_date))
            tax = cursor.fetchone()
            # pyodbc rows index by position; use 0th column
            if tax and tax[0] is not None:
                try:
                    tax_rate = float(tax[0])
                except Exception:
                    tax_rate = 0.0
        
        cursor.close()
        conn.close()
        
        return unit_name, tax_rate
    
    except Exception as e:
        print(f"Error fetching item autofill data: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return None

def get_bill_sundry_info(name):
    """
    Get Bill Sundry info (nature) from master1.
    
    Args:
        name: Bill Sundry Name
        
    Returns:
        Dictionary with 'i1' (0=Subtractive, else Additive) or None
    """
    conn = get_sql_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i1
            FROM master1
            WHERE mastertype = 9 AND name = ?
        """, (name,))
        
        row = cursor.fetchone()
        if row:
            return {'i1': row[0]}
        return None
        
    except Exception as e:
        print(f"Error fetching Bill Sundry info: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_current_db_name():
    """Get currently configured database name."""
    config = get_sql_config()
    if config and len(config) >= 3:
        return config[2]
    return None

def parse_smart_date(date_str):
    """
    Parse a date string (e.g. '1-4', '1/1', 'DD-MM') into 'YYYY-MM-DD'.
    Infers year based on Financial Year from database name (e.g. '...db12025' -> FY 2025).
    FY starts April 1st.
    
    Args:
        date_str: Input date string
        
    Returns:
        tuple: (yyyy_mm_dd_string, dd_mm_yyyy_string) or (None, None)
    """
    if not date_str:
        return None, None
        
    date_str = date_str.strip()
    
    # Try fully formatted date first
    from datetime import datetime
    try:
        # Check if already in DD-MM-YYYY or similar
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d"), dt.strftime("%d-%m-%Y")
            except:
                pass
    except:
        pass

    # Handle short formats (DD-MM or D-M)
    import re
    # Match d-m or d/m
    match = re.match(r"^(\d{1,2})[-/.](\d{1,2})$", date_str)
    if not match:
        return None, None
        
    day, month = int(match.group(1)), int(match.group(2))
    
    # Get FY from DB Name
    db_name = get_current_db_name()
    start_year = datetime.today().year # Default to current year
    
    if db_name:
        # Look for pattern 'db1yyyy' or just 4 digits at end
        # User example: BusyComp0001_db12025 -> 2025
        # We look for "db1" followed by 4 digits, or just 4 digits? 
        # Let's try flexible search for 4 digits
        years = re.findall(r"20\d{2}", db_name)
        if years:
            # Likely the last one is the FY start?
            # Or if specific format db12025 -> 2025.
            # Let's assume the user format implies standard FY naming.
            start_year = int(years[-1])

    # Determine year
    # FY 2025 covers: 01-04-2025 to 31-03-2026
    if 4 <= month <= 12:
        year = start_year
    elif 1 <= month <= 3:
        year = start_year + 1
    else:
        return None, None # Invalid month
        
    try:
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%d-%m-%Y")
    except ValueError:
        return None, None
