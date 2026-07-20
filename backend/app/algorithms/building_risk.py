"""Drone vs OSM building solid clearance / risk (points + trajectory segments)."""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ..buildings.osm import Building, building_store, clearance_to_building
from ..buildings.trajectory import classify_trajectory_buildings, segment_clearance_to_building


def analyze_building_risk(
    df: pd.DataFrame,
    aircraft_id: str,
    threshold_m: float = 30.0,
    buildings: Optional[list[Building]] = None,
) -> dict:
    buildings = buildings if buildings is not None else building_store.get().buildings
    if not buildings:
        raise ValueError("No buildings loaded. Fetch OSM buildings for the airspace first.")

    series = df[df["aircraft_id"] == aircraft_id].sort_values("timestamp")
    if series.empty:
        raise ValueError(f"No telemetry for {aircraft_id}")

    # Keep enough points for meaningful segments (cap for payload size)
    if len(series) > 800:
        step = max(1, len(series) // 800)
        series = series.iloc[::step]

    path = [
        {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "altitude": float(row["altitude"]),
            "timestamp": row["timestamp"],
        }
        for _, row in series.iterrows()
    ]

    collision_ids, risk_ids = classify_trajectory_buildings(path, buildings, threshold_m)

    samples = []
    min_clearance = float("inf")
    penetrations = 0
    at_risk = 0
    nearest_building = None

    # Per-point series for charts (endpoints of segments)
    for i, p in enumerate(path):
        best = None
        # Prefer segment clearance to next point when available
        if i < len(path) - 1:
            nxt = path[i + 1]
            for b in buildings:
                c = segment_clearance_to_building(
                    p["latitude"], p["longitude"], p["altitude"],
                    nxt["latitude"], nxt["longitude"], nxt["altitude"],
                    b,
                )
                if best is None or c["clearance_m"] < best["clearance_m"]:
                    best = c
        else:
            for b in buildings:
                c = clearance_to_building(p["latitude"], p["longitude"], p["altitude"], b)
                if best is None or c["clearance_m"] < best["clearance_m"]:
                    best = c

        assert best is not None
        if best["penetrating"]:
            risk = 1.0
            penetrations += 1
        elif best["clearance_m"] <= 0:
            risk = 1.0
        else:
            risk = min(1.0, threshold_m / best["clearance_m"])

        if best["penetrating"] or best["clearance_m"] < threshold_m:
            at_risk += 1
        if best["clearance_m"] < min_clearance:
            min_clearance = best["clearance_m"]
            nearest_building = best["building_id"]

        samples.append(
            {
                "timestamp": p["timestamp"].isoformat()
                if hasattr(p["timestamp"], "isoformat")
                else str(p["timestamp"]),
                "clearance_m": float(best["clearance_m"]),
                "horizontal_m": float(best["horizontal_m"]),
                "risk": float(risk),
                "penetrating": bool(best["penetrating"]),
                "building_id": best["building_id"],
                "over_footprint": bool(best["over_footprint"]),
            }
        )

    # Ensure trajectory-level collisions are reflected in stats
    if collision_ids and penetrations == 0:
        penetrations = len(collision_ids)

    return {
        "aircraft_id": aircraft_id,
        "samples": samples,
        "min_clearance_m": float(min_clearance if min_clearance < float("inf") else 0.0),
        "time_at_risk_pct": float(at_risk / len(samples) * 100) if samples else 0.0,
        "penetration_count": penetrations,
        "nearest_building_id": nearest_building,
        "threshold_m": threshold_m,
        "buildings_checked": len(buildings),
        "trajectory_collisions": len(collision_ids),
        "trajectory_risk_buildings": len(risk_ids),
    }


def building_ids_at_risk(
    lat: float,
    lon: float,
    alt_m: float,
    threshold_m: float,
    buildings: Optional[list[Building]] = None,
) -> set[str]:
    buildings = buildings if buildings is not None else building_store.get().buildings
    hot: set[str] = set()
    for b in buildings:
        c = clearance_to_building(lat, lon, alt_m, b)
        if c["penetrating"] or c["clearance_m"] < threshold_m:
            hot.add(b.id)
    return hot
