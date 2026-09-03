# Building the Windows installer

The `.github/workflows/windows-build.yml` workflow does this automatically on
a `windows-latest` GitHub Actions runner (PyInstaller can't cross-compile a
Windows binary from Linux/macOS, so it has to run on real Windows). Every
push builds it; download the result from the workflow run's **Artifacts**:

- `PDFPro-Setup` — the installer (`PDFPro-Setup.exe`). Run it, click through,
  get a Start Menu entry and an optional desktop shortcut.
- `PDFPro-windows-app` — the raw unpacked app (`PDF Pro.exe` + its `_internal`
  folder), if you'd rather skip the installer and just run it directly.

A tag push matching `v*` (e.g. `v0.1.0`) also attaches the installer to a
GitHub Release.

## Building locally on Windows

```powershell
python -m pip install -e ".[dev]"
pip install pyinstaller
pyinstaller packaging\pdf_pro.spec --noconfirm
```

That produces `dist\PDF Pro\PDF Pro.exe`, runnable as-is. To also build the
installer, install [Inno Setup](https://jrsoftware.org/isinfo.php) and run:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

Output: `packaging\installer_output\PDFPro-Setup.exe`.

## OCR needs Tesseract separately

Everything except OCR (Tools → OCR Document…, and searching scanned pages)
works with no further setup. OCR calls Tesseract directly (via PyMuPDF), and
Tesseract isn't bundled into the installer — install it separately and make
sure it's on `PATH`:
[UB-Mannheim's Tesseract-OCR build for Windows](https://github.com/UB-Mannheim/tesseract/wiki).

**Why not bundled:** Tesseract's Windows distribution plus language data
would add real weight and complexity to `installer.iss` (extra files, and
telling PyMuPDF where to find `tessdata` at runtime) for a feature most
internal-alpha users won't touch on day one. Flagged here as a deliberate
scope call, not an oversight — revisit if OCR turns out to be a blocker in
practice.
