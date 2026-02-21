"""
SQL Server database access via pyodbc.
Fetches party/item/bill-sundry data from BUSY SQL Server tables.
"""
import pyodbc
import re
from database.db import get_connection

# ---------------------------------------------------------------------------
# Config helpers (stored in local SQLite)
# ---------------------------------------------------------------------------

def get_sql_config():
    """Return (username, password, database_name, server_name) from SQLite."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT username, password, database_name, server_name FROM sql_config WHERE id=1")
        return cur.fetchone()
    except Exception:
        return None
    finally:
        conn.close()


def save_sql_config(username, password, database_name, server_name):
    """Save SQL Server config to local SQLite."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sql_config")
    cur.execute(
        "INSERT INTO sql_config (id, username, password, database_name, server_name) VALUES (1,?,?,?,?)",
        (username, password, database_name, server_name)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_sql_connection(db_override=None):
    """
    Open and return a pyodbc connection to SQL Server.
    Returns None if config is missing or connection fails.
    """
    cfg = get_sql_config()
    if not cfg or not all([cfg[0], cfg[2], cfg[3]]):
        return None

    username, password, database_name, server_name = cfg
    database_name = db_override or database_name

    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_name};"
            f"DATABASE={database_name};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str, timeout=10)
    except Exception:
        # Try SQL auth fallback / Windows auth
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_name};"
                f"DATABASE={database_name};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, timeout=10)
        except Exception:
            return None


def test_sql_connection(username, password, database_name, server_name):
    """Test SQL Server connection. Returns (ok: bool, message: str)."""
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_name};"
            f"DATABASE={database_name};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def get_current_db_name():
    """Return database_name from the saved SQL config."""
    cfg = get_sql_config()
    if cfg and len(cfg) >= 3:
        return cfg[2]
    return None


def parse_smart_date(date_str):
    """
    Parse a partial or full date string into ('YYYY-MM-DD', 'DD-MM-YYYY').
    Supports DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, and short DD-MM forms.
    Infers year from financial year (April start) using database name.
    Returns (None, None) on failure.
    """
    if not date_str:
        return None, None

    date_str = date_str.strip()

    from datetime import datetime
    # Try full formats first
    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%d-%m-%Y")
        except ValueError:
            pass

    # Short DD-MM form
    match = re.match(r"^(\d{1,2})[-/.](\d{1,2})$", date_str)
    if not match:
        return None, None

    day, month = int(match.group(1)), int(match.group(2))

    db_name = get_current_db_name()
    start_year = datetime.today().year

    if db_name:
        years = re.findall(r"20\d{2}", db_name)
        if years:
            start_year = int(years[-1])

    if 4 <= month <= 12:
        year = start_year
    elif 1 <= month <= 3:
        year = start_year + 1
    else:
        return None, None

    try:
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%d-%m-%Y")
    except ValueError:
        return None, None


# ---------------------------------------------------------------------------
# Data queries
# ---------------------------------------------------------------------------

def fetch_autocomplete(prefix, mastertype, max_results=20):
    """
    Search master1 table by Name prefix.
    mastertype: 6=Item, 2=Party, 9=Bill Sundry, 8=Unit, 25=Tax Category, etc.
    Returns list of Name strings.
    """
    conn = get_sql_connection()
    if not conn or not prefix or not prefix.strip():
        return []

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT TOP (?) Name FROM master1 WHERE mastertype=? AND Name LIKE ? ORDER BY Name",
            (max_results, mastertype, prefix.strip() + "%")
        )
        rows = cur.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"SQL autocomplete error: {e}")
        return []
    finally:
        conn.close()


def get_item_autofill_data(item_name, voucher_date):
    """
    Fetch unit name and tax rate for an item.
    Returns (unit_name, tax_rate) tuple or None.
    """
    conn = get_sql_connection()
    if not conn or not item_name:
        return None

    try:
        cur = conn.cursor()

        # Get item code, unit code, tax code
        cur.execute(
            "SELECT Code, CM1, CM8 FROM master1 WHERE mastertype=6 AND Name=?",
            (item_name,)
        )
        row = cur.fetchone()
        if not row:
            return None

        code, unit_code, tax_code = row[0], row[1], row[2]

        # Unit name
        unit_name = ""
        if unit_code:
            cur.execute("SELECT Name FROM master1 WHERE mastertype=8 AND Code=?", (unit_code,))
            urow = cur.fetchone()
            if urow and urow[0]:
                unit_name = urow[0]

        # Tax rate
        tax_rate = 0.0
        if tax_code and voucher_date:
            try:
                from datetime import datetime
                dt = datetime.strptime(voucher_date, "%Y-%m-%d")
            except Exception:
                return unit_name, 0.0

            cur.execute(
                """
                SELECT TOP 1 D2 FROM mastersupport
                WHERE mastercode=?
                  AND (date IS NULL OR date <= ?)
                ORDER BY CASE WHEN date IS NULL THEN 0 ELSE 1 END, date DESC
                """,
                (tax_code, dt.date())
            )
            trow = cur.fetchone()
            if trow and trow[0] is not None:
                try:
                    tax_rate = float(trow[0])
                except Exception:
                    pass

        return unit_name, tax_rate

    except Exception as e:
        print(f"SQL autofill error: {e}")
        return None
    finally:
        conn.close()


def get_bill_sundry_info(name):
    """
    Fetch Bill Sundry info. I1=0 means Subtractive, else Additive.
    Returns dict {'i1': value} or None.
    """
    conn = get_sql_connection()
    if not conn or not name:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT I1 FROM master1 WHERE mastertype=9 AND Name=?", (name,))
        row = cur.fetchone()
        if row and row[0] is not None:
            return {"i1": row[0]}
        return None
    except Exception as e:
        print(f"SQL bill sundry error: {e}")
        return None
    finally:
        conn.close()


def get_all_item_names():
    """Fetch all item names from master1 where mastertype=6."""
    conn = get_sql_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("SELECT Name FROM master1 WHERE mastertype=6 ORDER BY Name")
        rows = cur.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"SQL get_all_item_names error: {e}")
        return []
    finally:
        conn.close()
