import unittest

from bson import ObjectId
from fastapi.encoders import jsonable_encoder

from app.utils.sri_lanka_zones import (
    SRI_LANKA_ZONE_ALIASES,
    enrich_zone_record,
    operational_zone_id,
    source_zone_id,
)


class SriLankaZoneMappingTests(unittest.TestCase):
    def test_all_fifteen_colombo_zones_are_native_operational_zones(self):
        self.assertEqual(len(SRI_LANKA_ZONE_ALIASES), 15)
        self.assertEqual(operational_zone_id("SP_sao_paulo"), "LK_colombo_central")
        self.assertEqual(source_zone_id("LK_colombo_central"), "LK_colombo_central")

    def test_enrichment_normalizes_legacy_input_without_exposing_foreign_source(self):
        enriched = enrich_zone_record(
            {
                "zone_id": "SP_guarulhos",
                "zone_lat": -23.44,
                "zone_lng": -46.51,
                "predicted_demand": 42,
            }
        )

        self.assertEqual(enriched["source_zone_id"], "LK_nugegoda")
        self.assertEqual(enriched["operational_zone_id"], "LK_nugegoda")
        self.assertEqual(enriched["zone_id"], "LK_nugegoda")
        self.assertEqual(enriched["zone_display_name"], "Nugegoda")
        self.assertAlmostEqual(enriched["zone_lat"], 6.8649)
        self.assertAlmostEqual(enriched["zone_lng"], 79.8997)
        self.assertEqual(enriched["data_context"], "colombo_operational_forecast")

    def test_unknown_operational_zone_is_preserved(self):
        enriched = enrich_zone_record({"zone_id": "LK_badulla", "predicted_demand": 12})

        self.assertEqual(enriched["source_zone_id"], "LK_badulla")
        self.assertEqual(enriched["operational_zone_id"], "LK_badulla")
        self.assertEqual(enriched["zone_display_name"], "Badulla")
        self.assertEqual(source_zone_id("LK_badulla"), "LK_badulla")

    def test_enrichment_serializes_mongodb_object_ids_for_api_responses(self):
        document_id = ObjectId()
        model_run_id = ObjectId()

        enriched = enrich_zone_record(
            {
                "_id": document_id,
                "model_run_id": model_run_id,
                "zone_id": "SP_sao_paulo",
                "predicted_demand": 42,
            }
        )

        self.assertEqual(enriched["id"], str(document_id))
        self.assertEqual(enriched["model_run_id"], str(model_run_id))
        jsonable_encoder(enriched)


if __name__ == "__main__":
    unittest.main()
