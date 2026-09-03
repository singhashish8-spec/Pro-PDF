# PyInstaller spec for PDF Pro (Blueprint v2, Section 10 Phase 10 / internal
# distribution). Run from the repo root:
#   pyinstaller packaging/pdf_pro.spec --noconfirm
#
# Unsigned builds are fine for the internal phase (Section 3); code signing
# becomes relevant only at external release.

import sys
from pathlib import Path

block_cipher = None

repo_root = Path(SPECPATH).parent
sys.path.insert(0, str(repo_root))

a = Analysis(
    [str(repo_root / "app" / "main.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyMuPDF's OCR path and a few PyQt6 submodules aren't always picked
        # up by PyInstaller's static import scan.
        "pymupdf",
        "PyQt6.sip",
        "PyQt6.QtPrintSupport",
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
    [],
    exclude_binaries=True,
    name="PDF Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PDF Pro",
)
