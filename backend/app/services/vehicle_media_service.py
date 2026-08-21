import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.database import get_database
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, safe_vehicle_document
from app.utils.object_id import validate_object_id


MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
VEHICLE_MEDIA_ROOT = MEDIA_ROOT / "vehicles"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not configured or connected",
        )
    return database


def _vehicle_object_id(vehicle_id: str):
    try:
        return validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc


async def validate_vehicle_image(upload: UploadFile) -> tuple[bytes, str]:
    content_type = upload.content_type or ""
    suffix = ALLOWED_IMAGE_TYPES.get(content_type)
    filename_suffix = Path(upload.filename or "").suffix.lower()
    if suffix is None or filename_suffix not in {suffix, ".jpeg" if suffix == ".jpg" else suffix}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Vehicle image must be JPEG, PNG, or WebP",
        )

    content = await upload.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle image is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Vehicle image must not exceed 5 MB",
        )
    return content, suffix


def _managed_vehicle_path(image_url: str | None) -> Path | None:
    prefix = "/media/vehicles/"
    if not image_url or not image_url.startswith(prefix):
        return None
    filename = image_url.removeprefix(prefix)
    if not filename or Path(filename).name != filename:
        return None
    candidate = (VEHICLE_MEDIA_ROOT / filename).resolve()
    if candidate.parent != VEHICLE_MEDIA_ROOT.resolve():
        return None
    return candidate


async def _remove_managed_image(image_url: str | None) -> None:
    path = _managed_vehicle_path(image_url)
    if path is not None and path.exists():
        await asyncio.to_thread(path.unlink, missing_ok=True)


async def save_vehicle_image(vehicle_id: str, upload: UploadFile) -> dict[str, Any]:
    object_id = _vehicle_object_id(vehicle_id)
    collection = _db()[VEHICLE_COLLECTION]
    vehicle = await collection.find_one({"_id": object_id})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    content, suffix = await validate_vehicle_image(upload)
    VEHICLE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    target = (VEHICLE_MEDIA_ROOT / filename).resolve()
    if target.parent != VEHICLE_MEDIA_ROOT.resolve():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid media target")

    await asyncio.to_thread(target.write_bytes, content)
    image_url = f"/media/vehicles/{filename}"
    result = await collection.find_one_and_update(
        {"_id": object_id},
        {"$set": {"image_url": image_url, "updated_at": utc_now()}},
        return_document=True,
    )
    if result is None:
        await asyncio.to_thread(target.unlink, missing_ok=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    await _remove_managed_image(vehicle.get("image_url"))
    return safe_vehicle_document(result)


async def delete_vehicle_image(vehicle_id: str) -> dict[str, Any]:
    object_id = _vehicle_object_id(vehicle_id)
    collection = _db()[VEHICLE_COLLECTION]
    vehicle = await collection.find_one({"_id": object_id})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    result = await collection.find_one_and_update(
        {"_id": object_id},
        {"$set": {"image_url": None, "updated_at": utc_now()}},
        return_document=True,
    )
    await _remove_managed_image(vehicle.get("image_url"))
    return safe_vehicle_document(result)
