from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.core.permissions import effective_permissions
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.user_model import USER_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.utils.sri_lanka_zones import SRI_LANKA_ZONE_ALIASES


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return database


async def global_search(query: str, current_user: dict[str, Any], types: set[str] | None = None) -> dict[str, Any]:
    query = query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search query must contain at least 2 characters")
    allowed = effective_permissions(str(current_user.get("role", "")), current_user.get("permission_overrides"))
    requested = types or {"vehicles", "drivers", "deliveries", "routes", "zones"}
    regex = {"$regex": re.escape(query), "$options": "i"}
    results: list[dict[str, Any]] = []

    if "vehicles" in requested and "vehicles.view" in allowed:
        rows = await _db()[VEHICLE_COLLECTION].find({"$or": [{"registration_number": regex}, {"vehicle_code": regex}]}, {"registration_number": 1, "vehicle_code": 1}).limit(6).to_list(6)
        results.extend({"type": "vehicle", "id": str(row["_id"]), "title": row.get("registration_number") or row.get("vehicle_code"), "subtitle": row.get("vehicle_code", ""), "path": f"/vehicles/{row['_id']}"} for row in rows)
    if "drivers" in requested and ("drivers.manage" in allowed or "routes.view" in allowed):
        rows = await _db()[USER_COLLECTION].find({"role": "driver", "$or": [{"username": regex}, {"full_name": regex}, {"email": regex}]}, {"username": 1, "full_name": 1}).limit(6).to_list(6)
        results.extend({"type": "driver", "id": str(row["_id"]), "title": f"@{row.get('username', 'driver')}", "subtitle": row.get("full_name", ""), "path": "/drivers/manage"} for row in rows)
    if "deliveries" in requested and "deliveries.view" in allowed:
        rows = await _db()[DELIVERY_COLLECTION].find({"order_code": regex}, {"order_code": 1, "customer_name": 1}).limit(6).to_list(6)
        results.extend({"type": "delivery", "id": str(row["_id"]), "title": row.get("order_code", "Delivery"), "subtitle": row.get("customer_name", ""), "path": "/deliveries"} for row in rows)
    if "routes" in requested and "routes.view" in allowed:
        rows = await _db()[ROUTE_PLAN_COLLECTION].find({"$or": [{"route_code": regex}, {"route_name": regex}]}, {"route_code": 1, "route_name": 1}).limit(6).to_list(6)
        results.extend({"type": "route", "id": str(row["_id"]), "title": row.get("route_code", "Route"), "subtitle": row.get("route_name", ""), "path": "/route-planning"} for row in rows)
    if "zones" in requested and "demand.view" in allowed:
        needle = query.casefold()
        for source_id, zone in SRI_LANKA_ZONE_ALIASES.items():
            if needle in source_id.casefold() or needle in zone["operational_zone_id"].casefold() or needle in zone["zone_display_name"].casefold():
                results.append({"type": "zone", "id": zone["operational_zone_id"], "title": zone["zone_display_name"], "subtitle": "Sri Lanka operational zone", "path": "/zones"})
    return {"items": results[:25], "query": query}
