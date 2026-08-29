import math
import re
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.database import get_database
from app.core.security import hash_password
from app.core.permissions import permission_overrides_from_selection
from app.models.user_model import USER_COLLECTION, build_user_document, safe_user_document, utc_now
from app.utils.object_id import serialize_mongo_list, validate_object_id


def get_user_collection():
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not configured or connected",
        )
    return db[USER_COLLECTION]


def assert_account_update_allowed(current_user: dict[str, Any], update_data: dict[str, Any]) -> None:
    protected_fields = {"role", "is_active", "permission_overrides"}
    if current_user.get("role") == "admin" and protected_fields.intersection(update_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrator access and account status are protected",
        )


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc

    user = await get_user_collection().find_one({"_id": object_id})
    return safe_user_document(user)


async def get_raw_user_by_id(user_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc
    return await get_user_collection().find_one({"_id": object_id})


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    user = await get_user_collection().find_one({"email": email.lower()})
    return safe_user_document(user)


async def get_raw_user_by_email(email: str) -> dict[str, Any] | None:
    return await get_user_collection().find_one({"email": email.lower()})


async def list_users(
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query: dict[str, Any] = {}

    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active
    if search:
        search_regex = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"full_name": search_regex},
            {"email": search_regex},
            {"phone": search_regex},
        ]

    collection = get_user_collection()
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    items = [safe_user_document(item) for item in await cursor.to_list(length=limit)]

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": math.ceil(total / limit) if total else 0,
    }


async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    user_document = build_user_document(data, hash_password(data["password"]))

    try:
        result = await get_user_collection().insert_one(user_document)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database operation failed") from exc

    created = await get_user_collection().find_one({"_id": result.inserted_id})
    return safe_user_document(created)


async def update_user(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id: ObjectId = validate_object_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc

    current_user = await get_user_collection().find_one({"_id": object_id})
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = {key: value for key, value in data.items() if value is not None}
    assert_account_update_allowed(current_user, update_data)
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()
    update_data["updated_at"] = utc_now()

    try:
        result = await get_user_collection().update_one({"_id": object_id}, {"$set": update_data})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await get_user_collection().find_one({"_id": object_id})
    return safe_user_document(updated)


async def deactivate_user(user_id: str) -> dict[str, Any]:
    return await update_user(user_id, {"is_active": False})


async def activate_user(user_id: str) -> dict[str, Any]:
    return await update_user(user_id, {"is_active": True})


async def update_user_permissions(user_id: str, permissions: list[str]) -> dict[str, Any]:
    raw_user = await get_raw_user_by_id(user_id)
    if raw_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if raw_user.get("role") == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator permissions cannot be reduced")
    return await update_user(
        user_id,
        {"permission_overrides": permission_overrides_from_selection(raw_user["role"], permissions)},
    )
