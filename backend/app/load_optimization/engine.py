from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np


BRANCH_POINT = {"latitude": 6.9271, "longitude": 79.8612}


@dataclass(frozen=True)
class _Parcel:
    parcel_id: str
    weight_kg: float
    latitude: float
    longitude: float
    profile: dict[str, Any]

    @property
    def volume_m3(self) -> float:
        return float(self.profile.get("volume_m3") or 0)


def _parcel(document: dict[str, Any]) -> _Parcel:
    return _Parcel(
        parcel_id=str(document.get("id") or document.get("_id") or document.get("order_code") or ""),
        weight_kg=float(document.get("parcel_weight") or 0),
        latitude=float(document.get("drop_latitude") or 0),
        longitude=float(document.get("drop_longitude") or 0),
        profile=dict(document.get("load_profile") or {}),
    )


def _compatible_type(parcel: _Parcel, vehicle: dict[str, Any]) -> tuple[bool, list[str]]:
    profile = parcel.profile
    reasons: list[str] = []
    dimensions = sorted([
        float(profile.get("length_cm") or 0),
        float(profile.get("width_cm") or 0),
        float(profile.get("height_cm") or 0),
    ])
    bay = sorted([
        float(vehicle.get("cargo_length_cm") or 0),
        float(vehicle.get("cargo_width_cm") or 0),
        float(vehicle.get("cargo_height_cm") or 0),
    ])
    fixed = bool(profile.get("loading_orientation_fixed") or profile.get("do_not_tilt"))
    if fixed:
        fits_dimensions = (
            float(profile.get("length_cm") or 0) <= float(vehicle.get("cargo_length_cm") or 0)
            and float(profile.get("width_cm") or 0) <= float(vehicle.get("cargo_width_cm") or 0)
            and float(profile.get("height_cm") or 0) <= float(vehicle.get("cargo_height_cm") or 0)
        )
    else:
        fits_dimensions = all(value <= limit for value, limit in zip(dimensions, bay))
    if not fits_dimensions:
        reasons.append("Parcel dimensions exceed cargo bay")
    if parcel.weight_kg > float(vehicle.get("capacity_kg") or 0):
        reasons.append("Parcel weight exceeds payload capacity")
    if parcel.volume_m3 > float(vehicle.get("capacity_m3") or 0):
        reasons.append("Parcel volume exceeds cargo capacity")
    if profile.get("hazardous") and not vehicle.get("is_hazmat_certified"):
        reasons.append("Hazmat certification is unavailable")
    if profile.get("requires_refrigeration"):
        if not vehicle.get("is_refrigerated"):
            reasons.append("Refrigeration capability is unavailable")
        else:
            vehicle_min = vehicle.get("temp_min_celsius")
            vehicle_max = vehicle.get("temp_max_celsius")
            parcel_min = profile.get("temp_min_celsius")
            parcel_max = profile.get("temp_max_celsius")
            if (
                vehicle_min is None or vehicle_max is None or parcel_min is None or parcel_max is None
                or float(vehicle_min) > float(parcel_min) or float(vehicle_max) < float(parcel_max)
            ):
                reasons.append("Vehicle temperature range is incompatible")
    return not reasons, reasons


