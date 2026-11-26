# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building standalone Windows nBio_ERG_Trace executable."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / "src" / "erg_reader" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "erg_reader" / "assets"), "erg_reader/assets"),
        (str(ROOT / "example_files"), "example_files"),
        (str(ROOT / "LICENSE"), "."),
    ],
    hiddenimports=[
        "PySide6.QtSvg",
        "pyqtgraph.exporters",
        "openpyxl",
        "scipy.signal",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="nBio_ERG_Trace",
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
