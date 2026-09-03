from app.tools.measure_polygon_tool import MeasurePolygonTool


class MeasurePerimeterTool(MeasurePolygonTool):
    tool_id = "measure_perimeter"
    markup_type = "measure_perimeter"
    mode = "perimeter"
