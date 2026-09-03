from app.tools.measure_polygon_tool import MeasurePolygonTool


class MeasureAreaTool(MeasurePolygonTool):
    tool_id = "measure_area"
    markup_type = "measure_area"
    mode = "area"
