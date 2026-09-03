# Build Progress

Tracks completion of the phases in `docs/blueprint/pdf_pro_development_blueprint_v2.md`, Section 10. Updated at the end of every phase.

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundations & Decisions | ✅ Done | ADRs 0001-0005, repo scaffolding |
| 1 — Core Shell & Dashboard | ✅ Done | `QMainWindow` shell, `theme.qss` tokens (light + dark), Home Dashboard with recent files |
| 2 — Rendering, Glass Layer, Undo/Redo | ✅ Done | `PDFDocument` core wrapper, `scene_to_pdf`/`pdf_to_scene`, Glass Layer canvas, pan/zoom, full Command-pattern undo/redo, autosave journal wired to the command stack |
| 3 — Drafting Suite v1 | ⬜ Not started | |
| 4 — Floating Menu, Command Palette, UX Polish | ⬜ Not started | |
| 5 — Engineering & Measurement Suite | ⬜ Not started | |
| 6 — Document & Page Management + Markups List | ⬜ Not started | |
| 7 — Forms, Redaction, Security, Signatures | ⬜ Not started | |
| 8 — OCR, Search, Compare, Search-and-Redact | ⬜ Not started | |
| Windows installer | ⬜ Not started | |

## Phase 1 detail

- `app/ui/theme/tokens.py` — `ThemeTokens` dataclass + `build_qss()`, light and dark token sets defined up front per Section 7.7 even though only light ships visibly first.
- `app/ui/theme/manager.py` — `ThemeManager` applies the stylesheet to the running `QApplication` and persists the choice via `QSettings`.
- `app/ui/dashboard/home_dashboard.py` — recent files list + quick actions (Open, New).
- `app/persistence/recent_files.py` — `QSettings`-backed recent files list.
- `app/ui/main_window.py` — `QMainWindow` shell with File/View menus, dashboard/document `QStackedWidget`. `open_document()` currently raises `NotImplementedError` past the recent-files bookkeeping; wired to the real Glass Layer canvas in Phase 2.
- `app/main.py` — application entry point (`pdf-pro` console script).
- Tests: `tests/unit/test_shell.py`, run offscreen via `QT_QPA_PLATFORM=offscreen` (set in `tests/conftest.py`).

## Phase 2 detail

- `app/core/pdf_document.py` — `PDFDocument`: open/close, page count/size, `render_page()` to `QImage`, and the `export()` save pipeline (bakes markups into a fresh copy of the PDF via `app/core/markup_baker.py`, leaving the live editing document untouched per Section 6.4).
- `app/core/coordinates.py` — `pdf_to_scene`/`scene_to_pdf` (ADR 0001). `scale` here means scene-pixels-per-PDF-point (`zoom * PDFDocument.BASE_DPI_SCALE`) so the Glass Layer lines up pixel-for-pixel with the rendered background — documented in the module so nobody passes a bare UI zoom level by mistake.
- `app/models/markup.py`, `app/models/project.py` — `MarkupObject`/`Style`/`Measurement` (ADR 0002) and `MarkupDocument`, the Qt-agnostic in-memory object store with change listeners; `Calibration` and `FormField` data classes are here too, ready for Phases 5 and 7.
- `app/commands/base.py`, `app/commands/object_commands.py` — `Command`/`CommandStack` (ADR 0003) plus `AddObjectCommand`, `DeleteObjectCommand`, `MoveObjectCommand`, `StyleChangeCommand`, `CalibrateCommand`.
- `app/tools/base.py` — the shared `Tool`/`ToolContext` base every Phase 3+ tool builds on; tools only ever push commands, never mutate `MarkupDocument` directly.
- `app/ui/canvas/` — `GlassScene` (background pixmap + per-object `QGraphicsItem`s via `markup_items.py`), `PdfGraphicsView` (ctrl+wheel zoom, drag-to-pan, forwards scene coordinates to the active tool), and `DocumentView`, the composite widget wiring `PDFDocument` + `MarkupDocument` + `CommandStack` + page/zoom controls together.
- `app/persistence/autosave.py` — the `*.pdfpro-journal` sidecar (ADR 0004), written after every command via the command-stack listener, with a recovery prompt wired into `MainWindow.open_document()`.
- `MainWindow` now hosts the real `DocumentView`, with Save/Save As wired to `PDFDocument.export()` and Undo/Redo wired to the command stack.
- Tests: `tests/unit/test_coordinates.py` (round-trip + orientation), `tests/unit/test_commands.py` (every command's do/undo), `tests/unit/test_markup_model.py` (JSON round-trip), `tests/unit/test_pdf_document.py` (render + export against a generated fixture PDF), `tests/integration/test_document_view.py` (load/navigate/draw/autosave-recovery through the real widget stack, offscreen). Also verified with a full manual smoke run: open → draw → undo → redo → export.

