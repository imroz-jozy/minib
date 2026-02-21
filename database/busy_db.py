"""
busy_db.py — Legacy Busy COM module (disabled).
All data is now fetched from SQL Server via sql_server.py.
This module is kept as a stub so existing imports don't break.
"""

DEFAULT_PROGID = "Busy2L21.CFixedInterface"


def get_busy_config():
    """Legacy stub — not used. Config now in sql_config table."""
    return None


def save_busy_config(busy_path, data_path, comp_code, progid=None):
    """Legacy stub — not used."""
    pass


def test_busy_connection(busy_path, data_path, comp_code, progid=None):
    """Legacy stub — not used."""
    return False, "COM connection disabled. Use SQL Server configuration."


def get_fi():
    """Legacy stub — not used."""
    return None


def fetch_autocomplete(prefix, mastertype, max_results=20):
    """Delegates to sql_server.fetch_autocomplete."""
    from database.sql_server import fetch_autocomplete as _fa
    return _fa(prefix, mastertype, max_results)


def get_item_autofill_data(item_name, voucher_date):
    """Delegates to sql_server.get_item_autofill_data."""
    from database.sql_server import get_item_autofill_data as _fn
    return _fn(item_name, voucher_date)


def get_bill_sundry_info(name):
    """Delegates to sql_server.get_bill_sundry_info."""
    from database.sql_server import get_bill_sundry_info as _fn
    return _fn(name)


def get_current_db_name():
    """Delegates to sql_server.get_current_db_name."""
    from database.sql_server import get_current_db_name as _fn
    return _fn()


def get_all_item_names():
    """Delegates to sql_server.get_all_item_names."""
    from database.sql_server import get_all_item_names as _fn
    return _fn()
