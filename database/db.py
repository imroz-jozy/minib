import sqlite3

DB_NAME = "mini_b.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Purchase items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id INTEGER,
        item_name TEXT,
        tax_category TEXT,
        qty REAL,
        unit TEXT,
        list_price REAL,
        discount REAL,
        price REAL,
        amount REAL
    )
    """)

    # Try to add voucher_id column if it doesn't exist (migration for existing DB)
    try:
        cur.execute("ALTER TABLE purchase_items ADD COLUMN voucher_id INTEGER")
    except sqlite3.OperationalError:
        pass # Column likely already exists

    # Try to add tax_category column if it doesn't exist (migration for existing DB)
    try:
        cur.execute("ALTER TABLE purchase_items ADD COLUMN tax_category TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists

    # Purchase Vouchers (Header)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        series TEXT,
        voucher_no TEXT,
        purchase_type TEXT,
        party_name TEXT
    )
    """)

    # Bill Sundry
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_sundry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id INTEGER,
        name TEXT,
        percentage REAL,
        amount REAL
    )
    """)

    # SQL CONFIG TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sql_config (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        database_name TEXT,
        server_name TEXT
    )
    """)

    # API CONFIG TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_config (
        id INTEGER PRIMARY KEY,
        url TEXT,
        username TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

