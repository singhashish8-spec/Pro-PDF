# ADR 0001: Dual coordinate systems with centralized transforms

**Status:** Accepted, amended during Phase 3 implementation (see Amendment below)
**Context:** Blueprint v2, Section 6.1

## Decision

The app deals with two coordinate systems everywhere a markup object's position is touched:

- **PDF space** — unaffected by zoom/DPI. This is the system every `MarkupObject.points` is stored in.
- **Scene/screen space** — origin at top-left, affected by zoom level, pan offset, and DPI scaling. This is the system tools operate in while the user is actively drawing, for responsiveness.

Two conversion functions, `scene_to_pdf` and `pdf_to_scene`, are implemented exactly once in `app/core/coordinates.py` and imported everywhere a conversion is needed. No tool, panel, or service computes its own transform.

## Amendment (Phase 3): "PDF space" is PyMuPDF's page space, not raw content-stream space

The original text above described "PDF user space" as origin-bottom-left, y-up, per the raw PDF specification's content-stream coordinate system. While drawing on that description while implementing Phase 3's tools, a verification against the actual library showed this was wrong for this codebase: **every** interaction with a PDF's geometry goes through PyMuPDF (`fitz`), and `fitz` already abstracts the raw content stream into its own **page space** — origin top-left, y-down — for `page.rect`, `draw_rect`, `insert_text`, `get_pixmap`, and `get_text` bboxes alike (verified directly: `page.draw_rect(fitz.Rect(10,10,50,50))` paints near the top of the rendered image, not the bottom).

Storing `MarkupObject.points` in the literal spec space and converting to fitz's page space only at bake time would have added a second, redundant flip on top of the one fitz already performs internally — silently mirroring every markup vertically when baked into the PDF. Since this app never touches the raw content stream itself, there is no reason to model that space at all.

**Corrected decision:** "PDF space" throughout this codebase means fitz's page space (top-left origin, y-down). `pdf_to_scene`/`scene_to_pdf` (`app/core/coordinates.py`) now differ from PDF space only by a scale factor (`scene = pdf * scale`, where `scale = zoom * PDFDocument.BASE_DPI_SCALE`) — no axis flip, since scene space is also top-left/y-down.

## Consequences

- Markup geometry survives zoom changes, window resizes, and save/reload without drift, because it is never stored in scene space.
- A single, unit-tested pair of transform functions is the only place coordinate bugs can hide, instead of one place per tool.
- Every new tool added in Phase 3+ must convert through `app/core` rather than reimplementing math; this is a code-review checklist item, not just a convention.
- Caught before Phase 3's drafting tools were built on top of it — worth flagging in case Phase 5 (measurement, real-world units) or Phase 7 (redaction rects) code ever needs to reason about "which way is up" again: the answer is always "same as the rendered image," never "same as the PDF spec's content stream."
