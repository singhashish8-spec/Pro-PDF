"""XFDF form data export/import (Blueprint v2, Section 7.3).

FDF/XFDF are listed together in the spec as equivalent form-data
interchange formats; XFDF (the XML one) is implemented here as the
modern, well-documented representative of the pair.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET

from app.models.markup import MarkupObject

_NS = "http://ns.adobe.com/xfdf/"
_FORM_TYPES = {"text_field", "checkbox", "radio_button", "date_field", "dropdown"}
ET.register_namespace("", _NS)


def export_xfdf(objects: list[MarkupObject], pdf_filename: str, output_path: str) -> int:
    """Writes field name/value pairs for every form-field MarkupObject. Returns the count written."""
    root = ET.Element(f"{{{_NS}}}xfdf")
    fields_el = ET.SubElement(root, f"{{{_NS}}}fields")
    count = 0
    for obj in objects:
        if obj.type not in _FORM_TYPES:
            continue
        name, _, extra = (obj.text or "").partition("\n")
        name = name.strip()
        if not name:
            continue
        field_el = ET.SubElement(fields_el, f"{{{_NS}}}field", {"name": name})
        value_el = ET.SubElement(field_el, f"{{{_NS}}}value")
        value_el.text = extra
        count += 1
    f_el = ET.SubElement(root, f"{{{_NS}}}f")
    f_el.set("href", pdf_filename)

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return count


def import_xfdf(path: str, page_index: int = 0, default_rect_size: tuple[float, float] = (180, 20)) -> list[MarkupObject]:
    """Parses field name/value pairs back into text_field MarkupObjects,
    stacked down the page; the caller can reposition them."""
    tree = ET.parse(path)
    root = tree.getroot()
    width, height = default_rect_size
    objects = []
    for i, field_el in enumerate(root.iter(f"{{{_NS}}}field")):
        name = field_el.get("name", "")
        value_el = field_el.find(f"{{{_NS}}}value")
        value = (value_el.text or "") if value_el is not None else ""
        y = 72 + i * (height + 10)
        obj = MarkupObject(
            id=str(uuid.uuid4()),
            type="text_field",
            page_index=page_index,
            points=[(72, y), (72 + width, y + height)],
            text=f"{name}\n{value}",
        )
        objects.append(obj)
    return objects
