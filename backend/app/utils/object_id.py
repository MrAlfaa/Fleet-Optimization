from typing import Any

from bson import ObjectId


def serialize_object_id(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def serialize_mongo_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None

    serialized: dict[str, Any] = {}
    for key, value in document.items():
        if key == "_id":
            serialized["id"] = serialize_object_id(value)
        elif isinstance(value, ObjectId):
            serialized[key] = serialize_object_id(value)
        elif isinstance(value, list):
            serialized[key] = [
                serialize_object_id(item) if isinstance(item, ObjectId) else item for item in value
            ]
        elif isinstance(value, dict):
            serialized[key] = {
                nested_key: serialize_object_id(nested_value) if isinstance(nested_value, ObjectId) else nested_value
                for nested_key, nested_value in value.items()
            }
        else:
            serialized[key] = value
    return serialized


def serialize_mongo_list(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_mongo_document(document) for document in documents if document is not None]


def validate_object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return ObjectId(value)
