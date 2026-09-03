# ADR 0003: Command-pattern undo/redo, built in Phase 2

**Status:** Accepted
**Context:** Blueprint v2, Section 6.3; Risk Register, Section 9

## Decision

Every user action that changes document state (add object, delete object, move object, change style, calibrate scale, etc.) is represented as a `Command` object with `do()` and `undo()` methods, pushed onto an undo stack living in `app/commands/`.

The command stack is built in Phase 2, alongside the Glass Layer and before any drafting tool (Phase 3) exists. Every tool built from Phase 3 onward emits `Command` objects instead of mutating `MarkupObject` state directly.

## Consequences

- Undo/redo work uniformly across every tool without per-tool retrofitting, because no tool is allowed to bypass the command stack.
- Tool implementations are slightly more indirect (construct-and-push a command rather than mutate in place), which is the intended tradeoff.
- This was the single most expensive omission in v1 of the blueprint (see Risk Register); building it first removes that risk entirely rather than mitigating it later.
