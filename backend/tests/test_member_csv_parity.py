from app.load_optimization.csv_parity import project_member_csv_row
from app.schemas.delivery_schema import DeliveryOrderCreate


def test_member_csv_row_projects_to_main_parcel_contract():
    projected = project_member_csv_row({
        "parcel_id": "D1-05-036", "delivery_date": "2026-01-05", "latitude": "6.871458",
        "longitude": "79.890147", "weight_kg": "7.66", "volume_m3": "0.05980578",
        "length_cm": "37.86", "width_cm": "39.65", "height_cm": "39.84",
        "time_window_start": "10:30", "time_window_end": "14:30", "fragile": "false",
        "stackable": "true", "max_stack_weight_kg": "52.4", "loading_orientation_fixed": "false",
        "hazardous": "false", "hazmat_class": "", "requires_refrigeration": "false",
        "temp_min_celsius": "", "temp_max_celsius": "", "two_person_lift": "false",
        "do_not_tilt": "false", "priority_level": "express", "service_type": "door_to_door",
    })

    validated = DeliveryOrderCreate.model_validate(projected)

    assert validated.order_code == "D1-05-036"
    assert validated.delivery_period == "first_half"
    assert validated.priority == "high"
    assert validated.load_profile is not None
