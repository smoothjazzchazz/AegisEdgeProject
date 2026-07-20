"""Pairwise 3D distance and collision risk analysis."""
from __future__ import annotations

import numpy as np
import pandas as pd


def analyze_collision(
    df: pd.DataFrame,
    drone_a: str,
    drone_b: str,
    threshold_m: float = 100.0,
) -> dict:
    drone1 = df[df["aircraft_id"] == drone_a].copy().sort_values("timestamp")
    drone2 = df[df["aircraft_id"] == drone_b].copy().sort_values("timestamp")

    if drone1.empty or drone2.empty:
        raise ValueError("No data available for selected drone(s).")

    # Prefer exact timestamp matches; otherwise align with nearest asof merge
    common = pd.merge(drone1, drone2, on="timestamp", suffixes=("_1", "_2"))
    if common.empty:
        left = drone1.rename(
            columns={
                "latitude": "latitude_1",
                "longitude": "longitude_1",
                "altitude": "altitude_1",
                "heading": "heading_1",
                "aircraft_id": "aircraft_id_1",
            }
        )
        right = drone2.rename(
            columns={
                "latitude": "latitude_2",
                "longitude": "longitude_2",
                "altitude": "altitude_2",
                "heading": "heading_2",
                "aircraft_id": "aircraft_id_2",
            }
        )
        common = pd.merge_asof(
            left,
            right,
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("30s"),
        )
        common = common.dropna(subset=["latitude_2", "longitude_2", "altitude_2"])

    if common.empty:
        raise ValueError("No overlapping flight times found.")

    # Cleaner numbers + numpy utilizes SIMD
    lat1 = common["latitude_1"].to_numpy()
    lat2 = common["latitude_2"].to_numpy()
    lon1 = common["longitude_1"].to_numpy()
    lon2 = common["longitude_2"].to_numpy()
    alt1 = common["altitude_1"].to_numpy()
    alt2 = common["altitude_2"].to_numpy()
    dx = (lon1 - lon2) * 111320 * np.cos(np.radians(lat1))
    dy = (lat1 - lat2) * 111320
    dz = alt1 - alt2
    
    common["distance"] = np.sqrt(dx**2 + dy**2 + dz**2)

    common["collision_risk"] = (1 / (common["distance"] / threshold_m)).clip(0, 1)

    # Downsample long series for API payload size
    step = max(1, len(common) // 500)
    sampled = common.iloc[::step]

    samples = [
        {
            "timestamp": row["timestamp"].isoformat(),
            "distance_m": float(row["distance"]),
            "risk": float(row["collision_risk"]),
        }
        for _, row in sampled.iterrows()
    ]

    time_at_risk = float((common["distance"] < threshold_m).sum() / len(common) * 100)

    return {
        "samples": samples,
        "min_distance_m": float(common["distance"].min()),
        "avg_distance_m": float(common["distance"].mean()),
        "max_risk": float(common["collision_risk"].max()),
        "time_at_risk_pct": time_at_risk,
    }
