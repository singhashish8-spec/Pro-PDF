# ADR 0004: Sidecar journal file for autosave/crash recovery

**Status:** Accepted
**Context:** Blueprint v2, Section 6.5

## Decision

The Glass Layer (the in-memory list of `MarkupObject`s) is the working document; the PDF binary itself is only touched at load and at save/export (ADR 0002, Section 6.4). Between saves, the app periodically serializes the current `MarkupObject` list to a sidecar journal file next to the open PDF:

```
filename.pdf.pdfpro-journal
```

The journal is written every N seconds and/or after every command pushed onto the undo stack (ADR 0003). On launch, if a journal file exists for a file being opened, the app prompts the user to recover it before falling back to the last saved version baked into the PDF.

## Consequences

- A crash loses at most the autosave interval of work, satisfying the crash-recovery target in Section 8 of the blueprint.
- The journal format is the same JSON `MarkupObject` list used everywhere else (ADR 0002), so no separate serialization format needs to be maintained.
- The journal file must be excluded from version control and cleaned up on a normal save (handled in `app/persistence/`); `*.pdfpro-journal` is added to `.gitignore`.
