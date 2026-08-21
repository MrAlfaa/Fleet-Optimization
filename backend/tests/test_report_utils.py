from app.utils.report_utils import safe_spreadsheet_value
from app.services.report_service import build_text_pdf


def test_prevents_spreadsheet_formula_injection():
    for value in ["=SUM(A1:A2)", "+cmd", "-2+3", "@payload"]:
        assert safe_spreadsheet_value(value).startswith("'")


def test_preserves_normal_values():
    assert safe_spreadsheet_value("WP CAA-1234") == "WP CAA-1234"
    assert safe_spreadsheet_value(42) == 42


def test_builds_valid_pdf_document():
    result = build_text_pdf(["FleetOpt AI", "Operational report"])
    assert result.startswith(b"%PDF-1.4")
    assert result.endswith(b"%%EOF")
