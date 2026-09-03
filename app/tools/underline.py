from app.tools.text_markup_tool import TextLineMarkupTool


class UnderlineTool(TextLineMarkupTool):
    tool_id = "underline"
    markup_type = "underline"
    vertical_fraction = 0.95  # near the text baseline
