import math

import pytest

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import Style
from app.models.project import Calibration, MarkupDocument
from app.tools.base import ToolContext
from app.tools.calibration_tool import CalibrationTool, parse_distance_input
from app.tools.measure_area import MeasureAreaTool
from app.tools.measure_count import MeasureCountTool
from app.tools.measure_diameter import MeasureDiameterTool
from app.tools.measure_linear import MeasureLinearTool
from app.tools.measure_perimeter import MeasurePerimeterTool
from app.tools.measure_radius import MeasureRadiusTool
from app.tools.measurement_math import (
    format_measurement,
    path_length,
    polygon_area,
    polygon_perimeter,
    to_real_area,
    to_real_length,
)


@pytest.fixture
def context(make_pdf):
    path = make_pdf(page_count=1)
    pdf = PDFDocument()
    pdf.open(path)
    document = MarkupDocument()
    stack = CommandStack()
    texts = iter(["20 ft", "not a number", ""])
    return ToolContext(
        document=document,
        command_stack=stack,
        page_index=0,
        default_style=Style(),
        pdf=pdf,
        text_provider=lambda title: next(texts, None),
        preview_callback=lambda obj: None,
    )


# -- measurement_math --------------------------------------------------------


def test_path_length_straight_line():
    assert path_length([(0, 0), (3, 4)]) == pytest.approx(5.0)


def test_polygon_area_unit_square():
    assert polygon_area([(0, 0), (10, 0), (10, 10), (0, 10)]) == pytest.approx(100.0)


def test_polygon_perimeter_square():
    assert polygon_perimeter([(0, 0), (10, 0), (10, 10), (0, 10)]) == pytest.approx(40.0)


def test_to_real_length_uses_scale_factor():
    cal = Calibration(id="c1", page_index=0, pdf_distance=10, real_distance=20, unit="ft")
    value, unit = to_real_length(5, cal)
    assert value == pytest.approx(10.0)  # 5 pdf pts * (20/10) scale
    assert unit == "ft"


def test_to_real_length_uncalibrated_passthrough():
    value, unit = to_real_length(5, None)
    assert value == 5
    assert unit == "pt"


def test_to_real_area_squares_the_scale_factor():
    cal = Calibration(id="c1", page_index=0, pdf_distance=10, real_distance=20, unit="ft")
    value, unit = to_real_area(100, cal)  # scale_factor=2 -> area factor 4
    assert value == pytest.approx(400.0)
    assert unit == "ft²"


def test_format_measurement():
    assert format_measurement(12.3456, "ft") == "12.35 ft"


# -- calibration input parsing ------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("20 ft", (20.0, "ft")),
        ("3.5m", (3.5, "m")),
        ("12", (12.0, "ft")),
        ("", None),
        ("abc", None),
    ],
)
def test_parse_distance_input(text, expected):
    assert parse_distance_input(text) == expected


def test_calibration_tool_creates_calibration(context):
    tool = CalibrationTool(context)
    tool.on_press((0, 0))
    tool.on_release((100, 0))  # 100 pdf points, user enters "20 ft"
    cals = context.document.calibrations_for_page(0)
    assert len(cals) == 1
    assert cals[0].pdf_distance == pytest.approx(100.0)
    assert cals[0].real_distance == 20.0
    assert cals[0].unit == "ft"
    assert cals[0].scale_factor == pytest.approx(0.2)


def test_calibration_tool_bad_input_creates_nothing(context):
    tool = CalibrationTool(context)
    tool.on_press((0, 0))
    tool.on_release((100, 0))  # consumes "20 ft"
    tool2 = CalibrationTool(context)
    tool2.on_press((0, 0))
    tool2.on_release((50, 0))  # consumes "not a number" -> invalid
    assert len(context.document.calibrations_for_page(0)) == 1


# -- measurement tools ---------------------------------------------------------


def test_measure_linear_without_calibration_uses_pt(context):
    tool = MeasureLinearTool(context)
    tool.on_press((0, 0))
    tool.on_release((30, 40))
    obj = context.document.all_objects()[0]
    assert obj.type == "measure_linear"
    assert obj.measurement.value == pytest.approx(50.0)
    assert obj.measurement.unit == "pt"
    assert "50.00 pt" in obj.text


def test_measure_linear_with_calibration(context):
    context.active_calibration = Calibration(id="c1", page_index=0, pdf_distance=10, real_distance=1, unit="m")
    tool = MeasureLinearTool(context)
    tool.on_press((0, 0))
    tool.on_release((100, 0))
    obj = context.document.all_objects()[0]
    assert obj.measurement.value == pytest.approx(10.0)
    assert obj.measurement.unit == "m"


def test_measure_area_tool_requires_three_points(context):
    tool = MeasureAreaTool(context)
    tool.on_press((0, 0))
    tool.on_press((10, 0))
    tool.finish()
    assert context.document.all_objects() == []

    tool.on_press((0, 0))
    tool.on_press((10, 0))
    tool.on_press((10, 10))
    tool.on_press((0, 10))
    tool.finish()
    obj = context.document.all_objects()[0]
    assert obj.type == "measure_area"
    assert obj.measurement.value == pytest.approx(100.0)


def test_measure_perimeter_tool(context):
    tool = MeasurePerimeterTool(context)
    tool.on_press((0, 0))
    tool.on_press((10, 0))
    tool.on_press((10, 10))
    tool.on_press((0, 10))
    tool.finish()
    obj = context.document.all_objects()[0]
    assert obj.type == "measure_perimeter"
    assert obj.measurement.value == pytest.approx(40.0)


def test_measure_diameter_and_radius(context):
    d_tool = MeasureDiameterTool(context)
    d_tool.on_press((0, 0))
    d_tool.on_release((20, 0))
    r_tool = MeasureRadiusTool(context)
    r_tool.on_press((0, 0))
    r_tool.on_release((10, 0))
    diameter_obj = [o for o in context.document.all_objects() if o.type == "measure_diameter"][0]
    radius_obj = [o for o in context.document.all_objects() if o.type == "measure_radius"][0]
    assert diameter_obj.measurement.value == pytest.approx(20.0)
    assert radius_obj.measurement.value == pytest.approx(10.0)
    assert diameter_obj.text.startswith("⌀")
    assert radius_obj.text.startswith("R")


def test_measure_count_tool_numbers_sequentially(context):
    tool = MeasureCountTool(context)
    tool.on_press((0, 0))
    tool.on_press((10, 10))
    tool.on_press((20, 20))
    texts = [o.text for o in context.document.all_objects() if o.type == "measure_count"]
    assert texts == ["1", "2", "3"]
    assert MeasureCountTool.count_on_page(context.document, 0) == 3
