"""Digital signature field placeholder (Blueprint v2, Section 7.3) — an
empty AcroForm signature widget, distinct from the SignatureTool that
actually captures a drawn/typed signature (app/tools/signature_tool.py)."""

from app.tools.form_field_tool import FormFieldTool


class SignatureFieldTool(FormFieldTool):
    tool_id = "signature_field"
    markup_type = "signature_field"
