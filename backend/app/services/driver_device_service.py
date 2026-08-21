import hashlib
import secrets
from datetime import timedelta
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.security import create_token_for_user, hash_password, verify_password
from app.models.driver_device_model import DRIVER_DEVICE_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.user_model import USER_COLLECTION, safe_user_document, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.utils.object_id import serialize_mongo_document, validate_object_id


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is unavailable")
    return db


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _driver_token(user: dict[str, Any], device: dict[str, Any]) -> str:
    return create_token_for_user(
        user,
        extra_claims={"device_id": str(device["_id"]), "credential_version": int(user.get("credential_version", 1))},
        expires_delta=timedelta(minutes=15),
    )


async def create_driver_by_admin(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    document = {
        "full_name": data["full_name"].strip(),
        "username": data["username"].strip().lower(),
        "email": data["email"].strip().lower(),
        "phone": data.get("phone"),
        "password_hash": hash_password(data["temporary_password"]),
        "role": "driver",
        "is_active": data.get("is_active", True),
        "is_verified": True,
        "credential_version": 1,
        "device_enrollment_status": "pending",
        "temporary_password_created_at": now,
        "device_reset_at": None,
        "device_reset_by": None,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    try:
        result = await _db()[USER_COLLECTION].insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver username or email already exists") from exc
    return safe_user_document(await _db()[USER_COLLECTION].find_one({"_id": result.inserted_id}))


async def update_driver_by_admin(driver_id: str, data: dict[str, Any]) -> dict[str, Any]:
    object_id = validate_object_id(driver_id)
    update = {key: value for key, value in data.items() if value is not None}
    if "username" in update:
        update["username"] = update["username"].strip().lower()
    if "email" in update:
        update["email"] = update["email"].strip().lower()
    update["updated_at"] = utc_now()
    try:
        result = await _db()[USER_COLLECTION].update_one({"_id": object_id, "role": "driver"}, {"$set": update})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver username or email already exists") from exc
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return safe_user_document(await _db()[USER_COLLECTION].find_one({"_id": object_id}))


async def list_drivers_for_admin() -> list[dict[str, Any]]:
    users = await _db()[USER_COLLECTION].find({"role": "driver"}).sort("username", 1).to_list(length=500)
    result = []
    for user in users:
        device = await _db()[DRIVER_DEVICE_COLLECTION].find_one({"user_id": user["_id"], "status": "active"})
        route = await _db()[ROUTE_PLAN_COLLECTION].find_one({"driver_id": user["_id"], "status": {"$in": ["dispatched", "in_progress"]}})
        vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": route.get("vehicle_id")}) if route and route.get("vehicle_id") else None
        item = safe_user_document(user)
        item["device"] = serialize_mongo_document(device) if device else None
        if item["device"]:
            item["device"].pop("device_secret_hash", None)
            item["device"].pop("installation_id_hash", None)
        item["active_route"] = {"id": str(route["_id"]), "route_code": route.get("route_code")} if route else None
        item["assigned_vehicle"] = {"id": str(vehicle["_id"]), "registration_number": vehicle.get("registration_number")} if vehicle else None
        result.append(item)
    return result


async def validate_driver_for_assignment(driver_id: str, route_id: str | None = None) -> dict[str, Any]:
    try:
        object_id = validate_object_id(driver_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver ID") from exc
    user = await _db()[USER_COLLECTION].find_one({"_id": object_id, "role": "driver"})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected driver account is inactive")
    device = await _db()[DRIVER_DEVICE_COLLECTION].find_one({"user_id": object_id, "status": "active"})
    if user.get("device_enrollment_status") != "enrolled" or device is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected driver has not enrolled an active mobile device")
    route_query: dict[str, Any] = {"driver_id": object_id, "status": {"$in": ["dispatched", "in_progress"]}}
    if route_id:
        try:
            route_query["_id"] = {"$ne": validate_object_id(route_id)}
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    conflict = await _db()[ROUTE_PLAN_COLLECTION].find_one(route_query)
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Driver already has active route {conflict.get('route_code', str(conflict['_id']))}",
        )
    return {"driver": safe_user_document(user), "device": serialize_mongo_document(device)}


async def reset_driver_device(driver_id: str, temporary_password: str, admin_user: dict[str, Any]) -> dict[str, Any]:
    object_id = validate_object_id(driver_id)
    user = await _db()[USER_COLLECTION].find_one({"_id": object_id, "role": "driver"})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    now = utc_now()
    await _db()[DRIVER_DEVICE_COLLECTION].update_many(
        {"user_id": object_id, "status": "active"},
        {"$set": {"status": "revoked", "revoked_at": now, "revoked_by": validate_object_id(admin_user["id"])}, "$unset": {"active_slot": ""}},
    )
    await _db()[USER_COLLECTION].update_one(
        {"_id": object_id},
        {"$set": {
            "password_hash": hash_password(temporary_password),
            "credential_version": int(user.get("credential_version", 1)) + 1,
            "device_enrollment_status": "pending",
            "temporary_password_created_at": now,
            "device_reset_at": now,
            "device_reset_by": validate_object_id(admin_user["id"]),
            "updated_at": now,
        }},
    )
    return safe_user_document(await _db()[USER_COLLECTION].find_one({"_id": object_id}))


async def enroll_driver_device(data: dict[str, Any]) -> dict[str, Any]:
    user = await _db()[USER_COLLECTION].find_one({"username": data["username"].strip().lower(), "role": "driver"})
    if user is None or not verify_password(data["temporary_password"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or temporary password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver account is inactive")
    if user.get("device_enrollment_status") == "enrolled" or await _db()[DRIVER_DEVICE_COLLECTION].find_one({"user_id": user["_id"], "status": "active"}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A device is already registered. Ask the fleet administrator to reset it")
    secret = secrets.token_urlsafe(48)
    now = utc_now()
    device = {
        "user_id": user["_id"],
        "installation_id_hash": _digest(data["installation_id"]),
        "device_secret_hash": _digest(secret),
        "device_name": data["device_name"],
        "device_model": data["device_model"],
        "android_version": data["android_version"],
        "app_version": data["app_version"],
        "credential_version": int(user.get("credential_version", 1)),
        "biometric_enabled": False,
        "status": "active",
        "active_slot": "active",
        "enrolled_at": now,
        "last_seen_at": now,
        "revoked_at": None,
    }
    result = await _db()[DRIVER_DEVICE_COLLECTION].insert_one(device)
    device["_id"] = result.inserted_id
    await _db()[USER_COLLECTION].update_one({"_id": user["_id"]}, {"$set": {"device_enrollment_status": "enrolled", "updated_at": now}})
    return {"access_token": _driver_token(user, device), "token_type": "bearer", "device_secret": secret, "device_id": str(device["_id"]), "user": safe_user_document(user)}


async def create_driver_device_session(data: dict[str, Any]) -> dict[str, Any]:
    device = await _db()[DRIVER_DEVICE_COLLECTION].find_one({
        "installation_id_hash": _digest(data["installation_id"]),
        "device_secret_hash": _digest(data["device_secret"]),
        "status": "active",
    })
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device registration is invalid or revoked")
    user = await _db()[USER_COLLECTION].find_one({"_id": device["user_id"], "role": "driver", "is_active": True})
    if user is None or int(user.get("credential_version", 1)) != int(device.get("credential_version", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device registration has been reset")
    await _db()[DRIVER_DEVICE_COLLECTION].update_one({"_id": device["_id"]}, {"$set": {"last_seen_at": utc_now()}})
    return {"access_token": _driver_token(user, device), "token_type": "bearer", "user": safe_user_document(user)}


async def validate_driver_device_claims(user: dict[str, Any], payload: dict[str, Any]) -> None:
    device_id = payload.get("device_id")
    if not device_id or int(payload.get("credential_version", 0)) != int(user.get("credential_version", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Driver device session is invalid")
    device = await _db()[DRIVER_DEVICE_COLLECTION].find_one({"_id": validate_object_id(device_id), "user_id": user["_id"], "status": "active"})
    if device is None or int(device.get("credential_version", 0)) != int(user.get("credential_version", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Driver device has been revoked")


async def revoke_current_device(current_user: dict[str, Any], device_id: str) -> None:
    await _db()[DRIVER_DEVICE_COLLECTION].update_one(
        {"_id": validate_object_id(device_id), "user_id": validate_object_id(current_user["id"])},
        {"$set": {"status": "revoked", "revoked_at": utc_now()}, "$unset": {"active_slot": ""}},
    )


async def update_biometric_indicator(current_user: dict[str, Any], device_id: str, enabled: bool) -> None:
    await _db()[DRIVER_DEVICE_COLLECTION].update_one(
        {"_id": validate_object_id(device_id), "user_id": validate_object_id(current_user["id"]), "status": "active"},
        {"$set": {"biometric_enabled": enabled, "last_seen_at": utc_now()}},
    )
