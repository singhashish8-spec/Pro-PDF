"""Shared Tool base class (Blueprint v2, Section 5).

A tool never mutates MarkupDocument directly — it builds MarkupObjects and
pushes Command objects onto the CommandStack (ADR 0003). Concrete tools are
added starting Phase 3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.commands.base import CommandStack
from app.models.markup import Style
from app.models.project import MarkupDocument


@dataclass
class ToolContext:
    document: MarkupDocument
    command_stack: CommandStack
    page_index: int
    default_style: Style


class Tool(ABC):
    tool_id: str = "base"
    cursor: str = "cross"

    def __init__(self, context: ToolContext) -> None:
        self.context = context

    def activate(self) -> None:
        """Called when the tool becomes the active tool."""

    def deactivate(self) -> None:
        """Called when a different tool becomes active; must leave no partial state."""

    @abstractmethod
    def on_press(self, pdf_point: tuple[float, float]) -> None: ...

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        """Optional: called while the tool is actively drawing."""

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        """Optional: called on mouse release; most tools finalize here."""
