from app.tools.measure_circular_tool import MeasureCircularTool


class MeasureRadiusTool(MeasureCircularTool):
    tool_id = "measure_radius"
    markup_type = "measure_radius"
    label_prefix = "R"
