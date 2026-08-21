import unittest

from pydantic import ValidationError

from app.schemas.vehicle_part_schema import VehiclePartCreate


class EvPartCatalogTests(unittest.TestCase):
    def test_catalog_exposes_ten_ml_aligned_default_parts(self):
        from app.models.vehicle_part_model import get_ev_part_catalog

        catalog = get_ev_part_catalog()

        self.assertEqual(len(catalog), 10)
        self.assertEqual(catalog[0]["key"], "battery_pack")
        self.assertEqual(catalog[0]["name"], "Battery Pack")
        self.assertTrue(all(item["ml_supported"] for item in catalog))
        self.assertEqual(
            {(item["name"], item["category"]) for item in catalog},
            set(__import__("app.models.vehicle_part_model", fromlist=["DEFAULT_EV_PARTS"]).DEFAULT_EV_PARTS),
        )

    def test_manual_part_status_uses_backend_supported_values(self):
        payload = VehiclePartCreate(
            vehicle_id="507f1f77bcf86cd799439011",
            part_name="Battery Pack",
            part_category="battery",
            status="warning",
        )

        self.assertEqual(payload.status, "warning")

    def test_rejects_status_not_supported_by_vehicle_part_model(self):
        with self.assertRaises(ValidationError):
            VehiclePartCreate(
                part_name="Battery Pack",
                part_category="battery",
                status="attention_required",
            )


if __name__ == "__main__":
    unittest.main()
