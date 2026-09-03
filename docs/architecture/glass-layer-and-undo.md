# The Glass Layer, coordinate transforms, and undo/redo

How the systems described at a decision level in ADRs 0001-0004 actually fit together, as implemented in Phase 2.

## Coordinate systems

`app/core/coordinates.py` has the only `pdf_to_scene`/`scene_to_pdf` implementation in the app. `scale` in those functions is **scene pixels per PDF point**, i.e. `zoom * PDFDocument.BASE_DPI_SCALE` — the same factor `PDFDocument.render_page()` uses to rasterize the page. `DocumentView._render_current_page()` computes this once per zoom change and hands it to `GlassScene`, which stores it as `scale_factor` and exposes `scene_point_to_pdf`/`pdf_point_to_scene` convenience wrappers. Nothing downstream (tools, panels) is allowed to recompute this.

## The Glass Layer

`GlassScene` (a `QGraphicsScene`) holds exactly one background `QGraphicsPixmapItem` (the rasterized current page, z=-1000) plus one `QGraphicsItem` per visible `MarkupObject`, built by `app/ui/canvas/markup_items.py`. `MarkupObject.points` are always PDF-space; `markup_items.py` converts them to scene space at build time via `pdf_to_scene`. The scene is rebuilt (not diffed) on every `MarkupDocument` change — acceptable at internal-alpha object counts, revisit if the 5,000-object target (Section 8) shows jank.

`DocumentView` is the composite: it owns the `PDFDocument`, `MarkupDocument`, and `CommandStack`, and wires `PdfGraphicsView` (pan/zoom) to `GlassScene`. Only load() touches the PDF binary directly (via `PDFDocument.open`/`render_page`); everything else — drawing, editing, undo — works purely against the Glass Layer's in-memory objects.

## Undo/redo

Every mutation to `MarkupDocument` state must go through a `Command` (`app/commands/`). `CommandStack.push()` calls `do()` immediately and clears the redo stack; `undo()`/`redo()` pop and replay. Tools (Phase 3+) build a `MarkupObject`, wrap it in a `Command`, and push — they never call `MarkupDocument.add`/`remove` directly. This is enforced by convention today (Tool base class only exposes the document via `ToolContext` for reads); a code-review checklist item, not a runtime guard.

`CommandStack` has its own listener list, separate from `MarkupDocument`'s — `DocumentView._on_stack_changed` uses it to (a) update the Undo/Redo menu enabled-state and (b) write the autosave journal after every command.

## Autosave / crash recovery

`app/persistence/autosave.py` writes the full `MarkupDocument.to_journal()` (the same JSON shape as `MarkupObject.to_dict()`) to `<file>.pdf.pdfpro-journal` after every command. `DocumentView.load()` checks for a journal *before* resetting any state and suspends autosave writes during its own reset (`_suspend_autosave`) so the act of opening a file can't stomp on a journal it hasn't offered for recovery yet. `MainWindow.open_document()` prompts the user; `discard_journal()` is called on both "discard" and on a successful `Save`.

## Save/export

`PDFDocument.export()` opens a **fresh** `fitz` handle on the original file (the live editing document is never touched), bakes every `MarkupObject` via `app/core/markup_baker.py` (`page.new_shape()` draw calls, one bake function per type), and saves to the target path. New markup types get a bake function here as their tool ships (Phase 3 adds the rest of the drafting suite; Phase 5 measurements; Phase 7 redaction/forms/signatures).
