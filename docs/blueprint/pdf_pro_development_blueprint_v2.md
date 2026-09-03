# PDF Pro: Development Blueprint v2 (Internal R&D Edition)

**Status:** Internal use only, no external distribution or outside contributor access during this phase.
**Audience:** Internal dev team and/or AI coding agents building this from scratch.
**Supersedes:** `pdf_pro_comprehensive_blueprint.md` (v1). This document keeps everything useful from v1 and fills in what was missing so a team (human or AI) can build from it without having to guess.

---

## 0. How to use this document

This is the single source of truth for PDF Pro during the internal R&D phase. If you are an AI coding agent picking this up cold: read this entire document before writing code, follow the phase order in Section 10, and do not skip Phase 0 (Section 10.0). If a decision here conflicts with something convenient to code, this document wins unless the product owner (Ashish) says otherwise.

---

## 1. Vision & Positioning

**What we are building:** A desktop PDF editor with a clean, Figma/Notion-inspired interface ("Corporate-Figma Hybrid"), aimed first at architecture, engineering, and construction (AEC) workflows, the same space Bluebeam Revu dominates. General office/legal features (the Acrobat side: forms, redaction, signatures) come after the AEC core is solid, not in parallel with it.

**Why AEC first, not "Acrobat and Bluebeam at once":** Trying to match two mature, decades-old products in every dimension at launch is how projects stall. AEC-first gives us a real, scoped wedge, a built-in test group (our own BIM team at HSA), and a feature set (measurement, takeoff, markup) that plays directly to domain knowledge we already have.

**Current phase:** Internal R&D. Used only by our own team, on our own machines, for capability testing. No outside installs, no public repo, no external contributors. This affects licensing decisions (Section 3) and the roadmap (Section 10): we can move fast now and revisit distribution-sensitive decisions before anything leaves the building.

---

## 2. Product Scope for v1 (Internal Alpha)

**In scope for v1:**
Core shell and dashboard, PDF rendering with pan/zoom, the Glass Layer annotation system, the full drafting/annotation tool set, the AEC measurement and takeoff tool set, the Markups List, basic page and document management, AcroForms, redaction, OCR, search, and document comparison.

**Explicitly out of scope for v1 (v2 or later):**
Real-time multi-user collaboration (Bluebeam Studio style live sessions), mobile/tablet companion app, cloud storage sync, plugin/extension marketplace, print production tooling (color separations, preflight), full accessibility (PDF/UA) tagging, localization beyond English.

Reasoning: these either require infrastructure we do not need yet (a backend/server for collaboration) or are premature before the core single-user experience is proven internally.

---

## 3. Licensing & Legal (Internal Phase)

**Current stance:** Internal use only, no distribution outside the company, no external contributors, no CLA/DCO needed yet.

**Why this is fine for now:** Copyleft obligations in licenses like AGPL and GPL are generally triggered by *distributing* the software or, for AGPL specifically, by *making it available to third parties over a network*. Internal use by employees on company machines for internal testing does not trigger either. This is a legitimate way to move fast during R&D.

**What is NOT resolved, and must be revisited before any of the following happens:**
- Before any code leaves the company (public repo, open sourcing, sharing a build with an outside party, a pilot with another firm)
- Before any external contributor gets write access
- Before any commercial distribution or sale

