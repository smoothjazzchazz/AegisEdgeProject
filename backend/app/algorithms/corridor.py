"""Safe corridor / trajectory generation avoiding high-traffic zones and buildings."""
from __future__ import annotations

import math

import numpy as np
from scipy.interpolate import CubicSpline

from ..buildings.osm import building_store, clearance_to_building
from ..buildings.trajectory import segment_clearance_to_building
from .congestion import analyze_traffic_density


def find_safe_path(
    start_point: np.ndarray,
    end_point: np.ndarray,
    traffic_zones: list[dict],
    num_points: int = 100,
) -> np.ndarray:
    t = np.linspace(0, 1, num_points)
    path = np.array(
        [
            np.interp(t, [0, 1], [start_point[0], end_point[0]]),
            np.interp(t, [0, 1], [start_point[1], end_point[1]]),
            np.interp(t, [0, 1], [start_point[2], end_point[2]]),
        ]
    ).T

    safety_margin = 0.0005
    vertical_adjustment = 30
    max_deviation = 0.001

    direct_distance = np.linalg.norm(
        [
            (end_point[0] - start_point[0]) * 111320,
            (end_point[1] - start_point[1]) * 111320 * np.cos(np.radians(start_point[0])),
            end_point[2] - start_point[2],
        ]
    )

    for zone in traffic_zones:
        verts = np.array(zone["vertices"])
        zone_center = verts.mean(axis=0)
        base_influence = safety_margin * min(1 + zone["density"] / 20, 2.0)
        influence_radius = min(base_influence, max_deviation)

        for i in range(len(path)):
            dist_lat = abs(path[i, 0] - zone_center[0])
            dist_lon = abs(path[i, 1] - zone_center[1])
            dist_alt = abs(path[i, 2] - zone_center[2])

            original_point = np.array(
                [
                    np.interp(i / len(path), [0, 1], [start_point[0], end_point[0]]),
                    np.interp(i / len(path), [0, 1], [start_point[1], end_point[1]]),
                    np.interp(i / len(path), [0, 1], [start_point[2], end_point[2]]),
                ]
            )
            deviation = np.linalg.norm(path[i] - original_point)

            if (
                dist_lat < influence_radius
                and dist_lon < influence_radius
                and dist_alt < vertical_adjustment
                and deviation < max_deviation
            ):
                direction = path[i] - zone_center
                if not np.any(direction):
                    continue
                direction = direction / np.linalg.norm(direction)

                deviation_strength = (influence_radius - max(dist_lat, dist_lon)) / influence_radius
                deviation_strength = min(deviation_strength * 0.5, 0.3)

                path[i, 0] += direction[0] * deviation_strength * safety_margin
                path[i, 1] += direction[1] * deviation_strength * safety_margin

                if zone["density"] > 5:
                    if zone["avg_altitude"] > path[i, 2]:
                        path[i, 2] -= min(vertical_adjustment * deviation_strength, 20)
                    else:
                        path[i, 2] += min(vertical_adjustment * deviation_strength, 20)

    window_size = 5
    if len(path) >= window_size:
        path = np.array(
            [
                np.convolve(path[:, 0], np.ones(window_size) / window_size, mode="valid"),
                np.convolve(path[:, 1], np.ones(window_size) / window_size, mode="valid"),
                np.convolve(path[:, 2], np.ones(window_size) / window_size, mode="valid"),
            ]
        ).T

    optimized_distance = 0.0
    for i in range(1, len(path)):
        optimized_distance += np.linalg.norm(
            [
                (path[i, 0] - path[i - 1, 0]) * 111320,
                (path[i, 1] - path[i - 1, 1])
                * 111320
                * np.cos(np.radians(path[i - 1, 0])),
                path[i, 2] - path[i - 1, 2],
            ]
        )

    if optimized_distance > direct_distance * 1.5 and direct_distance > 0:
        path = 0.7 * path + 0.3 * np.array(
            [
                np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[0], end_point[0]]),
                np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[1], end_point[1]]),
                np.interp(np.linspace(0, 1, len(path)), [0, 1], [start_point[2], end_point[2]]),
            ]
        ).T

    return path


