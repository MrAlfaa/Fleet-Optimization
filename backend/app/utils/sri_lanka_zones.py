from typing import Any

from app.utils.geo_utils import haversine_distance_km
from app.utils.object_id import serialize_mongo_document


DATA_CONTEXT = "colombo_operational_forecast"
DEFAULT_SERVICE_RADIUS_KM = 12.0

SRI_LANKA_ZONE_ALIASES: dict[str, dict[str, Any]] = {
    "LK_colombo_central": {
        "operational_zone_id": "LK_colombo_central",
        "zone_display_name": "Colombo Central",
        "zone_lat": 6.9271,
        "zone_lng": 79.8612,
    },
    "LK_nugegoda": {
        "operational_zone_id": "LK_nugegoda",
        "zone_display_name": "Nugegoda",
        "zone_lat": 6.8649,
        "zone_lng": 79.8997,
    },
    "LK_malabe": {
        "operational_zone_id": "LK_malabe",
        "zone_display_name": "Malabe",
        "zone_lat": 6.9061,
        "zone_lng": 79.9696,
    },
    "LK_dehiwala": {
        "operational_zone_id": "LK_dehiwala",
        "zone_display_name": "Dehiwala",
        "zone_lat": 6.8511,
        "zone_lng": 79.8659,
    },
    "LK_mount_lavinia": {
        "operational_zone_id": "LK_mount_lavinia",
        "zone_display_name": "Mount Lavinia",
        "zone_lat": 6.8389,
        "zone_lng": 79.8638,
    },
    "LK_rajagiriya": {
        "operational_zone_id": "LK_rajagiriya",
        "zone_display_name": "Rajagiriya",
        "zone_lat": 6.9097,
        "zone_lng": 79.8943,
    },
    "LK_battaramulla": {
        "operational_zone_id": "LK_battaramulla",
        "zone_display_name": "Battaramulla",
        "zone_lat": 6.9022,
        "zone_lng": 79.9197,
    },
    "LK_kaduwela": {
        "operational_zone_id": "LK_kaduwela",
        "zone_display_name": "Kaduwela",
        "zone_lat": 6.9319,
        "zone_lng": 79.9842,
    },
    "LK_moratuwa": {
        "operational_zone_id": "LK_moratuwa",
        "zone_display_name": "Moratuwa",
        "zone_lat": 6.7730,
        "zone_lng": 79.8816,
    },
    "LK_kotte": {
        "operational_zone_id": "LK_kotte",
        "zone_display_name": "Sri Jayawardenepura Kotte",
        "zone_lat": 6.8905,
        "zone_lng": 79.9015,
    },
    "LK_wellawatte": {
        "operational_zone_id": "LK_wellawatte",
        "zone_display_name": "Wellawatte",
        "zone_lat": 6.8747,
        "zone_lng": 79.8605,
    },
    "LK_kollupitiya": {
        "operational_zone_id": "LK_kollupitiya",
        "zone_display_name": "Kollupitiya",
        "zone_lat": 6.9105,
        "zone_lng": 79.8503,
    },
    "LK_borella": {
        "operational_zone_id": "LK_borella",
        "zone_display_name": "Borella",
        "zone_lat": 6.9147,
        "zone_lng": 79.8777,
    },
    "LK_wattala": {
        "operational_zone_id": "LK_wattala",
        "zone_display_name": "Wattala",
        "zone_lat": 6.9897,
        "zone_lng": 79.8927,
    },
    "LK_piliyandala": {
        "operational_zone_id": "LK_piliyandala",
        "zone_display_name": "Piliyandala",
        "zone_lat": 6.8018,
        "zone_lng": 79.9227,
    },
}

_LEGACY_SOURCE_TO_OPERATIONAL = {
    "SP_sao_paulo": "LK_colombo_central",
    "SP_guarulhos": "LK_nugegoda",
    "SP_sao_bernardo_do_campo": "LK_malabe",
}


def source_zone_id(zone_id: str) -> str:
    return operational_zone_id(zone_id)


def operational_zone_id(zone_id: str) -> str:
    return _LEGACY_SOURCE_TO_OPERATIONAL.get(zone_id, zone_id)


def _fallback_display_name(zone_id: str) -> str:
    value = zone_id[3:] if zone_id.startswith("LK_") else zone_id
    return value.replace("_", " ").title()


def enrich_zone_record(record: dict[str, Any]) -> dict[str, Any]:
    safe_record = serialize_mongo_document(record) or {}
    original_zone_id = str(safe_record.get("source_zone_id") or safe_record.get("zone_id") or "")
    operational = operational_zone_id(original_zone_id)
    alias = SRI_LANKA_ZONE_ALIASES.get(operational)
    return {
        **safe_record,
        "zone_id": operational,
        "source_zone_id": operational,
        "operational_zone_id": operational,
        "zone_display_name": str(alias["zone_display_name"]) if alias else _fallback_display_name(operational),
        "zone_lat": alias["zone_lat"] if alias else safe_record.get("zone_lat"),
        "zone_lng": alias["zone_lng"] if alias else safe_record.get("zone_lng"),
        "data_context": DATA_CONTEXT,
    }


def operational_zone_options() -> list[dict[str, Any]]:
    return [
        {
            "source_zone_id": source,
            **alias,
            "zone_id": alias["operational_zone_id"],
            "service_radius_km": DEFAULT_SERVICE_RADIUS_KM,
            "data_context": DATA_CONTEXT,
        }
        for source, alias in SRI_LANKA_ZONE_ALIASES.items()
    ]


def nearest_operational_zone(latitude: float, longitude: float) -> dict[str, Any]:
    candidates = []
    for option in operational_zone_options():
        distance = haversine_distance_km(latitude, longitude, float(option["zone_lat"]), float(option["zone_lng"]))
        candidates.append({**option, "distance_km": round(distance, 2)})
    nearest = min(candidates, key=lambda item: item["distance_km"])
    return {**nearest, "within_service_area": nearest["distance_km"] <= nearest["service_radius_km"]}


def prepare_delivery_zone(latitude: float, longitude: float, requested_zone_id: str | None, assignment_method: str | None = None) -> dict[str, Any]:
    nearest = nearest_operational_zone(latitude, longitude)
    if not requested_zone_id:
        return {
            "zone_id": nearest["operational_zone_id"],
            "operational_zone_id": nearest["operational_zone_id"],
            "source_zone_id": nearest["source_zone_id"],
            "zone_assignment_method": "nearest",
            "zone_distance_km": nearest["distance_km"],
            "within_service_area": nearest["within_service_area"],
        }
    source = source_zone_id(requested_zone_id)
    alias = SRI_LANKA_ZONE_ALIASES.get(source)
    if alias is None:
        raise ValueError("Unknown Sri Lankan operational zone")
    selected_id = str(alias["operational_zone_id"])
    selected_distance = haversine_distance_km(latitude, longitude, float(alias["zone_lat"]), float(alias["zone_lng"]))
    method = assignment_method or ("confirmed" if selected_id == nearest["operational_zone_id"] else "manual_override")
    if method not in {"nearest", "confirmed", "manual_override"}:
        raise ValueError("Invalid zone assignment method")
    return {
        "zone_id": selected_id,
        "operational_zone_id": selected_id,
        "source_zone_id": source,
        "zone_assignment_method": method,
        "zone_distance_km": round(selected_distance, 2),
        "within_service_area": selected_distance <= DEFAULT_SERVICE_RADIUS_KM,
    }