**Current dependencies and their licenses (for the record, so this isn't forgotten):**
| Library | License | Note |
|---|---|---|
| PyMuPDF (fitz) | AGPL-3.0 (or commercial from Artifex) | Fine for internal-only use now. Must be resolved (commercial license, or swap to `pypdfium2`, Apache/BSD) before external distribution. |
| PyQt6 | GPL-3.0 (or commercial from Riverbank) | Same situation. `PySide6` (official Qt for Python, LGPL) is a drop-in-ish alternative that avoids this entirely, worth evaluating during Phase 0. |

**Action item for later (not now):** When we get within a few weeks of any external release, revisit this table as a formal go/no-go decision, not an afterthought. Flag it now, decide it then.

**Data handling note:** PDFs frequently contain confidential client and legal content. Even in internal testing, do not use any cloud-based OCR, telemetry, or crash reporting service that uploads document content off our machines. Anything like that needs an explicit decision, not a default.

---

## 4. Technology Stack

- **Language:** Python 3.11+
- **PDF engine:** PyMuPDF (`fitz`) for the internal phase (see Section 3 for the caveat)
- **GUI framework:** PyQt6 (see Section 3 for the caveat)
- **Rendering approach:** PDF pages rendered to raster images as a background layer; a transparent `QGraphicsScene` ("the Glass Layer") sits on top and owns all interactive objects. Nothing is drawn directly onto the PDF until save/export time.
- **Data persistence:** SQLite for the Markups List and project metadata; JSON for the in-memory/serialized markup object model (see Section 6.2)
- **Testing:** `pytest` for unit and integration tests
- **Packaging (internal builds only for now):** PyInstaller, unsigned builds are fine internally; code signing becomes relevant only at external release

---

## 5. Repository Structure

```
pdf-pro/
  app/
    core/            # PDF engine wrapper (fitz calls live ONLY here), coordinate transforms, file I/O
    models/          # MarkupObject, Page, Project, FormField, Calibration data classes
    tools/           # One file per tool (rectangle.py, arrow.py, measure_linear.py, ...), shared Tool base class
    commands/         # Undo/redo command objects (Command pattern, see Section 6.3)
    ui/
      dashboard/       # Home screen: recent files, quick actions
      canvas/          # QGraphicsScene viewport, zoom/pan, the Glass Layer
      panels/          # Right pane accordion, Markups List, floating context menu
      theme/           # theme.qss, design tokens (colors, radii, spacing)
    services/         # OCR, redaction, export, document compare, search
    persistence/       # Autosave, project file format, recent files list
  tests/
    fixtures/          # Test PDF corpus (see Section 11.2)
    unit/
    integration/
  docs/
    architecture/       # How the Glass Layer, undo stack, and coordinate system work
    adr/                # Architecture Decision Records, one short file per major decision
  scripts/              # Dev environment setup, build scripts
  pyproject.toml
  README.md
```

**Rule:** All direct calls to `fitz` (PyMuPDF) live inside `app/core/`. No other module talks to PyMuPDF directly. This is what makes swapping the PDF engine later (Section 3) a contained change instead of a rewrite.

---

## 6. Core Architecture

### 6.1 The Glass Layer and coordinate systems

Two coordinate systems are in play at all times, and mixing them up is the single most common source of bugs in this kind of app:
- **PDF user space:** origin at bottom-left of the page, defined by the PDF spec, unaffected by zoom or screen resolution.
- **Scene/screen space:** origin at top-left, affected by zoom level, pan offset, and DPI scaling.

Every tool works in scene space while the user is drawing (for responsiveness), but every markup object stores its geometry in PDF user space internally, so it stays correct across zoom changes, window resizes, and save/reload. Write the transform functions (`scene_to_pdf`, `pdf_to_scene`) once, in `app/core/`, and use them everywhere. Do not let individual tools compute their own transforms.

### 6.2 Markup object data model

Every annotation, measurement, form field, and shape is a `MarkupObject` with a common shape, serialized as JSON internally:

```json
{
  "id": "uuid-v4",
  "type": "rectangle | ellipse | arrow | pen | highlight | underline | strikeout | note | stamp | callout | cloud | text_field | checkbox | measure_linear | measure_area | measure_count | redaction",
  "page_index": 0,
  "geometry": { "points": [[x, y], [x, y]], "note": "always in PDF user space" },
  "style": { "stroke_color": "#339AF0", "fill_color": null, "line_width": 2, "opacity": 1.0 },
  "measurement": { "calibration_id": "uuid", "value": 14.5, "unit": "ft" },
  "author": "username",
  "created_at": "iso8601",
  "modified_at": "iso8601",
  "layer": "default",
  "linked_form_field": null
}
```

This is the object that the Markups List panel reads from, that gets baked into the PDF on save, and that undo/redo commands operate on. Treat this schema as the contract between tools, the canvas, the Markups List, and the save/export pipeline.

### 6.3 Undo/redo (build this in Phase 2, not later)

Use the Command pattern: every user action that changes document state (add object, delete object, move object, change style, calibrate scale) is a `Command` object with `do()` and `undo()` methods, pushed onto a stack. This was missing entirely from v1 of the blueprint and is not optional; retrofitting undo/redo after tools already exist means touching every tool a second time. Build the command stack in Phase 2 alongside the Glass Layer, and every tool built afterward emits commands instead of mutating state directly.

### 6.4 Save/export pipeline

The Glass Layer is the working document. The actual PDF binary is only touched at two points: load (render pages to background images) and save/export (translate every `MarkupObject` from PDF user space into `fitz` drawing calls and bake them in). This keeps editing fast and reversible, and keeps all PyMuPDF-specific code contained to one pipeline.

### 6.5 Autosave and crash recovery

Every N seconds (or after every command), serialize the current `MarkupObject` list to a sidecar journal file (`filename.pdf.pdfpro-journal`) next to the open file. On launch, if a journal file exists for a file being opened, prompt to recover. This is cheap to build now and prevents losing an afternoon of markup work to a crash.

---

## 7. Complete Feature Specification

This consolidates the original v1 feature list with everything identified as missing. Each item notes which phase it targets (Section 10).

### 7.1 Drafting & Annotation
Rectangle, Ellipse (Phase 3) · Arrow/Line (Phase 3) · Pen/freehand (Phase 3) · Highlighter with text-baseline snapping (Phase 3) · **Underline, strikeout, squiggly underline, tied to actual selected text, not freehand** (Phase 3) · **Sticky note/comment** (Phase 3) · **Stamp, including dynamic stamps with auto-filled date/user** (Phase 3) · **Text box/Typewriter tool** (Phase 3) · **Callout** (Phase 3) · **Cloud/polygon markup** (Phase 3, AEC-standard for redlines) · **Eraser** (Phase 3) · **Real signature tool** (draw, type, or image-based signature, distinct from freehand pen) (Phase 7)

### 7.2 Engineering & Measurement (our AEC wedge, prioritize this)
Scale calibration, per-page, savable (Phase 5) · Linear distance with live-updating dimension label (Phase 5) · Area measurement (Phase 5) · **Count tool** (click-to-tally, e.g. door/window counts) (Phase 5) · **Diameter/radius and perimeter for irregular shapes** (Phase 5) · **Multiple saved scales per document** (Phase 5) · **Tool Chest: save and reuse custom markup sets and symbols across projects** (Phase 5, this is the single most important Bluebeam-parity feature to get right)

### 7.3 Interactive Forms
Text field, checkbox, dropdown (Phase 7) · **Radio buttons, date fields** (Phase 7) · **Digital signature field** (Phase 7) · **Form data export/import (FDF/XFDF)** (Phase 7) · **Field validation/calculation logic** (Phase 7)

### 7.4 Document & Page Management (entirely missing from v1)
**Insert, delete, rotate, reorder, extract pages** (Phase 6) · **Merge/split** (already a dashboard action in v1, needs a real tool behind it) (Phase 6) · **Bates numbering, watermarking, headers/footers** (Phase 6) · **Bookmarks/table of contents editing** (Phase 6) · **Editing existing PDF text in place (paragraph reflow)**, this is materially different from annotation and should be scoped as its own effort (Phase 8, stretch goal, flag as high difficulty)

### 7.5 Security
**Password protection and permission restrictions** (Phase 7) · Redaction, draw-a-box-to-permanently-erase (Phase 7) · **Search-and-redact-all-instances (e.g. every SSN pattern in a document)** (Phase 8) · **Metadata scrubbing** (Phase 7) · Redaction must have an automated test verifying the underlying content is actually destroyed, not just visually covered (Section 11)

### 7.6 Enterprise/Review Features
Markups List panel, sortable spreadsheet view of every object (Phase 6) · **Document Compare (visual diff between two PDF versions)** (Phase 8) · OCR (Phase 8) · **Search within document, find and replace** (Phase 8)

### 7.7 Cross-cutting UX
**Undo/redo** (Phase 2, foundational, see 6.3) · Floating context menu (Phase 4) · **Command palette (Cmd/Ctrl+K)** (Phase 4) · **Dark mode**, build the token system to support it from the start even if light mode ships first (Phase 1) · **External file change detection** (file changed on disk while open) (Phase 6)

### 7.8 Deferred to v2 (post internal-alpha)
Real-time multi-user collaboration and Studio-style sessions · Mobile/tablet companion app · Plugin/extension system · Full accessibility (PDF/UA) tagging and screen reader support · Localization/i18n · Cloud storage integration · Print production tooling (color separations, preflight)

---

## 8. Non-Functional Requirements

| Category | Target |
|---|---|
| Platform (v1) | Windows 10/11 only. Mac/Linux is a v2 decision, PyQt6/PySide6 support it but it is not being tested or targeted now. |
| File size | Must open and remain responsive with PDFs up to 500MB / 1000 pages |
| Performance | A 200-page PDF should open and become interactive in under 2 seconds on a mid-range machine |
| Supported PDF versions | 1.4 through 2.0, including encrypted and form-heavy files |
| Markup object count | Canvas must stay responsive with 5,000+ objects in the Glass Layer on one document |
| Crash recovery | No more than the last autosave interval of work should be lost on a crash |

---

## 9. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| PyMuPDF/PyQt6 licensing becomes a blocker later | Could force a rendering-layer rewrite right before launch | Flag it now (Section 3), decide before any external step, evaluate `pypdfium2` + `PySide6` early so the door stays open |
| Redaction doesn't actually destroy underlying data | Legal liability, real-world precedent of "redacted" PDFs leaking text | Automated test suite specifically for this (Section 11), never ship without it passing |
| Scope creep, trying to match Acrobat and Bluebeam simultaneously | Project never ships | AEC-first scope discipline (Section 2), defer list (7.8) is not optional |
| Undo/redo bolted on late | Expensive rework across every tool | Build the command stack in Phase 2, before any tool beyond the shell exists |
| Large file performance | Unusable on real-world construction drawing sets | Performance targets in Section 8, test against the large-file fixtures in Section 11.2 from Phase 2 onward |
| Malicious/malformed PDFs (parser exploits) | Security/stability | Test corpus includes malformed and adversarial PDFs from the start, not added later |

---

## 10. Phased Development Roadmap (Revised)

Timeline is internal-only and sequential; adjust for actual team size and AI-assisted development velocity.

### Phase 0: Foundations & Decisions (before Phase 1 starts)
Finalize the coordinate system approach (6.1), the markup object schema (6.2), the undo/redo design (6.3), and the project/autosave file format (6.5). Set up the repo structure (Section 5), dev environment, and pytest scaffolding. Collect the test PDF corpus (Section 11.2). Confirm Windows-only target for v1. Write these decisions up as short ADRs in `docs/adr/`.

### Phase 1: Core Shell & Dashboard (Weeks 1-2)
`QMainWindow`, `theme.qss` including dark mode tokens even if unused yet, Home Dashboard (recent files, quick actions).
*Milestone:* Empty shell, looks and feels right.

### Phase 2: Rendering, Glass Layer, Undo/Redo (Weeks 3-4)
PyMuPDF page rendering, transparent `QGraphicsScene`, zoom/pan, coordinate transform functions, and the full undo/redo command stack.
*Milestone:* Open a PDF, zoom/pan smoothly, and the undo stack exists and is wired up before any tool is built.

### Phase 3: Drafting Suite v1 (Weeks 5-6)
All of Section 7.1: shapes, pen, highlighter, text markup (underline/strikeout), sticky notes, stamps, callouts, cloud markup, eraser.
*Milestone:* Full annotation set, all changes go through undo/redo.

### Phase 4: Floating Menu, Command Palette, UX Polish (Weeks 7-8)
Floating context menu, command palette, real-time style editing on selected objects.
*Milestone:* The "Figma feel" is achieved.

### Phase 5: Engineering & Measurement Suite (Weeks 9-10)
All of Section 7.2, including the Tool Chest. This is the competitive differentiator, do not rush it.
*Milestone:* A real AEC user could do a basic takeoff in this app.

### Phase 6: Document & Page Management + Markups List (Weeks 11-12)
All of Section 7.4 plus the Markups List panel (backed by SQLite).
*Milestone:* Full page-level document control, plus a real review/audit trail of every markup.

### Phase 7: Forms, Redaction, Security Basics, Signatures (Weeks 13-14)
All of Section 7.3, 7.5 (except search-and-redact), and the real signature tool.
*Milestone:* Redaction ships only after passing the destruction-verification test suite (Section 11).

### Phase 8: OCR, Search, Compare, Search-and-Redact (Weeks 15-16)
All of Section 7.6 remaining items.

### Phase 9: Internal Dogfooding & Hardening (Weeks 17-18)
Deploy to the HSA BIM team for real daily use. Collect friction points directly. Performance-tune against real project files (large drawing sets, not just synthetic fixtures). Fix crashes and rough edges found in real use, this is the most valuable testing this project will get and it is free.

### Phase 10: External Readiness Decision Point (after Phase 9, not before)
Revisit Section 3 licensing table as a formal decision with real usage data in hand. Decide: open source publicly, stay proprietary, or open-core. If going public: set up CLA/DCO, choose the actual license, resolve PyMuPDF/PyQt6, set up code signing and an installer/update mechanism. If staying internal longer: just keep iterating from Phase 9 feedback.

---

## 11. Testing & QA

### 11.1 Automated testing
`pytest` unit tests for coordinate transform math (this is where subtle bugs hide), the command stack (every command's `do()`/`undo()` pair), and the save/export pipeline (round-trip: create objects, save, reload, verify objects match). Integration tests that open real PDFs from the fixture corpus and exercise each tool programmatically.

### 11.2 Test PDF corpus (build this in Phase 0)
Collect and check into `tests/fixtures/`: a large (500+ page) PDF, an encrypted/password-protected PDF, a corrupted/malformed PDF, a scanned image-only PDF (for OCR testing), a form-heavy AcroForm PDF, a PDF with non-Latin fonts, and a real anonymized architectural drawing set from an HSA project (with client-sensitive info removed) for realistic AEC testing.

### 11.3 Redaction verification (non-negotiable before Phase 7 ships)
An automated test that redacts text in a fixture PDF, saves it, then attempts to extract text and images from the redacted region programmatically, and asserts nothing is recoverable. This must pass before redaction is considered done, not just visually reviewed.

### 11.4 Manual QA
Phase 9 dogfooding at HSA is the primary manual QA pass. Track issues found there the same way as any bug, with priority given to anything that causes data loss or crashes.

---

## 12. Team & Roles (Internal Phase)

Even for a small or AI-assisted team, assign these responsibilities explicitly so nothing falls through:
- **Product owner:** Ashish, scope decisions, AEC domain expertise, final call on feature priority and the Section 3 licensing decision.
- **Engineering (human and/or AI agents):** Own `app/core/`, `app/tools/`, `app/commands/` per the architecture in Section 6. One owner per module keeps the `fitz`-only-in-core rule enforced.
- **QA:** Owns the fixture corpus (11.2) and the redaction verification suite (11.3) specifically, these should not be an afterthought assigned to whoever is free.
- **Internal test users:** The HSA BIM team, Phase 9 onward.

---

## 13. Glossary

- **AcroForm:** The PDF spec's native interactive form format (text fields, checkboxes, etc.)
- **OCG (Optional Content Group):** PDF's native "layers" mechanism, used heavily in CAD-exported PDFs
- **PDF/A:** Archival PDF standard, no external dependencies, used for long-term document retention
- **PDF/UA:** Accessibility standard for PDFs (tagged structure, screen reader support)
- **AGPL/GPL/LGPL:** Open source license families with different obligations around distribution and network use, see Section 3
- **Glass Layer:** This project's term for the transparent interactive `QGraphicsScene` rendered on top of the static PDF page image
- **Tool Chest:** Bluebeam's term (adopted here) for a saved, reusable set of custom markup tools/symbols

---

## 14. Open Decisions Log

Track unresolved questions here as they come up, so nothing gets silently decided by default:
- Final call on `PyMuPDF`/`PyQt6` vs `pypdfium2`/`PySide6` (Section 3), before Phase 10.
- Whether editing existing PDF text (7.4) stays in v1 scope or moves to v2, revisit after Phase 6.
- Windows-only vs cross-platform for v1, currently Windows-only (Section 8), revisit if dogfooding surfaces a need.
