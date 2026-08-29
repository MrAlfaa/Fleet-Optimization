from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.load_optimization.csv_parity import project_member_csv_row
from app.schemas.delivery_schema import DeliveryOrderCreate


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the supplied member CSV against the main Parcel Gallery contract")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    valid = 0
    errors: list[dict[str, str | int]] = []
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                DeliveryOrderCreate.model_validate(project_member_csv_row(row))
                valid += 1
            except Exception as exc:
                errors.append({"line": line_number, "parcel_id": row.get("parcel_id", ""), "error": str(exc)})
    print(json.dumps({"rows_valid": valid, "rows_invalid": len(errors), "errors": errors[:20]}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
