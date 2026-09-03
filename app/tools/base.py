"""Shared Tool base class (Blueprint v2, Section 5).

A tool never mutates MarkupDocument directly — it builds MarkupObjects and
pushes Command objects onto the CommandStack (ADR 0003). Concrete tools are
added starting Phase 3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import Style
from app.models.project import Calibration, MarkupDocument

#: Prompts the user for text given a dialog title; returns None if cancelled.
TextProvider = Callable[[str], "str | None"]
#: Called with a draft MarkupObject while a tool is actively drawing, or None to clear the preview.
PreviewCallback = Callable[["object | None"], None]
#: Called with the selected object's id (or None) when SelectTool's selection changes.
SelectionCallback = Callable[["str | None"], None]


@dataclass
class ToolContext:
    document: MarkupDocument
    command_stack: CommandStack
    page_index: int
    default_style: Style
    pdf: PDFDocument
    text_provider: TextProvider
    preview_callback: PreviewCallback
    selection_callback: SelectionCallback = lambda obj_id: None
    author: str = "user"
    #: The scale (Section 7.2) measurement tools should use for the current page, if any has been set.
    active_calibration: "Calibration | None" = None


class Tool(ABC):
    tool_id: str = "base"
    cursor: str = "cross"

    def __init__(self, context: ToolContext) -> None:
        self.context = context

    def activate(self) -> None:
        """Called when the tool becomes the active tool."""

    def deactivate(self) -> None:
        """Called when a different tool becomes active; must leave no partial state."""
        self.context.preview_callback(None)

    @abstractmethod
    def on_press(self, pdf_point: tuple[float, float]) -> None: ...

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        """Optional: called while the tool is actively drawing."""

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        """Optional: called on mouse release; most tools finalize here."""
