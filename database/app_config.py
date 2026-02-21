import json
import os
from database.db import get_connection


def get_app_config():
    """
    Get app configuration (OpenAI API key and Serial No) from database.
    
    Returns:
        tuple: (openai_api_key, serial_no) or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT openai_api_key, serial_no
        FROM app_config WHERE id = 1
    """)
    row = cur.fetchone()
    conn.close()
    return row


def save_app_config(openai_api_key, serial_no):
    """
    Save app configuration to database.
    
    Args:
        openai_api_key: OpenAI API key
        serial_no: License serial number
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Delete existing config
        cur.execute("DELETE FROM app_config")
        
        # Insert new config
        cur.execute("""
            INSERT INTO app_config (id, openai_api_key, serial_no)
            VALUES (1, ?, ?)
        """, (openai_api_key, serial_no))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving app config: {e}")
        return False


def migrate_from_json():
    """
    Migrate configuration from config.json to database (one-time migration).
    Only migrates if database is empty and config.json exists.
    
    Returns:
        bool: True if migration occurred, False otherwise
    """
    # Check if database already has config
    config = get_app_config()
    if config and (config[0] or config[1]):
        # Database already has data, skip migration
        return False
    
    # Try to find config.json
    try:
        # config.json should be in minib/minib directory
        current_dir = os.path.dirname(os.path.abspath(__file__))  # minib/database
        project_root = os.path.dirname(current_dir)  # minib/minib
        config_path = os.path.join(project_root, 'config.json')
        
        if not os.path.exists(config_path):
            return False
        
        with open(config_path, 'r') as f:
            json_config = json.load(f)
        
        openai_api_key = json_config.get('openai_api_key', '')
        serial_no = json_config.get('serial_no', '')
        
        if openai_api_key or serial_no:
            # Migrate to database
            success = save_app_config(openai_api_key, serial_no)
            if success:
                print("Successfully migrated config.json to database")
                return True
        
        return False
    except Exception as e:
        print(f"Error during config migration: {e}")
        return False
