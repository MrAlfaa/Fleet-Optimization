from app.services.demo_reset_service import OPERATIONAL_COLLECTIONS, retained_user_filter


def test_reset_covers_all_operational_collections() -> None:
    expected = {
        "vehicles", "vehicle_parts", "maintenance_records", "maintenance_predictions", "alerts",
        "demand_zones", "demand_forecasts", "fleet_planning_recommendations", "demand_model_runs",
        "delivery_orders", "delivery_attempts", "route_plans", "route_segments", "route_model_runs",
        "driver_devices", "driver_issue_reports", "driver_trip_sessions", "driver_locations", "trip_events",
    }
    assert set(OPERATIONAL_COLLECTIONS) == expected


def test_reset_preserves_only_the_selected_admin_email() -> None:
    assert retained_user_filter("Admin@Fleet.Local") == {"email": {"$ne": "admin@fleet.local"}}

