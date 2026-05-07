# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pdf_crawler_gui_2.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('requirements.txt', '.'),
        ('READ me.txt', '.'),
        ('NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx', '.'),
        ('updated_master_list.xlsx', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'pandas',
        'PyPDF2',
        'pdfplumber',
        'beautifulsoup4',
        'playwright',
        'requests',
        'urllib3',
        'asyncio',
        'threading',
        'difflib',
        'unicodedata',
        're',
        'os',
        'time',
        'shutil',
        'typing',
        'bs4',
        'bs4.element',
        'urllib.parse',
        'urllib.parse.urlparse',
        'urllib.parse.urljoin',
        'urllib.parse.urldefrag',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF_Crawler_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True if you want console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to your icon file if you have one
) 