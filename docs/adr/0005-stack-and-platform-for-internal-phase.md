# ADR 0005: PyMuPDF + PyQt6 on Windows-only for the internal phase

**Status:** Accepted for the internal R&D phase; revisit before Phase 10
**Context:** Blueprint v2, Sections 3, 4, 8, 14

## Decision

For the internal R&D phase:

- **PDF engine:** PyMuPDF (`fitz`). All calls to it are confined to `app/core/` (Section 5 rule) so it can be swapped for `pypdfium2` (Apache/BSD) later without touching the rest of the app.
- **GUI framework:** PyQt6. `PySide6` (LGPL, official Qt for Python) is the identified fallback if the GPL/commercial licensing of PyQt6 becomes a blocker.
- **Platform target for v1:** Windows 10/11 only. Not tested or targeted on macOS/Linux yet, though PyQt6/PySide6 support them.

## Rationale

AGPL/GPL copyleft obligations are triggered by *distribution* or, for AGPL, by *network availability to third parties*. Internal-only use on company machines triggers neither, so this combination is acceptable to move fast during R&D without a licensing decision blocking Phase 1.

## Consequences

- Nothing here is a final decision. It **must** be revisited as a formal go/no-go before any of: code leaving the company, an external contributor getting write access, or commercial distribution (Section 3). Phase 10 (Section 10) is the designated checkpoint.
- Because all `fitz` calls are isolated to `app/core/` (enforced by repo structure, Section 5), swapping to `pypdfium2` is a contained change rather than a rewrite if that becomes necessary.
- Windows-only is a v1 scope decision, not an architectural one; PyQt6/PySide6 do not block cross-platform support later if dogfooding surfaces a need (Section 14, Open Decisions Log).
