# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\dist\\obfuscated\\main.py'],
    pathex=['C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\dist\\obfuscated'],
    binaries=[],
    datas=[('C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\minib\\assets', 'assets'), ('C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\minib\\config', 'config'), ('C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\minib\\database', 'database')],
    hiddenimports=['ui.add_item', 'ui.add_party', 'ui.api_config', 'ui.main_window', 'ui.purchase_voucher', 'ui.secret_window', 'ui.settings_window', 'ui.sql_config', 'ui', 'utils.ai_utils', 'utils.autocomplete', 'utils.busy_utils', 'utils.calculation', 'utils.common', 'utils.license_utils', 'utils.pdf_utils', 'utils.setting_keys', 'utils', 'database.api_config', 'database.app_config', 'database.busy_db', 'database.db', 'database.sql_server', 'database', 'tkinter', 'tkinter.messagebox', 'tkinter.filedialog', 'tkinter.simpledialog', 'tkinter.ttk', 'PIL', 'PIL._tkinter_finder', 'sqlite3', 'win32com.client', 'openai', 'requests', 'urllib3', 'rapidfuzz', 'pdfplumber', 'pypdfium2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MiniB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\imroz\\OneDrive\\Desktop\\projects\\tkinter new\\minib\\minib\\ICON.ico'],
)
