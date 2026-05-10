from datetime import datetime, timedelta, timezone
from typing import Any
import math
import random

import numpy as np
import pandas as pd
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.predictive_model import PREDICTION_COLLECTION, build_prediction_document, safe_prediction_document
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.models.vehicle_part_model import VEHICLE_PART_COLLECTION
from app.services.alert_service import create_alert
from app.services.ml_model_loader_service import (
    ModelUnavailableError,
    get_artifact_metadata,
    get_feature_columns_from_file,
    get_predictive_maintenance_bundle,
)
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination
from app.utils.risk_utils import (
    calculate_next_maintenance_date,
    map_maintenance_type_to_part,
    normalize_probability,
    recommended_action_from_risk,
    risk_level_from_probability,
)


PREDICTIVE_ALLOWED_ROLES = ["admin", "fleet_manager", "maintenance_manager"]


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def _object_id(value: str, field_name: str = "id") -> ObjectId:
    try:
        return validate_object_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}") from exc


def _to_plain_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        return None if math.isnan(value) else value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, dict):
        return {str(key): _to_plain_value(inner_value) for key, inner_value in value.items()}
    if isinstance(value, list):
        return [_to_plain_value(item) for item in value]
    return value


def _sensor_dict(sensor_data: Any) -> dict[str, Any]:
    if hasattr(sensor_data, "model_dump"):
        return sensor_data.model_dump(exclude_none=True)
    return dict(sensor_data or {})


def _class_one_probability(model: Any, frame: pd.DataFrame, fallback_prediction: int) -> float:
    if not hasattr(model, "predict_proba"):
        return normalize_probability(fallback_prediction)

    probabilities = model.predict_proba(frame)[0]
    classes = list(getattr(model, "classes_", []))
    if 1 in classes:
        return normalize_probability(probabilities[classes.index(1)])
    if len(probabilities) > 1:
        return normalize_probability(probabilities[1])
    return normalize_probability(probabilities[0])


def _decode_maintenance_type(prediction: Any, mapping: Any) -> tuple[int | None, str | None]:
    maintenance_type_id: int | None = None
    if isinstance(prediction, (np.integer, int)):
        maintenance_type_id = int(prediction)
    elif isinstance(prediction, str) and prediction.isdigit():
        maintenance_type_id = int(prediction)

    if isinstance(mapping, dict):
        for key in (prediction, str(prediction), maintenance_type_id, str(maintenance_type_id)):
            if key in mapping:
                return maintenance_type_id, str(mapping[key])
        reverse_mapping = {str(value): str(key) for key, value in mapping.items()}
        if str(prediction) in reverse_mapping:
            return maintenance_type_id, str(prediction)

    if isinstance(mapping, list) and maintenance_type_id is not None and 0 <= maintenance_type_id < len(mapping):
        return maintenance_type_id, str(mapping[maintenance_type_id])

    if prediction is None:
        return maintenance_type_id, None
    return maintenance_type_id, str(prediction)


def _prediction_health_status(risk_level: str) -> str:
    return "critical" if risk_level == "critical" else "warning" if risk_level in {"medium", "high"} else "healthy"


def _prediction_part_status(risk_level: str) -> str:
    return "critical" if risk_level == "critical" else "warning" if risk_level in {"medium", "high"} else "healthy"


async def _get_vehicle(vehicle_id: str) -> dict[str, Any]:
    vehicle_oid = _object_id(vehicle_id, "vehicle_id")
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_oid})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


async def _get_part(part_id: str | None, vehicle_id: ObjectId, maintenance_type_name: str | None) -> dict[str, Any] | None:
    collection = _db()[VEHICLE_PART_COLLECTION]

    if part_id:
        part_oid = _object_id(part_id, "part_id")
        part = await collection.find_one({"_id": part_oid, "vehicle_id": vehicle_id})
        if part is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle part not found")
        return part

    mapped_part_name = map_maintenance_type_to_part(maintenance_type_name)
    if mapped_part_name is None:
        return None

    return await collection.find_one({"vehicle_id": vehicle_id, "part_name": mapped_part_name})


