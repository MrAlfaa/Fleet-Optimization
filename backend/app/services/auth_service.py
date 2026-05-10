from typing import Any

from fastapi import HTTPException, status

from app.core.security import create_token_for_user, verify_password, hash_password
from app.models.user_model import safe_user_document, utc_now
from app.services.user_service import (
    create_user,
    get_raw_user_by_email,
    get_raw_user_by_id,
    get_user_collection,
)
from app.utils.object_id import validate_object_id


def token_payload(user: dict[str, Any]) -> dict[str, Any]:
    safe_user = safe_user_document(user)
    return {
        "access_token": create_token_for_user(user),
        "token_type": "bearer",
        "user": safe_user,
    }


async def register_user(data: dict[str, Any]) -> dict[str, Any]:
    user = await create_user(data)
    raw_user = await get_raw_user_by_id(user["id"])
    return token_payload(raw_user)


async def authenticate_user(email: str, password: str) -> dict[str, Any]:
    user = await get_raw_user_by_email(email)
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    await get_user_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": utc_now(), "updated_at": utc_now()}},
    )
    updated_user = await get_raw_user_by_id(str(user["_id"]))
    return token_payload(updated_user)


async def get_current_user_from_token(token: str) -> dict[str, Any]:
    from app.core.security import decode_access_token

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing token subject")
        validate_object_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc

    user = await get_raw_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    return safe_user_document(user)


async def change_password(user_id: str, old_password: str, new_password: str) -> dict[str, Any]:
    user = await get_raw_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(old_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    await get_user_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": utc_now()}},
    )
    return safe_user_document(await get_raw_user_by_id(user_id))