def _cluster_parcels(parcels: list[_Parcel]) -> tuple[dict[int, list[_Parcel]], str]:
    if len(parcels) < 5:
        return {0: parcels}, "single_region"
    coordinates = np.array([[parcel.latitude, parcel.longitude] for parcel in parcels], dtype=float)
    try:
        from sklearn.cluster import HDBSCAN

        labels = HDBSCAN(min_cluster_size=max(3, min(12, len(parcels) // 8 or 3)), min_samples=2).fit_predict(coordinates)
        method = "hdbscan"
    except (ImportError, ValueError):
        labels = np.zeros(len(parcels), dtype=int)
        method = "single_region_fallback"

    non_noise = sorted(set(int(label) for label in labels if int(label) >= 0))
    if not non_noise:
        labels = np.zeros(len(parcels), dtype=int)
    elif -1 in labels:
        centres = {
            label: coordinates[labels == label].mean(axis=0)
            for label in non_noise
        }
        for index, label in enumerate(labels):
            if int(label) == -1:
                labels[index] = min(non_noise, key=lambda candidate: float(np.linalg.norm(coordinates[index] - centres[candidate])))

    grouped: dict[int, list[_Parcel]] = {}
    for parcel, label in zip(parcels, labels):
        grouped.setdefault(int(label), []).append(parcel)
    return {label: sorted(items, key=lambda item: item.parcel_id) for label, items in sorted(grouped.items())}, method


def _load_accepts(load: dict[str, Any], parcel: _Parcel, vehicle: dict[str, Any]) -> bool:
    if len(load["parcels"]) >= int(vehicle.get("max_parcels") or 0):
        return False
    if load["used_weight_kg"] + parcel.weight_kg > float(vehicle["capacity_kg"]):
        return False
    if load["used_volume_m3"] + parcel.volume_m3 > float(vehicle["capacity_m3"]):
        return False
    load_profile = load["special_profile"]
    parcel_profile = parcel.profile
    if bool(load_profile["hazardous"]) != bool(parcel_profile.get("hazardous")):
        return False
    if bool(load_profile["requires_refrigeration"]) != bool(parcel_profile.get("requires_refrigeration")):
        return False
    if parcel_profile.get("requires_refrigeration"):
        if load_profile["temp_min_celsius"] != parcel_profile.get("temp_min_celsius"):
            return False
        if load_profile["temp_max_celsius"] != parcel_profile.get("temp_max_celsius"):
            return False
    return True


def _candidate_catalog(parcel: _Parcel, catalog: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    candidates = [vehicle for vehicle in catalog if _compatible_type(parcel, vehicle)[0]]
    candidates.sort(
        key=lambda item: (float(item["capacity_m3"]), float(item["capacity_kg"]), str(item["code"])),
    )
    if strategy == "largest_capacity":
        candidates.reverse()
    elif strategy == "balanced_capacity" and candidates:
        middle = len(candidates) // 2
        candidates = [candidates[middle], *candidates[:middle], *candidates[middle + 1:]]
    elif strategy.startswith("nsga2_bias_") and candidates:
        bias = max(0.0, min(float(strategy.removeprefix("nsga2_bias_")), 1.0))
        selected_index = min(round(bias * (len(candidates) - 1)), len(candidates) - 1)
        candidates = [candidates[selected_index], *candidates[:selected_index], *candidates[selected_index + 1:]]
    return candidates


def _orient(parcel: _Parcel, vehicle: dict[str, Any]) -> tuple[float, float, float]:
    profile = parcel.profile
    original = (
        float(profile["length_cm"]), float(profile["width_cm"]), float(profile["height_cm"]),
    )
    if profile.get("loading_orientation_fixed") or profile.get("do_not_tilt"):
        return original
    rotations = [
        original,
        (original[1], original[0], original[2]),
        (original[2], original[1], original[0]),
        (original[0], original[2], original[1]),
        (original[1], original[2], original[0]),
        (original[2], original[0], original[1]),
    ]
    fitting = [
        dims for dims in rotations
        if dims[0] <= float(vehicle["cargo_length_cm"])
        and dims[1] <= float(vehicle["cargo_width_cm"])
        and dims[2] <= float(vehicle["cargo_height_cm"])
    ]
    return min(fitting, key=lambda dims: (dims[1], dims[0], dims[2]))


def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = (math.radians(value) for value in first)
    lat2, lon2 = (math.radians(value) for value in second)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1 - value)))


def _route_preview(parcels: list[_Parcel]) -> tuple[list[dict[str, Any]], float]:
    branch = (BRANCH_POINT["latitude"], BRANCH_POINT["longitude"])
    current = branch
    remaining = list(sorted(parcels, key=lambda item: item.parcel_id))
    path: list[dict[str, Any]] = [{"type": "branch", **BRANCH_POINT}]
    distance = 0.0
    while remaining:
        selected = min(
            remaining,
            key=lambda item: (_distance_km(current, (item.latitude, item.longitude)), item.parcel_id),
        )
        point = (selected.latitude, selected.longitude)
        distance += _distance_km(current, point)
        path.append({
            "type": "parcel",
            "parcel_id": selected.parcel_id,
            "latitude": selected.latitude,
            "longitude": selected.longitude,
        })
        remaining.remove(selected)
        current = point
    distance += _distance_km(current, branch)
    path.append({"type": "branch", **BRANCH_POINT})
    return path, round(distance, 3)


def _place(parcels: list[_Parcel], vehicle: dict[str, Any]) -> tuple[list[dict[str, Any]], list[_Parcel]]:
    placements: list[dict[str, Any]] = []
    rejected: list[_Parcel] = []
    x = y = row_depth = 0.0
    parcel_by_id = {parcel.parcel_id: parcel for parcel in parcels}
    ordered = sorted(parcels, key=lambda item: (bool(item.profile.get("fragile")), -item.volume_m3, item.parcel_id))
    for parcel in ordered:
        length, width, height = _orient(parcel, vehicle)
        if parcel.profile.get("fragile") and int(vehicle.get("max_stack_layers") or 1) >= 2:
            support = next((
                item for item in placements
                if item["layer"] == 0
                and not item["fragile"]
                and not item.get("supports_load")
                and parcel_by_id[item["parcel_id"]].profile.get("stackable", True)
                and float(parcel_by_id[item["parcel_id"]].profile.get("max_stack_weight_kg") or 0) >= parcel.weight_kg
                and length <= item["length_cm"]
                and width <= item["width_cm"]
                and item["z_cm"] + item["height_cm"] + height <= float(vehicle["cargo_height_cm"])
            ), None)
            if support is not None:
                support["supports_load"] = True
                placements.append({
                    "parcel_id": parcel.parcel_id,
                    "x_cm": support["x_cm"], "y_cm": support["y_cm"],
                    "z_cm": round(support["z_cm"] + support["height_cm"], 3),
                    "length_cm": length, "width_cm": width, "height_cm": height,
                    "layer": 1,
                    "fragile": True,
                    "fixed_orientation": bool(parcel.profile.get("loading_orientation_fixed") or parcel.profile.get("do_not_tilt")),
                })
                continue
        if x + length > float(vehicle["cargo_length_cm"]):
            x = 0.0
            y += row_depth
            row_depth = 0.0
        if y + width > float(vehicle["cargo_width_cm"]):
            rejected.append(parcel)
            continue
        placements.append({
            "parcel_id": parcel.parcel_id,
            "x_cm": round(x, 3), "y_cm": round(y, 3), "z_cm": 0.0,
            "length_cm": length, "width_cm": width, "height_cm": height,
            "layer": 0,
            "fragile": bool(parcel.profile.get("fragile")),
            "fixed_orientation": bool(parcel.profile.get("loading_orientation_fixed") or parcel.profile.get("do_not_tilt")),
        })
        x += length
        row_depth = max(row_depth, width)
    return placements, rejected


def _build_option(
    regions: dict[int, list[_Parcel]], catalog: list[dict[str, Any]], strategy: str, seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    loads: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    for region_id, region_parcels in regions.items():
        for parcel in sorted(region_parcels, key=lambda item: (-item.volume_m3, -item.weight_kg, item.parcel_id)):
            candidates = _candidate_catalog(parcel, catalog, strategy)
            if not candidates:
                reasons = sorted({reason for vehicle in catalog for reason in _compatible_type(parcel, vehicle)[1]})
                exceptions.append({"parcel_id": parcel.parcel_id, "reasons": reasons or ["No compatible vehicle profile"]})
                continue
            accepted = False
            for load in loads:
                if load["region_id"] != region_id:
                    continue
                vehicle = next(item for item in catalog if item["code"] == load["vehicle_type_code"])
                if _load_accepts(load, parcel, vehicle):
                    load["parcels"].append(parcel)
                    load["used_weight_kg"] += parcel.weight_kg
                    load["used_volume_m3"] += parcel.volume_m3
                    accepted = True
                    break
            if not accepted:
                vehicle = candidates[0]
                profile = parcel.profile
                loads.append({
                    "region_id": region_id,
                    "vehicle_type_code": vehicle["code"],
                    "parcels": [parcel],
                    "used_weight_kg": parcel.weight_kg,
                    "used_volume_m3": parcel.volume_m3,
                    "special_profile": {
                        "hazardous": bool(profile.get("hazardous")),
                        "requires_refrigeration": bool(profile.get("requires_refrigeration")),
                        "temp_min_celsius": profile.get("temp_min_celsius"),
                        "temp_max_celsius": profile.get("temp_max_celsius"),
                    },
                })

    finalized: list[dict[str, Any]] = []
    for index, load in enumerate(loads, start=1):
        vehicle = next(item for item in catalog if item["code"] == load["vehicle_type_code"])
        placements, rejected = _place(load["parcels"], vehicle)
        if rejected:
            exceptions.extend({"parcel_id": parcel.parcel_id, "reasons": ["3D placement is infeasible"]} for parcel in rejected)
        placed_ids = {item["parcel_id"] for item in placements}
        parcels = [parcel for parcel in load["parcels"] if parcel.parcel_id in placed_ids]
        if not parcels:
            continue
        digest = hashlib.sha256(f"{seed}:{strategy}:{index}:{','.join(sorted(placed_ids))}".encode()).hexdigest()[:10]
        route_preview, estimated_route_km = _route_preview(parcels)
        finalized.append({
            "load_id": f"LOAD-{digest.upper()}",
            "region_id": load["region_id"],
            "vehicle_type_code": load["vehicle_type_code"],
            "capacity_kg": vehicle["capacity_kg"],
            "capacity_m3": vehicle["capacity_m3"],
            "cargo_length_cm": vehicle["cargo_length_cm"],
            "cargo_width_cm": vehicle["cargo_width_cm"],
            "cargo_height_cm": vehicle["cargo_height_cm"],
            "used_weight_kg": round(sum(item.weight_kg for item in parcels), 4),
            "used_volume_m3": round(sum(item.volume_m3 for item in parcels), 6),
            "parcel_count": len(parcels),
            "parcel_ids": sorted(placed_ids),
            "placements": sorted(placements, key=lambda item: (item.get("layer", 0), item["parcel_id"])),
            "loading_sequence": [
                item["parcel_id"]
                for item in sorted(placements, key=lambda value: (value.get("layer", 0), value.get("fragile", False), value["parcel_id"]))
            ],
            "requires_refrigeration": load["special_profile"]["requires_refrigeration"],
            "temp_min_celsius": load["special_profile"]["temp_min_celsius"],
            "temp_max_celsius": load["special_profile"]["temp_max_celsius"],
            "hazardous": load["special_profile"]["hazardous"],
            "assigned_vehicle_id": None,
            "route_preview": route_preview,
            "estimated_route_km": estimated_route_km,
        })
    unused_volume = sum(float(load["capacity_m3"]) - float(load["used_volume_m3"]) for load in finalized)
    option_digest = hashlib.sha256(f"{seed}:{strategy}".encode()).hexdigest()[:8]
    option = {
        "option_id": f"OPTION-{option_digest.upper()}",
        "label": strategy.replace("_", " ").title(),
        "strategy": strategy,
        "objectives": {
            "vehicle_count": len(finalized),
            "unused_volume_m3": round(unused_volume, 4),
            "unassigned_parcels": len(exceptions),
            "estimated_route_km": round(sum(float(load["estimated_route_km"]) for load in finalized), 3),
        },
        "loads": finalized,
        "exceptions": sorted(exceptions, key=lambda item: item["parcel_id"]),
    }
    return option, sorted(exceptions, key=lambda item: item["parcel_id"])


def _region_summary(regions: dict[int, list[_Parcel]]) -> list[dict[str, Any]]:
    return [
        {
            "region_id": region_id,
            "parcel_count": len(parcels),
            "total_weight_kg": round(sum(item.weight_kg for item in parcels), 3),
            "total_volume_m3": round(sum(item.volume_m3 for item in parcels), 6),
            "centroid": {
                "latitude": round(sum(item.latitude for item in parcels) / len(parcels), 6),
                "longitude": round(sum(item.longitude for item in parcels) / len(parcels), 6),
            },
            "parcel_ids": [item.parcel_id for item in parcels],
        }
        for region_id, parcels in regions.items()
    ]


def consolidate_batch(documents: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build the deterministic spatial snapshot used before load assignment."""
    parcels = sorted((_parcel(document) for document in documents), key=lambda item: item.parcel_id)
    if not parcels:
        return {"parcel_count": 0, "cluster_method": "empty", "regions": []}
    regions, cluster_method = _cluster_parcels(parcels)
    region_by_parcel = {
        parcel.parcel_id: region_id
        for region_id, region_parcels in regions.items()
        for parcel in region_parcels
    }
    return {
        "parcel_count": len(parcels),
        "cluster_method": cluster_method,
        "regions": _region_summary(regions),
        "parcel_points": [
            {
                "parcel_id": parcel.parcel_id,
                "order_code": parcel.parcel_id,
                "latitude": parcel.latitude,
                "longitude": parcel.longitude,
                "region_id": region_by_parcel[parcel.parcel_id],
            }
            for parcel in parcels
        ],
    }


def _optimization_strategies(
    regions: dict[int, list[_Parcel]], catalog: list[dict[str, Any]], seed: int,
) -> tuple[list[str], str]:
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.optimize import minimize
    except ImportError:
        return ["smallest_capacity", "balanced_capacity", "largest_capacity"], "deterministic_pareto_fallback"

    class CapacityBiasProblem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=1, n_obj=3, xl=np.array([0.0]), xu=np.array([1.0]))

        def _evaluate(self, x, out, *args, **kwargs):
            strategy = f"nsga2_bias_{float(x[0]):.4f}"
            option, exceptions = _build_option(regions, catalog, strategy, seed)
            objectives = option["objectives"]
            out["F"] = np.array([
                float(objectives["vehicle_count"]),
                float(objectives["unused_volume_m3"]),
                float(len(exceptions)),
            ])

    result = minimize(
        CapacityBiasProblem(),
        NSGA2(pop_size=12),
        termination=("n_gen", 8),
        seed=seed,
        verbose=False,
    )
    raw = np.atleast_2d(result.X) if result.X is not None else np.empty((0, 1))
    biases = sorted({0.0, 1.0, *(round(float(row[0]), 4) for row in raw)})
    if len(biases) > 4:
        biases = [biases[0], biases[len(biases) // 3], biases[(2 * len(biases)) // 3], biases[-1]]
    return [f"nsga2_bias_{bias:.4f}" for bias in biases], "nsga2"


def optimize_batch(documents: Iterable[dict[str, Any]], catalog: list[dict[str, Any]], *, seed: int) -> dict[str, Any]:
    parcels = sorted((_parcel(document) for document in documents), key=lambda item: item.parcel_id)
    regions, cluster_method = _cluster_parcels(parcels)
    options: list[dict[str, Any]] = []
    all_exceptions: dict[str, dict[str, Any]] = {}
    strategies, assignment_method = _optimization_strategies(regions, catalog, seed)
    for strategy in strategies:
        option, exceptions = _build_option(regions, catalog, strategy, seed)
        options.append(option)
        for exception in exceptions:
            all_exceptions[exception["parcel_id"]] = exception
    options.sort(key=lambda item: (
        item["objectives"]["unassigned_parcels"],
        item["objectives"]["vehicle_count"],
        item["objectives"]["unused_volume_m3"],
        item["option_id"],
    ))
    selected = options[0] if options else {"option_id": "OPTION-EMPTY", "loads": [], "objectives": {}}
    return {
        "regions": _region_summary(regions),
        "exceptions": [all_exceptions[key] for key in sorted(all_exceptions)],
        "pareto_options": options,
        "selected_option": selected,
        "engine": {
            "name": "fleetopt-controlled-hdbscan-pareto-3d",
            "version": "1.0.0",
            "cluster_method": cluster_method,
            "assignment_method": assignment_method,
            "seed": int(seed),
        },
    }
