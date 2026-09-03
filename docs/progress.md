# Build Progress

Tracks completion of the phases in `docs/blueprint/pdf_pro_development_blueprint_v2.md`, Section 10. Updated at the end of every phase.

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundations & Decisions | ✅ Done | ADRs 0001-0005, repo scaffolding |
| 1 — Core Shell & Dashboard | ✅ Done | `QMainWindow` shell, `theme.qss` tokens (light + dark), Home Dashboard with recent files |
| 2 — Rendering, Glass Layer, Undo/Redo | ✅ Done | `PDFDocument` core wrapper, `scene_to_pdf`/`pdf_to_scene`, Glass Layer canvas, pan/zoom, full Command-pattern undo/redo, autosave journal wired to the command stack |
| 3 — Drafting Suite v1 | ✅ Done | 15 tools (select, rectangle, ellipse, arrow, pen, highlighter, underline, strikeout, squiggly, note, stamp, textbox, callout, cloud, eraser), all undo/redo-backed, wired into a left tool palette |
| 4 — Floating Menu, Command Palette, UX Polish | ✅ Done | Live style-editing floating panel on selection, Ctrl+K command palette |
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

**Note:** a coordinate-system bug was caught and fixed at the start of Phase 3 — see ADR 0001's amendment and the "Fix coordinate-system mismatch" commit. `MarkupObject.points` are PyMuPDF's own page space (top-left origin, y-down), not the raw PDF spec's content-stream space the ADR originally described; `pdf_to_scene`/`scene_to_pdf` no longer flip on `page_height`.

## Phase 3 detail

- `app/tools/base.py` — `ToolContext` grew `pdf` (for text-line lookups), `text_provider` (prompts the user, real dialog in `DocumentView.prompt_for_text`), `preview_callback` (live draft rendering while drawing), and `selection_callback`.
- `app/tools/geometry.py` — hit-testing (`bbox_of`, `point_in_bbox`), `arrowhead_wings`, `wavy_points` (squiggly), `rect_intersection` — shared by tools and by the canvas/baker so arrowheads render identically on screen and in the exported PDF.
- `app/tools/select_tool.py` — `SelectTool` (the default tool): pure-Python bbox hit-testing against `MarkupDocument` (not Qt's native item selection — keeps every tool on the same on_press/on_move/on_release path, see the module for the tradeoff), drag-to-move via `MoveObjectCommand`, `delete_selected()`.
- `app/tools/drag_shape_tool.py` + `rectangle.py`, `ellipse.py`, `arrow.py` — shared two-point drag base; arrow adds an arrowhead (`markup_items._build_arrow`, `markup_baker._bake_arrow`).
- `app/tools/pen.py` — freehand polyline.
- `app/core/pdf_document.get_text_lines()` + `app/tools/text_line_lookup.py` — line-level text bboxes under a drag rect, used by:
  - `app/tools/highlighter.py` — snaps to intersected text lines (falls back to the raw drag rect over non-text areas).
  - `app/tools/text_markup_tool.py` + `underline.py`, `strikeout.py`, `squiggly.py` — tied to actual text lines per Section 7.1 ("not freehand"), one object per intersected line, grouped into one undo step via the new `CompositeCommand`.
- `app/tools/note.py`, `stamp.py` (dynamic `{preset}\n{author} — {date}` text, `STAMP_PRESETS`), `textbox.py`, `callout.py` (two-click leader+anchor) — all use `text_provider` for input.
- `app/tools/cloud.py` — click-to-add-vertex polygon; `finish()`/`cancel()` bound to Return/Escape in `DocumentView`.
- `app/tools/eraser.py` — click or drag-to-delete.
- `app/ui/canvas/document_view.py` — left tool palette (checkable, exclusive `QToolButton`s + a stamp-preset combo), `select_tool()`/`activate_tool()`, keyboard shortcuts (Delete/Backspace → `SelectTool.delete_selected`, Return/Enter → `CloudTool.finish`, Escape → cancel + back to Select). Select is the default tool on every `load()`.
- `app/core/markup_baker.py` — bake functions added for every new type this phase (arrow with arrowhead, highlight, underline/strikeout/squiggly polylines, text-based note/textbox, stamp box, callout leader+text).
- Tests: `tests/unit/test_tools.py` (one or more tests per tool, plus the geometry helpers, using a real `PDFDocument` for text-line snapping), `tests/integration/test_document_view.py` additions (toolbar wiring, keyboard shortcuts). 55 tests passing. Also verified with a full manual smoke run exercising all 15 tools plus export.

## Phase 4 detail

- `app/ui/panels/floating_style_panel.py` — `FloatingStylePanel`: appears near the selected object (positioned via `DocumentView._position_floating_panel`, which converts the object's PDF-space bbox to a global screen point through the same `pdf_to_scene`/`view.mapFromScene`/`viewport.mapToGlobal` chain used everywhere else). Stroke/fill color swatches (`QColorDialog`), a fill-clear button, line-width spinner, and an opacity slider each push a `StyleChangeCommand` immediately on change — real-time, undoable style editing, per Section 7.7. A delete button reuses `DeleteObjectCommand`. Wired to `SelectTool`'s `selection_callback`; hidden whenever a non-Select tool is chosen, repositioned after every command (so it tracks a dragged object).
- `app/ui/panels/command_palette.py` — `CommandPalette` (`QDialog`) + `PaletteCommand`; substring filter, arrow-key navigation, Enter/double-click to run. `DocumentView.build_palette_commands()` registers every tool, Undo/Redo, zoom in/out, and page navigation. Bound to Ctrl+K both as a `QShortcut` on `DocumentView` and as a `MainWindow` View-menu action, satisfying the "Figma feel" milestone alongside the floating panel.
- Tests: `tests/unit/test_command_palette.py`, `tests/unit/test_floating_style_panel.py`, plus `tests/integration/test_document_view.py` additions for selection→panel wiring and palette command registration. 65 tests passing. Also verified with a full manual smoke run through `MainWindow`: select an object, live-edit its style via the floating panel, undo, then run a tool switch through the command palette's own command list.

