from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.demand_model import DEMAND_FORECAST_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.utils.report_utils import safe_spreadsheet_value
from app.utils.sri_lanka_zones import enrich_zone_record


SECTIONS = {
    "Vehicles": (VEHICLE_COLLECTION, ["registration_number", "vehicle_code", "vehicle_type", "status", "health_status", "current_mileage", "updated_at"]),
    "Maintenance": (MAINTENANCE_COLLECTION, ["part_name", "maintenance_type", "service_date", "priority", "status", "cost"]),
    "Predictions": (PREDICTION_COLLECTION, ["vehicle_id", "part_name", "failure_probability", "risk_level", "maintenance_type_name", "predicted_rul", "rul_unit", "created_at"]),
    "Demand": (DEMAND_FORECAST_COLLECTION, ["zone_display_name", "operational_zone_id", "forecast_date", "predicted_demand", "model_type"]),
    "Routes": (ROUTE_PLAN_COLLECTION, ["route_code", "status", "total_predicted_eta_minutes", "average_delay_probability", "optimization_method", "created_at"]),
    "Deliveries": (DELIVERY_COLLECTION, ["order_code", "customer_name", "zone_id", "priority", "delivery_status", "scheduled_date"]),
    "Alerts": (ALERT_COLLECTION, ["alert_type", "severity", "title", "status", "created_at", "resolved_at"]),
}


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return database


def _date_query(start_date: datetime | None, end_date: datetime | None) -> dict[str, Any]:
    if not start_date and not end_date:
        return {}
    value: dict[str, datetime] = {}
    if start_date:
        value["$gte"] = start_date
    if end_date:
        value["$lte"] = end_date
    return {"created_at": value}


async def collect_report_data(start_date: datetime | None = None, end_date: datetime | None = None) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for name, (collection_name, fields) in SECTIONS.items():
        projection = {field: 1 for field in fields}
        if name == "Demand":
            projection["zone_id"] = 1
        rows = await _db()[collection_name].find(_date_query(start_date, end_date), projection).sort("_id", -1).limit(5000).to_list(5000)
        cleaned = []
        for row in rows:
            if name == "Demand":
                row = enrich_zone_record(row)
            cleaned.append({field: row.get(field) for field in fields})
        result[name] = cleaned
    return result


def _display(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return safe_spreadsheet_value("" if value is None else str(value))


async def build_xlsx_report(start_date: datetime | None = None, end_date: datetime | None = None) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="XLSX report dependency is unavailable") from exc
    data = await collect_report_data(start_date, end_date)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["FleetOpt AI Operational Report", datetime.now(timezone.utc).isoformat()])
    summary.append(["Section", "Records"])
    for name, rows in data.items():
        summary.append([name, len(rows)])
    for cell in summary[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="173B8F")
    for name, rows in data.items():
        sheet = workbook.create_sheet(name)
        headers = list(SECTIONS[name][1])
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="173B8F")
        for row in rows:
            sheet.append([_display(row.get(header)) for header in headers])
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(max(len(str(cell.value or "")) for cell in column) + 2, 42)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


async def build_pdf_report(start_date: datetime | None = None, end_date: datetime | None = None) -> bytes:
    data = await collect_report_data(start_date, end_date)
    lines = [
        "FleetOpt AI Operational Report",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Operational summary",
        *[f"{name}: {len(rows)} record(s)" for name, rows in data.items()],
        "",
        "Model limitations",
        "RUL estimates are planning signals, not exact service dates.",
        "Graph-enhanced demand output requires comparison with the baseline model.",
    ]
    for name, rows in data.items():
        lines.extend(["", name, " | ".join(SECTIONS[name][1])])
        for row in rows[:80]:
            lines.append(" | ".join(str(_display(row.get(field)))[:40] for field in SECTIONS[name][1]))
    return build_text_pdf(lines)


def build_text_pdf(lines: list[str]) -> bytes:
    """Build a standards-compliant, dependency-free A4 PDF with paginated text."""
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")

    pages = [lines[index:index + 48] for index in range(0, len(lines), 48)] or [[]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 3
    next_id = 4
    content_objects: list[tuple[int, bytes]] = []
    for page in pages:
        page_id, content_id = next_id, next_id + 1
        next_id += 2
        page_ids.append(page_id)
        commands = ["BT", "/F1 10 Tf", "50 790 Td", "13 TL"]
        for line in page:
            commands.append(f"({escape(str(line))}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        content_objects.append((content_id, b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"))
        objects.append(f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n".encode())
    base_objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>\nendobj\n".encode(),
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    by_id: dict[int, bytes] = {1: base_objects[0], 2: base_objects[1], 3: base_objects[2]}
    for raw in objects:
        object_id = int(raw.split(b" ", 1)[0])
        by_id[object_id] = raw
    for object_id, body in content_objects:
        by_id[object_id] = f"{object_id} 0 obj\n".encode() + body + b"\nendobj\n"
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id in range(1, max(by_id) + 1):
        offsets.append(len(output))
        output.extend(by_id[object_id])
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)
