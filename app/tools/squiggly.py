from app.tools.geometry import wavy_points
from app.tools.text_markup_tool import TextLineMarkupTool


class SquigglyTool(TextLineMarkupTool):
    tool_id = "squiggly"
    markup_type = "squiggly"
    vertical_fraction = 0.95

    def _line_points(self, x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
        y = y0 + (y1 - y0) * self.vertical_fraction
        return wavy_points(x0, x1, y, amplitude=1.5, wavelength=6.0)
