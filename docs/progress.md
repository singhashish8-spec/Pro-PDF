# Build Progress

Tracks completion of the phases in `docs/blueprint/pdf_pro_development_blueprint_v2.md`, Section 10. Updated at the end of every phase.

| Phase | Status | Notes |
|---|---|---|
| 0 — Foundations & Decisions | ✅ Done | ADRs 0001-0005, repo scaffolding |
| 1 — Core Shell & Dashboard | ✅ Done | `QMainWindow` shell, `theme.qss` tokens (light + dark), Home Dashboard with recent files |
| 2 — Rendering, Glass Layer, Undo/Redo | ⬜ Not started | |
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
