from app.tools.form_field_tool import FormFieldTool


class TextFieldTool(FormFieldTool):
    tool_id = "text_field"
    markup_type = "text_field"
    extra_prompt = "Default value (optional)"
