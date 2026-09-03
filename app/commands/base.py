"""Command pattern undo/redo stack (Blueprint v2, Section 6.3 / ADR 0003).

Built before any drafting tool exists; every tool from Phase 3 onward must
emit Command objects instead of mutating MarkupDocument state directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

StackListener = Callable[[], None]


class Command(ABC):
    """A single undoable user action."""

    label: str = "Action"

    @abstractmethod
    def do(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...


class CommandStack:
    def __init__(self) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._listeners: list[StackListener] = []

    def add_listener(self, listener: StackListener) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def push(self, command: Command) -> None:
        command.do()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        self._notify()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._notify()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.do()
        self._undo_stack.append(command)
        self._notify()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_label(self) -> str | None:
        return self._undo_stack[-1].label if self._undo_stack else None

    @property
    def redo_label(self) -> str | None:
        return self._redo_stack[-1].label if self._redo_stack else None

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()
