import unittest

from app.services.fleet_intelligence_service import classify_vehicle_readiness


class VehicleReadinessClassificationTests(unittest.TestCase):
    def test_critical_health_blocks_vehicle(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "critical"},
            {"risk_level": "low"},
        )
        self.assertFalse(result["eligible"])
        self.assertIn("Vehicle health status is critical", result["blocking_reasons"])

    def test_non_operational_status_blocks_vehicle(self):
        result = classify_vehicle_readiness(
            {"status": "under_maintenance", "health_status": "healthy"},
            {"risk_level": "low"},
        )
        self.assertFalse(result["eligible"])
        self.assertIn("Vehicle status is under maintenance", result["blocking_reasons"])

    def test_critical_prediction_blocks_healthy_vehicle(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "healthy"},
            {"risk_level": "critical"},
        )
        self.assertFalse(result["eligible"])
        self.assertIn("Latest predictive maintenance risk is critical", result["blocking_reasons"])

    def test_high_prediction_warns_without_blocking(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "healthy"},
            {"risk_level": "high"},
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["readiness_status"], "warning")
        self.assertIn("Latest predictive maintenance risk is high", result["warnings"])

    def test_cleared_critical_prediction_does_not_block(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "healthy"},
            {"risk_level": "critical", "dispatch_hold": False, "review_status": "cleared"},
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["readiness_status"], "warning")

    def test_pending_review_hold_blocks(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "healthy"},
            {"risk_level": "critical", "dispatch_hold": True, "review_status": "pending"},
        )
        self.assertFalse(result["eligible"])
        self.assertIn("Engineering review is pending", result["blocking_reasons"])

    def test_missing_prediction_warns_without_blocking(self):
        result = classify_vehicle_readiness(
            {"status": "active", "health_status": "healthy"},
            None,
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["readiness_status"], "warning")
        self.assertIn("No recent predictive maintenance result is available", result["warnings"])


if __name__ == "__main__":
    unittest.main()
