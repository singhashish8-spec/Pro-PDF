# Build Progress

Tracks completion of the phases in `docs/blueprint/pdf_pro_development_blueprint_v2.md`, Section 10. Updated at the end of every phase.

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundations & Decisions | ✅ Done | ADRs 0001-0005, repo scaffolding |
| 1 — Core Shell & Dashboard | ✅ Done | `QMainWindow` shell, `theme.qss` tokens (light + dark), Home Dashboard with recent files |
| 2 — Rendering, Glass Layer, Undo/Redo | ✅ Done | `PDFDocument` core wrapper, `scene_to_pdf`/`pdf_to_scene`, Glass Layer canvas, pan/zoom, full Command-pattern undo/redo, autosave journal wired to the command stack |
| 3 — Drafting Suite v1 | ✅ Done | 15 tools (select, rectangle, ellipse, arrow, pen, highlighter, underline, strikeout, squiggly, note, stamp, textbox, callout, cloud, eraser), all undo/redo-backed, wired into a left tool palette |
| 4 — Floating Menu, Command Palette, UX Polish | ✅ Done | Live style-editing floating panel on selection, Ctrl+K command palette |
| 5 — Engineering & Measurement Suite | ✅ Done | Calibration, distance/area/perimeter/diameter/radius/count, multi-scale-per-document, Tool Chest |
| 6 — Document & Page Management + Markups List | ✅ Done | Insert/delete/rotate/move/extract/merge/split, Bates/watermark/header-footer, TOC editor, external file-change detection, SQLite-backed Markups List |
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

## Phase 5 detail

