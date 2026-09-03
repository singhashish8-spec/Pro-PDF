"""MarkupObject: the common shape for every annotation, measurement, form field,
and shape in the Glass Layer (Blueprint v2, Section 6.2 / ADR 0002)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

MARKUP_TYPES = (
    "rectangle",
    "ellipse",
    "arrow",
    "pen",
    "highlight",
    "underline",
    "strikeout",
    "squiggly",
    "note",
    "stamp",
    "textbox",
    "callout",
    "cloud",
    "eraser",
    "signature",
    "text_field",
    "checkbox",
    "radio_button",
    "date_field",
    "dropdown",
    "signature_field",
    "measure_linear",
    "measure_area",
    "measure_count",
    "measure_perimeter",
    "redaction",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Style:
    stroke_color: str = "#339AF0"
    fill_color: str | None = None
    line_width: float = 2.0
    opacity: float = 1.0
    font_size: float = 12.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stroke_color": self.stroke_color,
            "fill_color": self.fill_color,
            "line_width": self.line_width,
            "opacity": self.opacity,
            "font_size": self.font_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Style":
        data = data or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Measurement:
    calibration_id: str | None = None
    value: float = 0.0
    unit: str = "ft"

    def to_dict(self) -> dict[str, Any]:
        return {"calibration_id": self.calibration_id, "value": self.value, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Measurement | None":
        if not data:
            return None
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MarkupObject:
    type: str
    page_index: int
    points: list[tuple[float, float]] = field(default_factory=list)
    text: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    style: Style = field(default_factory=Style)
    measurement: Measurement | None = None
    author: str = "user"
    created_at: str = field(default_factory=_now_iso)
    modified_at: str = field(default_factory=_now_iso)
    layer: str = "default"
    linked_form_field: str | None = None

    def __post_init__(self) -> None:
        if self.type not in MARKUP_TYPES:
            raise ValueError(f"Unknown markup type: {self.type!r}")

    def touch(self) -> None:
        self.modified_at = _now_iso()

    def clone(self, **overrides: Any) -> "MarkupObject":
        return replace(self, **overrides)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "page_index": self.page_index,
            "geometry": {
                "points": [list(p) for p in self.points],
                "note": "PDF page space: top-left origin, y-down, unaffected by zoom (see ADR 0001)",
            },
            "text": self.text,
            "style": self.style.to_dict(),
            "measurement": self.measurement.to_dict() if self.measurement else None,
            "author": self.author,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "layer": self.layer,
            "linked_form_field": self.linked_form_field,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarkupObject":
        geometry = data.get("geometry") or {}
        points = [tuple(p) for p in geometry.get("points", [])]
        return cls(
            type=data["type"],
            page_index=data["page_index"],
            points=points,
            text=data.get("text", ""),
            id=data.get("id", str(uuid.uuid4())),
            style=Style.from_dict(data.get("style")),
            measurement=Measurement.from_dict(data.get("measurement")),
            author=data.get("author", "user"),
            created_at=data.get("created_at", _now_iso()),
            modified_at=data.get("modified_at", _now_iso()),
            layer=data.get("layer", "default"),
            linked_form_field=data.get("linked_form_field"),
        )
