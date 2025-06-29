# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for TopSky Weather Radar Bridge

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect data files from packages that might need them
datas = []
try:
    datas += collect_data_files('uvicorn')
except Exception:
    pass
try:
    datas += collect_data_files('fastapi')
except Exception:
    pass

# Don't include config.ini in the executable - it should be external
# datas += [('config.ini', '.')]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn',
        'uvicorn.main',
        'uvicorn.server',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.loops.uvloop',
        'fastapi',
        'fastapi.applications',
        'fastapi.openapi.constants',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'httpx',
        'httpx._client',
        'httpx._config',
        'httpx._models',
        'httpx._exceptions',
        'PIL',
        'PIL.Image',
        'PIL._tkinter_finder',
        'configparser',
        'asyncio',
        'dotenv',
        'python_dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'ipython',
        'pytest',
        'black',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='topsky-wxr-bridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,  # Disable version file for now to avoid path issues
    icon=None,
)