- `app/models/markup.py` — `MARKUP_TYPES` gained `measure_diameter`/`measure_radius` (perimeter/area/linear/count already existed from Phase 0's schema).
- `app/tools/measurement_math.py` — pure functions: `path_length`, `polygon_area` (shoelace), `polygon_perimeter`, `to_real_length`/`to_real_area` (apply a `Calibration.scale_factor`, squared for area), `format_measurement`. `Calibration.scale_factor` (already in `app/models/project.py` since Phase 2) is real-world units per PDF point.
- `app/tools/calibration_tool.py` — `CalibrationTool`: drag a line of known length, `parse_distance_input()` reads free text like `"20 ft"`/`"3.5m"`/`"12"` (defaults to ft), pushes a `CalibrateCommand`. Savable and multiple-per-page: `MarkupDocument.calibrations_for_page()` already supported this from Phase 2, now surfaced.
- `app/tools/measure_linear.py`, `measure_circular_tool.py` (+ `measure_diameter.py`, `measure_radius.py`), `measure_polygon_tool.py` (+ `measure_area.py`, `measure_perimeter.py`), `measure_count.py` — every measurement tool reads `ToolContext.active_calibration` (or falls back to raw PDF points, unit `"pt"`) and writes both a human-readable `text` label (so it's visible without a scale) and a structured `MarkupObject.measurement`. The label updates live during the drag/click-sequence via the same `preview_callback` mechanism from Phase 3, satisfying "live-updating dimension label."
- `app/ui/canvas/document_view.py` — a scale-selector combo in the toolbar (`_scale_combo`) lists every calibration on the current page (`"No scale"` plus one entry per `Calibration`); the newest calibration is auto-selected but the user can switch between saved scales per page — "multiple saved scales per document." `_CLICK_TO_BUILD_TOOLS` now covers Cloud, Area, and Perimeter under the same Return/Escape shortcuts.
- `app/persistence/tool_chest.py` + `app/ui/panels/tool_chest_panel.py` — the Tool Chest: named style presets (`{id, name, markup_type, style}`) persisted as JSON under the Qt app-data directory (`QStandardPaths.AppDataLocation`), so entries are shared across every project/document, not stored per-PDF. `DocumentView.open_tool_chest()` wires "Save Current Style…" to the live `self._default_style` (now a single persistent `Style` instance per `DocumentView`, mutated in place by the Tool Chest and by nothing else — individual drawn objects still get their own copy) and "Apply" to both restoring that style and switching to the matching tool.
- Tests: `tests/unit/test_measurement.py` (math helpers, calibration parsing, all 6 measurement tools with and without a calibration), `tests/unit/test_tool_chest.py` (persistence round-trip against a temp file), `tests/integration/test_document_view.py` additions (scale combo wiring end-to-end, Return-key finishing `MeasureAreaTool`). 89 tests passing. Also verified with a full manual smoke run through `MainWindow`: calibrate a page, run all 6 measurement tools against that scale and check the computed real-world values, round-trip a Tool Chest entry through the real persistence file (cleaned up afterward so the smoke run doesn't leave test data in the user's actual config), then export.

## Phase 6 detail

- `app/core/pdf_document.py` — page management (`insert_blank_page`, `delete_page`, `rotate_page`, `move_page`, `extract_pages`), TOC (`get_toc`/`set_toc`), watermark/Bates/header-footer (`add_watermark`, `add_bates_numbers`, `add_header_footer`), metadata (`get_metadata`/`scrub_metadata`, ready for Phase 7), and module-level `merge_pdfs`/`split_pdf`. **`export()` was changed to build its working copy from `doc.write()` (the currently open, possibly structurally-edited document) instead of re-reading `self.path` from disk** — otherwise Save would silently drop any page operations applied this session, since they mutate the in-memory `fitz.Document` but aren't written to disk until Save.
- Two real bugs caught by tests before they shipped: (1) `fitz.Document.move_page(pno, to)`'s `to` argument means "insert before this position in the pre-move array" (or -1 for append), not "the page's final index" — `PDFDocument.move_page()` now translates the intuitive (from, to) into what fitz actually expects, verified against 6 cases. (2) `Page.insert_text(rotate=...)` only accepts multiples of 90 — the original 45° "diagonal watermark" raised `ValueError`; `add_watermark()` now clamps to the nearest multiple of 90.
- `app/models/project.py` — `MarkupDocument.remove_objects_on_page()`, `shift_pages()`, `remap_pages()` keep markup `page_index` (and calibrations) consistent across page insert/delete/reorder. **Scope decision:** page-structure operations apply immediately and are not part of the undo/redo `CommandStack` (unlike markup edits) — reconstructing a whole-document snapshot for undo was out of scope for this phase; destructive ones (delete) get a confirmation dialog instead. Documented here rather than silently decided.
- `app/persistence/markups_db.py` — SQLite-backed Markups List per Section 4, one DB file next to the PDF, full-resync-on-change (simple and correct at internal-alpha object counts). `app/ui/panels/markups_list_panel.py` — sortable `QTableWidget` (click any header), double-click/Enter jumps to the object's page and selects it via the new `DocumentView.select_object()`.
- `app/ui/panels/toc_editor_dialog.py` — plain-text bookmark editor (`Title<TAB>Page`, tab-indent for nesting) round-tripping fitz's `[[level, title, page], ...]` TOC format.
- External file-change detection: `QFileSystemWatcher` on the open path (`DocumentView._on_file_changed_on_disk`), re-armed if the watched inode disappears (some editors replace-on-save). `notify_saving()` suppresses the notice for the app's own writes. `MainWindow` prompts to reload on a genuine external change.
- **Important architectural fix this phase:** the `MarkupDocument` change listener (`_on_markup_document_changed`, previously named `_refresh_markups`) is now the single place that re-renders the Glass Layer, writes the autosave journal, and syncs the Markups DB — because page-management operations mutate `MarkupDocument` directly (not through a `Command`), and the autosave/DB sync were originally only wired to the `CommandStack` listener. A manual smoke run caught this: after `delete_current_page()`, the Markups DB still showed the deleted object. Scene rebuilding was split back out into `_rebuild_scene_markups()` so pure zoom/pan (no state change) doesn't also re-write the journal and DB on every wheel tick.
- Tests: `tests/unit/test_page_management.py` (every `PDFDocument` page-management/watermark/TOC/metadata method, plus the `move_page` and `export`-includes-in-memory-edits regressions), `tests/unit/test_markup_document_pages.py`, `tests/unit/test_markups_db.py`, `tests/unit/test_toc_editor_dialog.py`, `tests/integration/test_document_view.py` and `test_external_file_change.py` additions (page ops shifting/dropping markups end-to-end, DB sync firing, `select_object`, watermark/Bates/header-footer, real `QFileSystemWatcher` detection via `qtbot.waitSignal`, and confirming our own save doesn't self-trigger the notice). 119 tests passing. Also verified with a full manual smoke run through `MainWindow` covering every Phase 6 feature end-to-end.