def _building_centroid(footprint: list[list[float]]) -> np.ndarray:
    arr = np.array(footprint)
    return arr.mean(axis=0)  # lat, lon


def deflect_from_buildings(
    path: np.ndarray,
    buffer_m: float = 25.0,
    roof_buffer_m: float = 25.0,
    passes: int = 4,
) -> tuple[np.ndarray, set[str]]:
    """
    Multi-pass deflection around OSM building prisms.
    Returns (path, ids of buildings that forced a maneuver).
    """
    buildings = building_store.get().buildings
    touched: set[str] = set()
    if not buildings:
        return path, touched

    out = path.copy()
    # ~meters to degrees at mid-lat
    mid_lat = float(np.mean(out[:, 0]))
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(mid_lat))

    for _ in range(passes):
        changed = False

        # Point-wise: climb or slide clear of solids / buffer
        for i in range(len(out)):
            lat, lon, alt = float(out[i, 0]), float(out[i, 1]), float(out[i, 2])
            for b in buildings:
                c = clearance_to_building(lat, lon, alt, b)
                need = (
                    c["penetrating"]
                    or c["clearance_m"] < buffer_m
                    or (c["over_footprint"] and alt < b.height_m + roof_buffer_m)
                )
                if not need:
                    continue
                touched.add(b.id)
                changed = True
                center = _building_centroid(b.footprint)
                # Prefer climb if already near/over footprint; else lateral then climb
                climb_alt = b.height_m + roof_buffer_m
                if c["over_footprint"] or c["horizontal_m"] < buffer_m * 0.5:
                    out[i, 2] = max(out[i, 2], climb_alt)
                else:
                    direction = np.array([lat - center[0], lon - center[1]])
                    norm = np.linalg.norm(direction)
                    if norm < 1e-12:
                        out[i, 2] = max(out[i, 2], climb_alt)
                    else:
                        direction = direction / norm
                        # Push out to ~buffer_m beyond wall
                        push_m = buffer_m - c["horizontal_m"] + 5.0
                        out[i, 0] += direction[0] * (push_m / m_per_deg_lat)
                        out[i, 1] += direction[1] * (push_m / m_per_deg_lon)
                        if alt < b.height_m:
                            out[i, 2] = max(out[i, 2], min(climb_alt, b.height_m + 5.0))

        # Segment-wise: if any edge still pierces a prism, raise both endpoints
        for i in range(len(out) - 1):
            a = out[i]
            bpt = out[i + 1]
            for b in buildings:
                c = segment_clearance_to_building(
                    float(a[0]), float(a[1]), float(a[2]),
                    float(bpt[0]), float(bpt[1]), float(bpt[2]),
                    b,
                )
                if c["penetrating"] or c["clearance_m"] < buffer_m:
                    touched.add(b.id)
                    changed = True
                    climb_alt = b.height_m + roof_buffer_m
                    out[i, 2] = max(out[i, 2], climb_alt)
                    out[i + 1, 2] = max(out[i + 1, 2], climb_alt)
                    # Slight lateral push at midpoint toward away from centroid
                    center = _building_centroid(b.footprint)
                    mid = 0.5 * (a + bpt)
                    direction = np.array([mid[0] - center[0], mid[1] - center[1]])
                    norm = np.linalg.norm(direction)
                    if norm > 1e-12:
                        direction = direction / norm
                        push = 15.0
                        out[i, 0] += direction[0] * (push / m_per_deg_lat) * 0.5
                        out[i, 1] += direction[1] * (push / m_per_deg_lon) * 0.5
                        out[i + 1, 0] += direction[0] * (push / m_per_deg_lat) * 0.5
                        out[i + 1, 1] += direction[1] * (push / m_per_deg_lon) * 0.5

        if not changed:
            break

    return out, touched


