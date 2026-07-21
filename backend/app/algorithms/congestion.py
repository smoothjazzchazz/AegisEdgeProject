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

    #Fast count across all grid cells (numpy histogramdd)
    points = df[["latitude", "longitude", "altitude"]].to_numpy()
    H, _ = np.histogramdd(points, bins=(lat_bins, lon_bins, alt_bins))
    
    # Fast point assignment per cell for average altitude calculation
    lat_indices = np.clip(np.digitize(df["latitude"], lat_bins) - 1, 0, grid_size - 2)
    lon_indices = np.clip(np.digitize(df["longitude"], lon_bins) - 1, 0, grid_size - 2)
    alt_indices = np.clip(np.digitize(df["altitude"], alt_bins) - 1, 0, grid_size - 2)
    
    # Group points by cell indices
    # Pandas .mean() is slower than numpy since it runs on Python and is single-threaded
    cell_keys = (
        lat_indices * (grid_size - 1) ** 2
        + lon_indices * (grid_size - 1)
        + alt_indices
    )
    alt_sums = np.bincount(cell_keys, weights=df["altitude"], minlength=(grid_size - 1) ** 3)
    
    traffic_zones: list[dict] = []

    # Iterate only through non-empty cells exceeding density threshold
    # Numpy uses C, so argwhere would be faster at finding empty cells
    active_indices = np.argwhere(H > density_threshold)

    # Triple for loop = 20 * 20 * 20 = 8000 iterations; not every cell is active, and G^3 scales poorly
    # Hopefully faster than O(N*G^3) where N is rows, G is grid size; Should be O(N+G^3) thanks to numpy histogramdd (C/Fortran)
    for i, j, k in active_indices:
        density = int(H[i, j, k])
        flat_idx = i * (grid_size - 1) ** 2 + j * (grid_size - 1) + k
        avg_alt = float(alt_sums[flat_idx] / density)

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
                "density": density,
                "avg_altitude": avg_alt,
            }
        )

    return traffic_zones
