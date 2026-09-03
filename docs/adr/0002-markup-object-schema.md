# ADR 0002: Common `MarkupObject` schema for all annotations

**Status:** Accepted
**Context:** Blueprint v2, Section 6.2

## Decision

Every annotation, measurement, form field, and shape — regardless of tool — is represented as one `MarkupObject` shape, serialized as JSON internally:

```json
{
  "id": "uuid-v4",
  "type": "rectangle | ellipse | arrow | pen | highlight | underline | strikeout | note | stamp | callout | cloud | text_field | checkbox | measure_linear | measure_area | measure_count | redaction",
  "page_index": 0,
  "geometry": { "points": [[x, y], [x, y]], "note": "always in PDF user space" },
  "style": { "stroke_color": "#339AF0", "fill_color": null, "line_width": 2, "opacity": 1.0 },
  "measurement": { "calibration_id": "uuid", "value": 14.5, "unit": "ft" },
  "author": "username",
  "created_at": "iso8601",
  "modified_at": "iso8601",
  "layer": "default",
  "linked_form_field": null
}
```

This is defined once as a data class in `app/models/` and is the contract shared by tools, the canvas (Glass Layer), the Markups List panel, the undo/redo command stack, and the save/export pipeline.

## Consequences

- Adding a new tool type means adding a `type` value and a renderer/exporter for it, not a new object shape or a new panel integration.
- The Markups List can display any object generically (id, type, page, author, timestamps) without per-type special-casing for the list view itself.
- `measurement` and `linked_form_field` are `null`/absent for object types that don't use them; fields are not repurposed per type.
