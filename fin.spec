# -*- mode: python ; coding: utf-8 -*-
# ============================================================
#  fin — Selachii Package Manager
#  fin.spec — PyInstaller build spec
# ============================================================

block_cipher = None

a = Analysis(
    ['run_fin.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'fin',
        'fin.cli',
        'fin.config',
        'fin.constants',
        'fin.exceptions',
        'fin.transaction',
        'fin.commands',
        'fin.resolver',
        'fin.downloader',
        'fin.installer',
        'fin.db',
        'fin.builder',
        'fin.security',
        'fin.ui',
        'zstandard',
        'gnupg',
        'requests',
    ],
    hookspath=[],
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
    name='fin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
