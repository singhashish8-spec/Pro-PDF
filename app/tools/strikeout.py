from app.tools.text_markup_tool import TextLineMarkupTool


class StrikeoutTool(TextLineMarkupTool):
    tool_id = "strikeout"
    markup_type = "strikeout"
    vertical_fraction = 0.5  # through the middle of the text
