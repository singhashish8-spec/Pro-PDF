# ADR 0001: Dual coordinate systems with centralized transforms

**Status:** Accepted
**Context:** Blueprint v2, Section 6.1

## Decision

The app deals with two coordinate systems everywhere a markup object's position is touched:

- **PDF user space** — origin at bottom-left, defined by the PDF spec, independent of zoom/DPI. This is the system every `MarkupObject.geometry` is stored in.
- **Scene/screen space** — origin at top-left, affected by zoom level, pan offset, and DPI scaling. This is the system tools operate in while the user is actively drawing, for responsiveness.

Two conversion functions, `scene_to_pdf` and `pdf_to_scene`, are implemented exactly once in `app/core/` and imported everywhere a conversion is needed. No tool, panel, or service computes its own transform.

## Consequences

- Markup geometry survives zoom changes, window resizes, and save/reload without drift, because it is never stored in scene space.
- A single, unit-tested pair of transform functions is the only place coordinate bugs can hide, instead of one place per tool.
- Every new tool added in Phase 3+ must convert through `app/core` rather than reimplementing math; this is a code-review checklist item, not just a convention.
