from bson import ObjectId

from app.services.driver_device_service import _bulk_device_revocation_update, _revoked_device_slot


def test_revoked_device_slots_are_unique_per_device():
    first = ObjectId()
    second = ObjectId()

    assert _revoked_device_slot(first) == f"revoked:{first}"
    assert _revoked_device_slot(first) != _revoked_device_slot(second)


def test_bulk_revocation_assigns_a_unique_slot_from_each_document_id():
    update = _bulk_device_revocation_update("now", ObjectId())

    assert update[0]["$set"]["active_slot"] == {
        "$concat": ["revoked:", {"$toString": "$_id"}],
    }
