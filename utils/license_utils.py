import re
from database.sql_server import get_sql_connection, get_current_db_name
from database.app_config import get_app_config as db_get_app_config, save_app_config as db_save_app_config, migrate_from_json


def get_app_config():
    """
    Get app configuration (OpenAI API key and Serial No) from database.
    Automatically migrates from config.json if database is empty.
    
    Returns:
        dict: {'openai_api_key': str, 'serial_no': str}
    """
    # Try migration from config.json first
    migrate_from_json()
    
    config = db_get_app_config()
    if config:
        return {
            'openai_api_key': config[0] or '',
            'serial_no': config[1] or ''
        }
    return {'openai_api_key': '', 'serial_no': ''}


def save_app_config(new_config):
    """
    Save app configuration to database.
    
    Args:
        new_config: dict with 'openai_api_key' and/or 'serial_no'
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get current config
    current_config = get_app_config()
    
    # Update with new values
    openai_api_key = new_config.get('openai_api_key', current_config.get('openai_api_key', ''))
    serial_no = new_config.get('serial_no', current_config.get('serial_no', ''))
    
    return db_save_app_config(openai_api_key, serial_no)

def get_master_db_name(current_db_name):
    """
    Derive master database name by removing trailing year digits.
    Example: BusyComp0002_db12024 -> BusyComp0002_db
    """
    if not current_db_name:
        return None
        
    # Regex to find the base part before the trailing digits
    # Only if it ends with _db followed by digits? 
    # Or just strip trailing digits?
    # User said: "BusyComp0002_db12024" -> "BusyComp0002_db"
    
    match = re.match(r"^(.*_db)(\d+)$", current_db_name)
    if match:
        return match.group(1)
    
    # Fallback: if it doesn't match that exact pattern, maybe just return as is 
    # or try to strip last 4-5 digits if strictly numbers?
    # Let's stick to the user's specific pattern for now.
    return current_db_name

def verify_serial_no():
    """
    Verify if the locally configured Serial No matches the database Serial No.
    Returns:
        (bool, str): (IsValid, Message)
    """
    config = get_app_config()
    local_serial = config.get('serial_no', '').strip()
    
    if not local_serial:
        return False, "Serial Number not configured in application."

    current_db = get_current_db_name()
    if not current_db:
        return True, "Busy database not configured yet. Please configure Busy in Settings."

    conn = get_sql_connection(db_override=get_master_db_name(current_db))
    if not conn:
        return True, "Busy database - license verification skipped. Configure Busy to verify license."

    try:
        cursor = conn.cursor()
        # Query dbo.Company for SerialNO
        # User said: "TABLE NAME IS dbo.Company in SerialNO column"
        cursor.execute("SELECT TOP 1 SerialNO FROM dbo.Company")
        row = cursor.fetchone()
        
        if not row:
            return False, "Could not retrieve Serial Number from database."
            
        db_serial = str(row[0]).strip()
        
        if local_serial == db_serial:
            return True, "License Valid"
        else:
            return False, f"Serial Number Mismatch! App: {local_serial}, DB: {db_serial}"
            
    except Exception as e:
        print(f"License check error: {e}")
        return False, f"Error checking license: {str(e)}"
    finally:
        conn.close()
