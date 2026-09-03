# PDF Pro

Internal R&D desktop PDF editor for AEC (architecture/engineering/construction) workflows — a Figma/Notion-styled markup and takeoff tool, built first for the AEC wedge before broader Acrobat-style features.

**Status:** Internal use only. No external distribution, no outside contributor access, during this phase.

## Start here

The single source of truth for this project is the blueprint:

- [`docs/blueprint/pdf_pro_development_blueprint_v2.md`](docs/blueprint/pdf_pro_development_blueprint_v2.md)

It covers vision/scope, licensing status, the architecture (Glass Layer, coordinate systems, undo/redo, save/export), the full feature spec, and the phased roadmap. Read it before making changes.

Phase 0 decisions from the blueprint are recorded as ADRs in [`docs/adr/`](docs/adr/):

- [0001 — Coordinate systems](docs/adr/0001-coordinate-systems.md)
- [0002 — Markup object schema](docs/adr/0002-markup-object-schema.md)
- [0003 — Undo/redo command pattern](docs/adr/0003-undo-redo-command-pattern.md)
- [0004 — Autosave journal file](docs/adr/0004-autosave-project-file-format.md)
- [0005 — Stack and platform for the internal phase](docs/adr/0005-stack-and-platform-for-internal-phase.md)

## Dev setup

```bash
./scripts/setup_dev_env.sh
source .venv/bin/activate
pytest
```

Requires Python 3.11+.

## Repository layout

See Section 5 of the blueprint for the rationale. Summary:

- `app/core/` — the only place that talks to PyMuPDF (`fitz`) directly
- `app/models/` — `MarkupObject` and related data classes
- `app/tools/` — one module per drafting/measurement tool
- `app/commands/` — undo/redo `Command` objects
- `app/ui/` — dashboard, canvas (Glass Layer), panels, theme
- `app/services/` — OCR, redaction, export, compare, search
- `app/persistence/` — autosave, project file format, recent files
- `tests/` — unit and integration tests, plus the fixture PDF corpus (not yet collected, see `tests/fixtures/README.md`)
- `docs/adr/` — Architecture Decision Records
- `docs/architecture/` — implementation write-ups for the systems above, added as they're built
