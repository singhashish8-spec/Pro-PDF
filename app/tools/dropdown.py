from app.tools.form_field_tool import FormFieldTool


class DropdownTool(FormFieldTool):
    tool_id = "dropdown"
    markup_type = "dropdown"
    extra_prompt = "Options, comma-separated (e.g. Yes,No,Maybe)"
