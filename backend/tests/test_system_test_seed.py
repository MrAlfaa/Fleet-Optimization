from scripts.seed_system_test_data import DELIVERY_SCENARIOS, PREDICTION_SCENARIOS, VEHICLE_SCENARIOS


def test_system_seed_has_enough_vehicle_and_prediction_scenarios():
    assert len(VEHICLE_SCENARIOS) >= 8
    assert len(PREDICTION_SCENARIOS) == len(VEHICLE_SCENARIOS)


def test_system_seed_has_enough_unassigned_sri_lankan_deliveries():
    assert len(DELIVERY_SCENARIOS) >= 20
    assert all(row["zone_id"].startswith("LK_") for row in DELIVERY_SCENARIOS)
    assert all("assigned_driver_id" not in row for row in DELIVERY_SCENARIOS)


def test_system_seed_contains_no_user_or_driver_credentials():
    combined = [*VEHICLE_SCENARIOS, *DELIVERY_SCENARIOS, *PREDICTION_SCENARIOS]
    forbidden = {"email", "username", "password", "temporary_password", "driver_id", "assigned_driver_id"}
    assert all(forbidden.isdisjoint(row) for row in combined)
