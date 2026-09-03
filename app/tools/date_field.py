"""Date field: validates the default value is ISO ``YYYY-MM-DD`` before
accepting it (Blueprint v2, Section 7.3 — field validation logic)."""

from __future__ import annotations

import re

from app.tools.form_field_tool import FormFieldTool

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DateFieldTool(FormFieldTool):
    tool_id = "date_field"
    markup_type = "date_field"
    extra_prompt = "Default date (YYYY-MM-DD, optional)"

    def _get_extra(self) -> str:
        for _ in range(2):
            value = (self.context.text_provider(self.extra_prompt) or "").strip()
            if not value or _DATE_RE.match(value):
                return value
            self.extra_prompt = f'"{value}" isn\'t YYYY-MM-DD — try again (or leave blank)'
        return ""
