# -*- mode: python ; coding: utf-8 -*-

import os
import casadi

block_cipher = None

CASADI_PATH = os.path.dirname(casadi.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        (os.path.join(CASADI_PATH, f), 'casadi')
        for f in os.listdir(CASADI_PATH)
        if f.endswith(('.dll', '.pyd'))
    ],
    datas=[
        ('assets/logo.ico', 'assets'),
        ('assets/logo.png', 'assets'),
    ],
    hiddenimports=[
        'shapely',
        'shapely.geometry',
        'shapely.prepared',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_agg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PyQt5', 'PyQt6',
        'PySide2',
    ],
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
    name='KrabbyPathy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
)
