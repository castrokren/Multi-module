# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pdf_crawler_gui_2.py'],
    pathex=[],
    binaries=[],
    datas=[('NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx', '.'), ('updated_master_list.xlsx', '.'), ('requirements.txt', '.'), ('READ me.txt', '.'), ('crossref_standalone.py', '.'), ('test_verbose_crossref.py', '.')],
    hiddenimports=[],
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
    name='PDF_Crawler_GUI',
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
)
