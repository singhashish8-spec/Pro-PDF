from app.tools.measure_circular_tool import MeasureCircularTool


class MeasureDiameterTool(MeasureCircularTool):
    tool_id = "measure_diameter"
    markup_type = "measure_diameter"
    label_prefix = "⌀"
