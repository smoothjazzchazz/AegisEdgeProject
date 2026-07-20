"""
Benchmark Comparison: Original vs Optimized Congestion
"""
# I copy-pasted the entire congestion/collision files that I changed and put the original ones here for comparison

from __future__ import annotations
import time
import numpy as np
import pandas as pd

# Original

def original_analyze_traffic_density(
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

def original_analyze_collision(
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

    common["distance"] = np.sqrt(
        (
            (common["longitude_1"] - common["longitude_2"])
            * 111320
            * np.cos(np.radians(common["latitude_1"]))
        )
        ** 2
        + ((common["latitude_1"] - common["latitude_2"]) * 111320) ** 2
        + (common["altitude_1"] - common["altitude_2"]) ** 2
    )

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
    
# Optimized

def new_analyze_collision(
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

def new_analyze_traffic_density(
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

# Syntethic benchmark data

def generate_mock_drone_data(num_points: int) -> pd.DataFrame:
    np.random.seed(42)
    timestamps = pd.date_range("2026-01-01", periods=num_points, freq="1s")

    data1 = {
        "timestamp": timestamps,
        "aircraft_id": "DRONE_A",
        "latitude": 37.7749 + np.cumsum(np.random.normal(0, 0.0001, num_points)),
        "longitude": -122.4194 + np.cumsum(np.random.normal(0, 0.0001, num_points)),
        "altitude": 100 + np.cumsum(np.random.normal(0, 0.5, num_points)),
        "heading": np.random.uniform(0, 360, num_points),
    }

    data2 = {
        "timestamp": timestamps,
        "aircraft_id": "DRONE_B",
        "latitude": 37.7750 + np.cumsum(np.random.normal(0, 0.0001, num_points)),
        "longitude": -122.4195 + np.cumsum(np.random.normal(0, 0.0001, num_points)),
        "altitude": 105 + np.cumsum(np.random.normal(0, 0.5, num_points)),
        "heading": np.random.uniform(0, 360, num_points),
    }

    df1 = pd.DataFrame(data1)
    df2 = pd.DataFrame(data2)
    return pd.concat([df1, df2], ignore_index=True)


def run_combined_benchmark():
    row_counts = [1000, 5000, 20000]
    grid_sizes = [10, 20, 35]
    iterations = 3

    print(
        f"{'Task':<16} | {'Rows':<7} | {'Grid Size':<9} | {'Cells':<7} | "
        f"{'Original (s)':<13} | {'Optimized (s)':<13} | {'Speedup':<8}"
    )
    print("-" * 88)

    for n in row_counts:
        df = generate_mock_drone_data(num_points=n)

        start = time.perf_counter()
        for _ in range(iterations):
            original_analyze_collision(df, "DRONE_A", "DRONE_B")
        orig_collision = (time.perf_counter() - start) / iterations

        start = time.perf_counter()
        for _ in range(iterations):
            new_analyze_collision(df, "DRONE_A", "DRONE_B")
        opt_collision = (time.perf_counter() - start) / iterations

        collision_speedup = orig_collision / opt_collision if opt_collision > 0 else 0
        print(
            f"{'Collision Risk':<16} | {n:<7} | {'N/A':<9} | {'N/A':<7} | "
            f"{orig_collision:<13.4f} | {opt_collision:<13.4f} | {collision_speedup:<8.1f}x"
        )

        for g in grid_sizes:
            total_cells = (g - 1) ** 3

            start = time.perf_counter()
            for _ in range(iterations):
                original_analyze_traffic_density(df, grid_size=g)
            orig_density = (time.perf_counter() - start) / iterations

            start = time.perf_counter()
            for _ in range(iterations):
                new_analyze_traffic_density(df, grid_size=g)
            opt_density = (time.perf_counter() - start) / iterations

            density_speedup = orig_density / opt_density if opt_density > 0 else 0
            print(
                f"{'Traffic Density':<16} | {n:<7} | {g:<9} | {total_cells:<7} | "
                f"{orig_density:<13.4f} | {opt_density:<13.4f} | {density_speedup:<8.1f}x"
            )
        print("-" * 88)


if __name__ == "__main__":
    run_combined_benchmark()