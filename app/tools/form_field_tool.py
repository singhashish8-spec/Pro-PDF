"""Shared base for AcroForm field placement tools (Blueprint v2, Section 7.3).

Drag a rect like the drafting shapes, then name the field. `obj.text` holds
"<field name>\\n<extra>", where <extra> is the default value (text/date
fields) or a comma-separated option list (dropdown) — kept this way rather
than widening the MarkupObject schema for a handful of field types.
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class FormFieldTool(Tool):
    markup_type: str = "text_field"
    #: Subclasses that need a second prompt (e.g. dropdown options) override this.
    extra_prompt: str | None = None

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        draft = MarkupObject(
            type=self.markup_type,
            page_index=self.context.page_index,
            points=[self._start, pdf_point],
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if self._start is None:
            return
        points = [self._start, pdf_point]
        self._start = None
        if points[0] == points[1]:
            return

        name = self.context.text_provider("Field name")
        if not name:
            return
        text = name.strip()
        if self.extra_prompt:
            text = f"{text}\n{self._get_extra()}"

        style = self.context.default_style
        obj = MarkupObject(
            type=self.markup_type,
            page_index=self.context.page_index,
            points=points,
            text=text,
            style=style.__class__(**style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    def _get_extra(self) -> str:
        """Prompts for the extra value; subclasses override to add validation."""
        return self.context.text_provider(self.extra_prompt) or ""

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
