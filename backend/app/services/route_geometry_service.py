from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import settings


Coordinate = tuple[float, float]
Fetcher = Callable[[str, float], Awaitable[dict[str, Any]]]


async def _default_fetcher(url: str, timeout: float) -> dict[str, Any]:
    def request() -> dict[str, Any]:
        headers = {"User-Agent": "FleetOpt-Research-MVP/1.0 (route geometry)"}
        with urlopen(Request(url, headers=headers), timeout=timeout) as response:  # noqa: S310 - URL is configured server-side.
            return json.loads(response.read().decode("utf-8"))

    return await asyncio.to_thread(request)


class RouteGeometryService:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 5.0,
        cache_ttl_seconds: float = 86_400,
        fetcher: Fetcher | None = None,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._base_url = (base_url or settings.osrm_base_url).rstrip("/")
        self._timeout = timeout_seconds
        self._cache_ttl = cache_ttl_seconds
        self._fetcher = fetcher or _default_fetcher
        self._now = now
        self._sleep = sleep
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._request_lock = asyncio.Lock()
        self._last_request_at = float("-inf")

    @staticmethod
    def _validate(coordinates: list[Coordinate]) -> list[Coordinate]:
        if len(coordinates) < 2:
            raise ValueError("Route geometry requires at least two coordinates")
        result: list[Coordinate] = []
        for latitude, longitude in coordinates:
            latitude = float(latitude)
            longitude = float(longitude)
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Route geometry contains invalid coordinates")
            result.append((latitude, longitude))
        return result

    @staticmethod
    def _key(coordinates: list[Coordinate]) -> str:
        canonical = ";".join(f"{latitude:.6f},{longitude:.6f}" for latitude, longitude in coordinates)
        return hashlib.sha256(canonical.encode("ascii")).hexdigest()

    @staticmethod
    def _fallback(coordinates: list[Coordinate]) -> dict[str, Any]:
        return {
            "geometry_source": "fallback",
            "coordinates": [
                {"latitude": latitude, "longitude": longitude}
                for latitude, longitude in coordinates
            ],
            "cached": False,
        }

    def _url(self, coordinates: list[Coordinate]) -> str:
        path = ";".join(f"{longitude:.6f},{latitude:.6f}" for latitude, longitude in coordinates)
        return f"{self._base_url}/route/v1/driving/{quote(path, safe=',;.')}?overview=full&geometries=geojson"

    async def _rate_limited_fetch(self, url: str) -> dict[str, Any]:
        async with self._request_lock:
            remaining = 1.0 - (self._now() - self._last_request_at)
            if remaining > 0:
                await self._sleep(remaining)
            try:
                return await self._fetcher(url, self._timeout)
            finally:
                self._last_request_at = self._now()

    async def geometry(self, coordinates: list[Coordinate]) -> dict[str, Any]:
        coordinates = self._validate(coordinates)
        cache_key = self._key(coordinates)
        cached = self._cache.get(cache_key)
        if cached and self._now() - cached[0] < self._cache_ttl:
            result = deepcopy(cached[1])
            result["cached"] = True
            return result

        try:
            payload = await self._rate_limited_fetch(self._url(coordinates))
            line = payload["routes"][0]["geometry"]["coordinates"]
            if payload.get("code") != "Ok" or len(line) < 2:
                raise ValueError("OSRM did not return a route")
            result = {
                "geometry_source": "osrm",
                "coordinates": [
                    {"latitude": float(latitude), "longitude": float(longitude)}
                    for longitude, latitude in line
                ],
                "cached": False,
            }
            self._cache[cache_key] = (self._now(), result)
            return deepcopy(result)
        except (KeyError, IndexError, TypeError, ValueError, OSError, TimeoutError):
            return self._fallback(coordinates)


route_geometry_service = RouteGeometryService()


def ensure_route_geometry_access(route: dict[str, Any], current_user: dict[str, Any]) -> None:
    if str(current_user.get("role") or "") != "driver":
        return
    assigned_driver = route.get("driver_id")
    if assigned_driver is None or str(assigned_driver) != str(current_user.get("id") or ""):
        raise PermissionError("Drivers may only view geometry for their assigned route")


def route_plan_coordinates(route: dict[str, Any]) -> list[Coordinate]:
    depot = (float(route["depot_latitude"]), float(route["depot_longitude"]))
    coordinates: list[Coordinate] = [depot]
    for stop in route.get("optimized_stop_order") or []:
        latitude = stop.get("latitude", stop.get("drop_latitude"))
        longitude = stop.get("longitude", stop.get("drop_longitude"))
        if latitude is None or longitude is None:
            continue
        point = (float(latitude), float(longitude))
        if point != coordinates[-1]:
            coordinates.append(point)
    if coordinates[-1] != depot:
        coordinates.append(depot)
    return coordinates