async def get_model_status(load_model: bool = True) -> dict[str, Any]:
    return get_artifact_metadata(load=load_model)


def prepare_model_input(sensor_data: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    bundle = get_predictive_maintenance_bundle()
    feature_columns = bundle.get("feature_columns") or get_feature_columns_from_file()
    if not feature_columns:
        raise ModelUnavailableError(
            "Predictive maintenance model feature metadata is unavailable",
            {"loaded": True, "required_features_count": 0},
        )

    values = _sensor_dict(sensor_data)
    now = datetime.now(timezone.utc)
    values.setdefault("hour", now.hour)
    values.setdefault("day_of_week", now.weekday())
    values.setdefault("month", now.month)
    values.setdefault("is_weekend", 1 if now.weekday() >= 5 else 0)

    ordered_values = {feature: values.get(feature, np.nan) for feature in feature_columns}
    frame = pd.DataFrame([ordered_values], columns=feature_columns)
    return frame, _to_plain_value(ordered_values)


async def save_prediction(prediction_data: dict[str, Any]) -> dict[str, Any]:
    document = build_prediction_document(prediction_data)
    result = await _db()[PREDICTION_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return safe_prediction_document(document) or {}


async def refresh_vehicle_risk_from_prediction(vehicle_id: ObjectId, prediction: dict[str, Any]) -> None:
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": vehicle_id},
        {
            "$set": {
                "health_status": _prediction_health_status(prediction["risk_level"]),
                "updated_at": utc_now(),
            }
        },
    )


async def update_part_risk_from_prediction(
    vehicle_id: ObjectId,
    part: dict[str, Any] | None,
    prediction: dict[str, Any],
) -> None:
    if part is None:
        return

    await _db()[VEHICLE_PART_COLLECTION].update_one(
        {"_id": part["_id"], "vehicle_id": vehicle_id},
        {
            "$set": {
                "risk_score": round(prediction["failure_probability"] * 100, 2),
                "risk_level": prediction["risk_level"],
                "status": _prediction_part_status(prediction["risk_level"]),
                "next_predicted_maintenance_date": prediction.get("next_maintenance_date"),
                "updated_at": utc_now(),
            }
        },
    )


async def create_alert_for_high_risk_prediction(
    vehicle: dict[str, Any],
    part: dict[str, Any] | None,
    prediction: dict[str, Any],
) -> bool:
    if prediction["risk_level"] not in {"high", "critical"}:
        return False

    db = _db()
    start_of_day = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    duplicate_query: dict[str, Any] = {
        "alert_type": "maintenance",
        "status": "active",
        "linked_vehicle_id": vehicle["_id"],
        "created_at": {"$gte": start_of_day},
    }
    if part is not None:
        duplicate_query["linked_part_id"] = part["_id"]

    existing_alert = await db[ALERT_COLLECTION].find_one(duplicate_query)
    if existing_alert is not None:
        return False

    severity = "critical" if prediction["risk_level"] == "critical" else "high"
    part_text = f" for {part['part_name']}" if part else ""
    maintenance_type = prediction.get("maintenance_type_name") or "Unknown"
    await create_alert(
        {
            "alert_type": "maintenance",
            "severity": severity,
            "title": f"{severity.title()} maintenance risk detected",
            "message": (
                f"Vehicle {vehicle.get('vehicle_code', str(vehicle['_id']))}{part_text} has "
                f"{prediction['failure_probability']:.0%} failure probability ({prediction['risk_level']}). "
                f"Maintenance type: {maintenance_type}. {prediction['recommended_action']}"
            ),
            "linked_vehicle_id": str(vehicle["_id"]),
            "linked_part_id": str(part["_id"]) if part else None,
            "created_by_system": True,
        }
    )
    return True


async def predict_vehicle_maintenance(request_data: Any, current_user: dict[str, Any]) -> dict[str, Any]:
    vehicle = await _get_vehicle(request_data.vehicle_id)
    frame, input_features = prepare_model_input(request_data.sensor_data)
    bundle = get_predictive_maintenance_bundle()

    failure_model = bundle.get("failure_model")
    if failure_model is None:
        raise ModelUnavailableError("Predictive maintenance failure model is unavailable", {"loaded": True})

    try:
        failure_prediction = int(failure_model.predict(frame)[0])
        failure_probability = _class_one_probability(failure_model, frame, failure_prediction)
    except Exception as exc:
        raise ModelUnavailableError(
            "Predictive maintenance model inference failed",
            {
                "loaded": True,
                "error": str(exc),
                "hint": "Use the artifact-compatible backend environment. The current artifact was trained with scikit-learn 1.6.1.",
            },
        ) from exc
    risk_level = risk_level_from_probability(failure_probability)

    maintenance_type_id: int | None = None
    maintenance_type_name: str | None = None
    maintenance_type_model = bundle.get("maintenance_type_model")
    if maintenance_type_model is not None:
        try:
            maintenance_prediction = maintenance_type_model.predict(frame)[0]
            mapping = bundle.get("maintenance_type_mapping") or bundle.get("maintenance_type_labels")
            maintenance_type_id, maintenance_type_name = _decode_maintenance_type(maintenance_prediction, mapping)
        except Exception:
            maintenance_type_name = "Unknown"

    predicted_rul: float | None = None
    next_maintenance_date = None
    rul_unit = bundle.get("rul_unit") or "hours"
    rul_model = bundle.get("rul_model")
    if rul_model is not None:
        try:
            rul_value = float(rul_model.predict(frame)[0])
            if math.isfinite(rul_value):
                predicted_rul = max(rul_value, 0)
                next_maintenance_date = calculate_next_maintenance_date(utc_now(), predicted_rul, rul_unit)
        except Exception:
            predicted_rul = None
            next_maintenance_date = None

    part = await _get_part(request_data.part_id, vehicle["_id"], maintenance_type_name)
    recommended_action = recommended_action_from_risk(risk_level, maintenance_type_name)
    prediction_payload = {
        "vehicle_id": vehicle["_id"],
        "part_id": part["_id"] if part else None,
        "part_name": part.get("part_name") if part else map_maintenance_type_to_part(maintenance_type_name),
        "input_source": request_data.input_source,
        "input_features": input_features,
        "failure_prediction": failure_prediction,
        "failure_probability": failure_probability,
        "risk_level": risk_level,
        "maintenance_type_id": maintenance_type_id,
        "maintenance_type_name": maintenance_type_name,
        "predicted_rul": predicted_rul,
        "rul_unit": rul_unit if predicted_rul is not None else None,
        "next_maintenance_date": next_maintenance_date,
        "recommended_action": recommended_action,
        "model_version": bundle.get("model_version") or bundle.get("version"),
        "model_metrics_snapshot": bundle.get("metrics"),
        "created_by": _object_id(current_user["id"], "current_user.id") if current_user.get("id") else None,
    }

    saved_prediction = await save_prediction(prediction_payload)
    await refresh_vehicle_risk_from_prediction(vehicle["_id"], prediction_payload)
    await update_part_risk_from_prediction(vehicle["_id"], part, prediction_payload)
    alert_created = await create_alert_for_high_risk_prediction(vehicle, part, prediction_payload)

    return {
        "vehicle_id": str(vehicle["_id"]),
        "failure_prediction": failure_prediction,
        "failure_probability": failure_probability,
        "risk_level": risk_level,
        "maintenance_type_id": maintenance_type_id,
        "maintenance_type_name": maintenance_type_name,
        "predicted_rul": predicted_rul,
        "rul_unit": prediction_payload["rul_unit"],
        "next_maintenance_date": next_maintenance_date.isoformat() if next_maintenance_date else None,
        "recommended_action": recommended_action,
        "alert_created": alert_created,
        "prediction_id": saved_prediction["id"],
        "part_id": saved_prediction.get("part_id"),
        "part_name": saved_prediction.get("part_name"),
    }


async def predict_batch_maintenance(batch_data: Any, current_user: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    requests = getattr(batch_data, "requests", None) or getattr(batch_data, "items", [])

    for index, item in enumerate(requests):
        try:
            results.append(await predict_vehicle_maintenance(item, current_user))
        except HTTPException as exc:
            errors.append({"index": index, "message": str(exc.detail), "status_code": exc.status_code})
        except ModelUnavailableError as exc:
            errors.append({"index": index, "message": exc.message, "data": exc.data})
        except Exception as exc:
            errors.append({"index": index, "message": f"Prediction failed: {exc}"})

    return {
        "total": len(requests),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


async def get_prediction_by_id(prediction_id: str) -> dict[str, Any]:
    prediction = await _db()[PREDICTION_COLLECTION].find_one({"_id": _object_id(prediction_id, "prediction_id")})
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return safe_prediction_document(prediction) or {}


async def list_predictions(
    vehicle_id: str | None = None,
    risk_level: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if vehicle_id:
        query["vehicle_id"] = _object_id(vehicle_id, "vehicle_id")
    if risk_level:
        query["risk_level"] = risk_level

    collection = _db()[PREDICTION_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit)
    items = serialize_mongo_list(await cursor.to_list(length=limit))
    return build_pagination_response(items, total, page, limit)


async def get_vehicle_prediction_history(vehicle_id: str, limit: int = 20) -> list[dict[str, Any]]:
    vehicle_oid = _object_id(vehicle_id, "vehicle_id")
    limit = min(max(limit, 1), 100)
    cursor = _db()[PREDICTION_COLLECTION].find({"vehicle_id": vehicle_oid}).sort("created_at", -1).limit(limit)
    return serialize_mongo_list(await cursor.to_list(length=limit))


async def get_fleet_risk_summary() -> dict[str, Any]:
    collection = _db()[PREDICTION_COLLECTION]
    counts = {
        "low": await collection.count_documents({"risk_level": "low"}),
        "medium": await collection.count_documents({"risk_level": "medium"}),
        "high": await collection.count_documents({"risk_level": "high"}),
        "critical": await collection.count_documents({"risk_level": "critical"}),
    }
    average = await collection.aggregate(
        [{"$group": {"_id": None, "average_failure_probability": {"$avg": "$failure_probability"}}}]
    ).to_list(length=1)
    latest_critical_cursor = collection.find({"risk_level": "critical"}).sort("created_at", -1).limit(10)
    return {
        "prediction_counts_by_risk": counts,
        "total_predictions": sum(counts.values()),
        "average_failure_probability": average[0]["average_failure_probability"] if average else 0,
        "latest_critical_predictions": serialize_mongo_list(await latest_critical_cursor.to_list(length=10)),
    }


async def get_predictive_dashboard_metrics() -> dict[str, Any]:
    collection = _db()[PREDICTION_COLLECTION]
    average = await collection.aggregate(
        [{"$group": {"_id": None, "average_failure_probability": {"$avg": "$failure_probability"}}}]
    ).to_list(length=1)
    latest_critical_cursor = collection.find({"risk_level": "critical"}).sort("created_at", -1).limit(5)
    high_risk_vehicle_ids = await collection.distinct("vehicle_id", {"risk_level": "high"})
    medium_risk_vehicle_ids = await collection.distinct("vehicle_id", {"risk_level": "medium"})
    return {
        "latest_predictions_count": await collection.count_documents({}),
        "critical_prediction_count": await collection.count_documents({"risk_level": "critical"}),
        "high_risk_vehicle_count": len(high_risk_vehicle_ids),
        "medium_risk_vehicle_count": len(medium_risk_vehicle_ids),
        "average_failure_probability": average[0]["average_failure_probability"] if average else 0,
        "latest_critical_predictions": serialize_mongo_list(await latest_critical_cursor.to_list(length=5)),
    }


def get_manual_ev_sensor_input_template() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "SoC": 65,
        "SoH": 92,
        "Battery_Voltage": 390,
        "Battery_Current": 55,
        "Battery_Temperature": 35,
        "Charge_Cycles": 450,
        "Motor_Temperature": 70,
        "Motor_Vibration": 0.3,
        "Motor_Torque": 180,
        "Motor_RPM": 3200,
        "Power_Consumption": 22,
        "Brake_Pad_Wear": 35,
        "Brake_Pressure": 60,
        "Reg_Brake_Efficiency": 78,
        "Tire_Pressure": 34,
        "Tire_Temperature": 38,
        "Suspension_Load": 70,
        "Ambient_Temperature": 30,
        "Ambient_Humidity": 72,
        "Load_Weight": 850,
        "Driving_Speed": 48,
        "Distance_Traveled": 42000,
        "Idle_Time": 8,
        "Route_Roughness": 0.4,
        "hour": now.hour,
        "day_of_week": now.weekday(),
        "month": now.month,
        "is_weekend": 1 if now.weekday() >= 5 else 0,
    }


def generate_simulated_ev_sensor_input(vehicle: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    mileage = float(vehicle.get("current_mileage") or 0)
    health_status = vehicle.get("health_status")
    degradation_bias = 1.0 if health_status == "critical" else 0.6 if health_status == "warning" else 0.25
    return {
        "SoC": round(random.uniform(35, 88), 2),
        "SoH": round(random.uniform(78, 96) - degradation_bias * 5, 2),
        "Battery_Voltage": round(random.uniform(360, 415), 2),
        "Battery_Current": round(random.uniform(20, 90), 2),
        "Battery_Temperature": round(random.uniform(28, 48) + degradation_bias * 5, 2),
        "Charge_Cycles": int(random.uniform(220, 900)),
        "Motor_Temperature": round(random.uniform(55, 92) + degradation_bias * 7, 2),
        "Motor_Vibration": round(random.uniform(0.12, 0.85) + degradation_bias * 0.15, 3),
        "Motor_Torque": round(random.uniform(110, 260), 2),
        "Motor_RPM": int(random.uniform(1800, 5200)),
        "Power_Consumption": round(random.uniform(14, 42), 2),
        "Brake_Pad_Wear": round(random.uniform(12, 72) + degradation_bias * 10, 2),
        "Brake_Pressure": round(random.uniform(35, 85), 2),
        "Reg_Brake_Efficiency": round(random.uniform(55, 92) - degradation_bias * 8, 2),
        "Tire_Pressure": round(random.uniform(28, 38), 2),
        "Tire_Temperature": round(random.uniform(30, 54), 2),
        "Suspension_Load": round(random.uniform(45, 96), 2),
        "Ambient_Temperature": round(random.uniform(26, 35), 2),
        "Ambient_Humidity": round(random.uniform(55, 88), 2),
        "Load_Weight": round(random.uniform(250, 1500), 2),
        "Driving_Speed": round(random.uniform(20, 78), 2),
        "Distance_Traveled": mileage,
        "Idle_Time": round(random.uniform(0, 22), 2),
        "Route_Roughness": round(random.uniform(0.12, 0.9), 3),
        "hour": now.hour,
        "day_of_week": now.weekday(),
        "month": now.month,
        "is_weekend": 1 if now.weekday() >= 5 else 0,
    }


async def simulate_vehicle_prediction(vehicle_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    from app.schemas.predictive_schema import EVSensorInput, PredictiveMaintenanceRequest

    vehicle = await _get_vehicle(vehicle_id)
    sensor_data = EVSensorInput(**generate_simulated_ev_sensor_input(vehicle))
    request = PredictiveMaintenanceRequest(vehicle_id=vehicle_id, input_source="simulated", sensor_data=sensor_data)
    return await predict_vehicle_maintenance(request, current_user)