def count_buildings_on_path(path: np.ndarray, buffer_m: float = 25.0) -> set[str]:
    """Buildings that a path collides with or comes within buffer of."""
    buildings = building_store.get().buildings
    hit: set[str] = set()
    if not buildings or len(path) < 2:
        return hit
    for i in range(len(path) - 1):
        a, bpt = path[i], path[i + 1]
        for b in buildings:
            if b.id in hit:
                continue
            c = segment_clearance_to_building(
                float(a[0]), float(a[1]), float(a[2]),
                float(bpt[0]), float(bpt[1]), float(bpt[2]),
                b,
            )
            if c["penetrating"] or c["clearance_m"] < buffer_m:
                hit.add(b.id)
    return hit


def generate_safe_trajectory(
    start_point: np.ndarray,
    end_point: np.ndarray,
    traffic_zones: list[dict],
) -> tuple[np.ndarray, set[str]]:
    rough_path = find_safe_path(start_point, end_point, traffic_zones)
    rough_path, touched = deflect_from_buildings(rough_path)
    if len(rough_path) < 4:
        return rough_path, touched
    t = np.linspace(0, 1, len(rough_path))
    cs = CubicSpline(t, rough_path)
    t_fine = np.linspace(0, 1, 120)
    smooth = cs(t_fine)
    smooth, touched2 = deflect_from_buildings(smooth, passes=5)
    return smooth, touched | touched2


def path_length_km(path: np.ndarray) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(path)):
        total += np.linalg.norm(
            [
                (path[i, 0] - path[i - 1, 0]) * 111.32,
                (path[i, 1] - path[i - 1, 1])
                * 111.32
                * np.cos(np.radians(path[i - 1, 0])),
                (path[i, 2] - path[i - 1, 2]) / 1000.0,
            ]
        )
    return float(total)


def build_corridor(
    df,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    altitude_m: float,
    drone_ids: list[str] | None = None,
) -> dict:
    filtered = df
    if drone_ids:
        filtered = df[df["aircraft_id"].isin(drone_ids)]

    traffic_zones = analyze_traffic_density(filtered)
    start_point = np.array([start_lat, start_lon, altitude_m])
    end_point = np.array([end_lat, end_lon, altitude_m])

    t = np.linspace(0, 1, 50)
    direct_path = np.array(
        [
            np.interp(t, [0, 1], [start_point[0], end_point[0]]),
            np.interp(t, [0, 1], [start_point[1], end_point[1]]),
            np.interp(t, [0, 1], [start_point[2], end_point[2]]),
        ]
    ).T

    direct_building_hits = count_buildings_on_path(direct_path)
    optimized, touched = generate_safe_trajectory(start_point, end_point, traffic_zones)
    # Buildings avoided = those on the direct path that we maneuvered for
    buildings_avoided = len(direct_building_hits | touched)

    direct_length = path_length_km(direct_path)
    optimized_length = path_length_km(optimized)
    path_diff = (
        ((optimized_length - direct_length) / direct_length) * 100 if direct_length > 0 else 0.0
    )

    high_zones = [z for z in traffic_zones if z["density"] > 5]

    def to_points(arr: np.ndarray) -> list[dict]:
        return [
            {
                "latitude": float(p[0]),
                "longitude": float(p[1]),
                "altitude": float(p[2]),
            }
            for p in arr
        ]

    return {
        "direct_path": to_points(direct_path),
        "optimized_path": to_points(optimized),
        "zones": high_zones,
        "direct_length_km": direct_length,
        "optimized_length_km": optimized_length,
        "path_difference_pct": float(path_diff),
        "avg_altitude": float(np.mean(optimized[:, 2])),
        "risk_zones_avoided": len(high_zones),
        "buildings_avoided": buildings_avoided,
        "buildings_loaded": len(building_store.get().buildings),
    }
