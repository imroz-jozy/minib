from database.db import get_connection

def get_api_config():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT url, username, password
        FROM api_config WHERE id = 1
    """)
    row = cur.fetchone()
    conn.close()
    return row

def test_api_connection(url, username, password):
    """
    Test API connection - basic validation
    You can extend this to make an actual API call if needed
    """
    try:
        if not url or not url.strip():
            return False, "URL cannot be empty"
        
        if not url.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"
        
        # Basic validation passed
        # You can add actual API call here if needed
        return True, "API configuration is valid"
    except Exception as e:
        return False, str(e)

