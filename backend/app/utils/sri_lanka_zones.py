from typing import Any

from app.utils.geo_utils import haversine_distance_km
from app.utils.object_id import serialize_mongo_document


DATA_CONTEXT = "sri_lanka_demo_alias"
DEFAULT_SERVICE_RADIUS_KM = 35.0

SRI_LANKA_ZONE_ALIASES: dict[str, dict[str, Any]] = {
    "SP_sao_paulo": {
        "operational_zone_id": "LK_colombo_central",
        "zone_display_name": "Colombo Central",
        "zone_lat": 6.9271,
        "zone_lng": 79.8612,
    },
    "RJ_rio_de_janeiro": {
        "operational_zone_id": "LK_kandy_city",
        "zone_display_name": "Kandy City",
        "zone_lat": 7.2906,
        "zone_lng": 80.6337,
    },
    "MG_belo_horizonte": {
        "operational_zone_id": "LK_galle_city",
        "zone_display_name": "Galle City",
        "zone_lat": 6.0329,
        "zone_lng": 80.2168,
    },
    "DF_brasilia": {
        "operational_zone_id": "LK_kurunegala",
        "zone_display_name": "Kurunegala",
        "zone_lat": 7.4863,
        "zone_lng": 80.3647,
    },
    "PR_curitiba": {
        "operational_zone_id": "LK_jaffna_city",
        "zone_display_name": "Jaffna City",
        "zone_lat": 9.6615,
        "zone_lng": 80.0255,
    },
    "SP_campinas": {
        "operational_zone_id": "LK_negombo",
        "zone_display_name": "Negombo",
        "zone_lat": 7.2083,
        "zone_lng": 79.8358,
    },
    "RS_porto_alegre": {
        "operational_zone_id": "LK_gampaha",
        "zone_display_name": "Gampaha",
        "zone_lat": 7.0873,
        "zone_lng": 80.0144,
    },
    "BA_salvador": {
        "operational_zone_id": "LK_matara",
        "zone_display_name": "Matara",
        "zone_lat": 5.9549,
        "zone_lng": 80.5550,
    },
    "SP_guarulhos": {
        "operational_zone_id": "LK_nugegoda",
        "zone_display_name": "Nugegoda",
        "zone_lat": 6.8649,
        "zone_lng": 79.8997,
    },
    "SP_sao_bernardo_do_campo": {
        "operational_zone_id": "LK_malabe",
        "zone_display_name": "Malabe",
        "zone_lat": 6.9061,
        "zone_lng": 79.9696,
    },
}

_SOURCE_BY_OPERATIONAL = {
    alias["operational_zone_id"]: source
    for source, alias in SRI_LANKA_ZONE_ALIASES.items()
}


def source_zone_id(zone_id: str) -> str:
    return _SOURCE_BY_OPERATIONAL.get(zone_id, zone_id)


def operational_zone_id(zone_id: str) -> str:
    source = source_zone_id(zone_id)
    alias = SRI_LANKA_ZONE_ALIASES.get(source)
    return str(alias["operational_zone_id"]) if alias else zone_id


def _fallback_display_name(zone_id: str) -> str:
    value = zone_id[3:] if zone_id.startswith("LK_") else zone_id
    return value.replace("_", " ").title()


def enrich_zone_record(record: dict[str, Any]) -> dict[str, Any]:
    safe_record = serialize_mongo_document(record) or {}
    original_zone_id = str(safe_record.get("source_zone_id") or safe_record.get("zone_id") or "")
    source = source_zone_id(original_zone_id)
    alias = SRI_LANKA_ZONE_ALIASES.get(source)
    operational = str(alias["operational_zone_id"]) if alias else original_zone_id
    return {
        **safe_record,
        "zone_id": operational,
        "source_zone_id": source,
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
