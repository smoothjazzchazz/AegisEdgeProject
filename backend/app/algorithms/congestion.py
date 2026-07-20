"""Grid-based airspace traffic density / congestion analysis."""
from __future__ import annotations

import numpy as np
import pandas as pd


def analyze_traffic_density(
    df: pd.DataFrame,
    grid_size: int = 20,
    density_threshold: int = 3,
) -> list[dict]:
    if df.empty:
        return []

    lat_min, lat_max = df["latitude"].min(), df["latitude"].max()
    lon_min, lon_max = df["longitude"].min(), df["longitude"].max()
    alt_min, alt_max = df["altitude"].min(), df["altitude"].max()

    # Avoid zero-width bins when all points share a coordinate
    if lat_max == lat_min:
        lat_max = lat_min + 0.001
    if lon_max == lon_min:
        lon_max = lon_min + 0.001
    if alt_max == alt_min:
        alt_max = alt_min + 10.0

    lat_bins = np.linspace(lat_min, lat_max, grid_size)
    lon_bins = np.linspace(lon_min, lon_max, grid_size)
    alt_bins = np.linspace(alt_min, alt_max, grid_size)

    traffic_zones: list[dict] = []

    for i in range(len(lat_bins) - 1):
        for j in range(len(lon_bins) - 1):
            for k in range(len(alt_bins) - 1):
                mask = (
                    (df["latitude"] >= lat_bins[i])
                    & (df["latitude"] < lat_bins[i + 1])
                    & (df["longitude"] >= lon_bins[j])
                    & (df["longitude"] < lon_bins[j + 1])
                    & (df["altitude"] >= alt_bins[k])
                    & (df["altitude"] < alt_bins[k + 1])
                )
                points_in_cell = df[mask]
                if len(points_in_cell) > density_threshold:
                    vertices = [
                        [float(lat_bins[i]), float(lon_bins[j]), float(alt_bins[k])],
                        [float(lat_bins[i + 1]), float(lon_bins[j]), float(alt_bins[k])],
                        [float(lat_bins[i]), float(lon_bins[j + 1]), float(alt_bins[k])],
                        [float(lat_bins[i + 1]), float(lon_bins[j + 1]), float(alt_bins[k])],
                        [float(lat_bins[i]), float(lon_bins[j]), float(alt_bins[k + 1])],
                        [float(lat_bins[i + 1]), float(lon_bins[j]), float(alt_bins[k + 1])],
                        [float(lat_bins[i]), float(lon_bins[j + 1]), float(alt_bins[k + 1])],
                        [float(lat_bins[i + 1]), float(lon_bins[j + 1]), float(alt_bins[k + 1])],
                    ]
                    traffic_zones.append(
                        {
                            "vertices": vertices,
                            "density": int(len(points_in_cell)),
                            "avg_altitude": float(points_in_cell["altitude"].mean()),
                        }
                    )

    return traffic_zones
