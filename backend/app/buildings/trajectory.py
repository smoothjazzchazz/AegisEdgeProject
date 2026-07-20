"""3D trajectory segment ∩ vertical building prism analysis."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .osm import Building


def _to_enu(lat: float, lon: float, alt: float, o_lat: float, o_lon: float) -> tuple[float, float, float]:
    cos = math.cos(math.radians(o_lat))
    return (
        (lon - o_lon) * 111320 * cos,
        (lat - o_lat) * 111320,
        alt,
    )


def _footprint_enu(ring: list[list[float]], o_lat: float, o_lon: float) -> list[tuple[float, float]]:
    cos = math.cos(math.radians(o_lat))
    pts = [((lon - o_lon) * 111320 * cos, (lat - o_lat) * 111320) for lat, lon in ring]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
        pts = pts[:-1]
    return pts


def _point_in_poly2(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        yi, xi = poly[i][1], poly[i][0]
        yj, xj = poly[j][1], poly[j][0]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def _seg_seg_t(
    ax: float, ay: float, bx: float, by: float,
    cx: float, cy: float, dx: float, dy: float,
) -> float | None:
    rx, ry = bx - ax, by - ay
    sx, sy = dx - cx, dy - cy
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    t = ((cx - ax) * sy - (cy - ay) * sx) / den
    u = ((cx - ax) * ry - (cy - ay) * rx) / den
    if t < -1e-9 or t > 1 + 1e-9 or u < -1e-9 or u > 1 + 1e-9:
        return None
    return max(0.0, min(1.0, t))


def _inside_intervals_2d(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    poly: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    ts = {0.0, 1.0}
    for i in range(len(poly)):
        p = poly[i]
        q = poly[(i + 1) % len(poly)]
        t = _seg_seg_t(a[0], a[1], b[0], b[1], p[0], p[1], q[0], q[1])
        if t is not None:
            ts.add(t)
    sorted_t = sorted(ts)
    intervals: list[tuple[float, float]] = []
    for i in range(len(sorted_t) - 1):
        t0, t1 = sorted_t[i], sorted_t[i + 1]
        if t1 - t0 < 1e-10:
            continue
        tm = (t0 + t1) / 2
        mx = a[0] + (b[0] - a[0]) * tm
        my = a[1] + (b[1] - a[1]) * tm
        if _point_in_poly2(mx, my, poly):
            if intervals and abs(intervals[-1][1] - t0) < 1e-9:
                intervals[-1] = (intervals[-1][0], t1)
            else:
                intervals.append((t0, t1))
    return intervals


def _ranges_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    lo_a, hi_a = min(a0, a1), max(a0, a1)
    lo_b, hi_b = min(b0, b1), max(b0, b1)
    return lo_a <= hi_b + 1e-6 and lo_b <= hi_a + 1e-6


def segment_intersects_prism(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    poly: list[tuple[float, float]],
    height: float,
) -> bool:
    if len(poly) < 3:
        return False
    h = max(height, 0.1)

    for p in (a, b):
        if 0 <= p[2] <= h and _point_in_poly2(p[0], p[1], poly):
            return True

    if abs(b[2] - a[2]) > 1e-9:
        for z_plane in (h, 0.0):
            t = (z_plane - a[2]) / (b[2] - a[2])
            if 0 <= t <= 1:
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t
                if _point_in_poly2(x, y, poly):
                    return True

    for t0, t1 in _inside_intervals_2d(a, b, poly):
        z0 = a[2] + (b[2] - a[2]) * t0
        z1 = a[2] + (b[2] - a[2]) * t1
        if _ranges_overlap(z0, z1, 0.0, h):
            return True
    return False


def _dist_point_seg2(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> tuple[float, float]:
    abx, aby = bx - ax, by - ay
    ab2 = abx * abx + aby * aby
    if ab2 < 1e-12:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / ab2))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby)), t


def _dist_point_poly2(x: float, y: float, poly: list[tuple[float, float]]) -> float:
    if _point_in_poly2(x, y, poly):
        return 0.0
    best = float("inf")
    for i in range(len(poly)):
        p = poly[i]
        q = poly[(i + 1) % len(poly)]
        d, _ = _dist_point_seg2(x, y, p[0], p[1], q[0], q[1])
        best = min(best, d)
    return best


def _min_dist_seg_poly2(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    poly: list[tuple[float, float]],
) -> tuple[float, float]:
    if _point_in_poly2(a[0], a[1], poly) or _point_in_poly2(b[0], b[1], poly):
        return 0.0, 0.0 if _point_in_poly2(a[0], a[1], poly) else 1.0
    if _inside_intervals_2d(a, b, poly):
        return 0.0, 0.5

    best = float("inf")
    best_t = 0.0
    for p in poly:
        d, t = _dist_point_seg2(p[0], p[1], a[0], a[1], b[0], b[1])
        if d < best:
            best, best_t = d, t
    for x, y, t in ((a[0], a[1], 0.0), (b[0], b[1], 1.0)):
        d = _dist_point_poly2(x, y, poly)
        if d < best:
            best, best_t = d, t
    for i in range(len(poly)):
        p = poly[i]
        q = poly[(i + 1) % len(poly)]
        t_hit = _seg_seg_t(a[0], a[1], b[0], b[1], p[0], p[1], q[0], q[1])
        if t_hit is not None:
            return 0.0, t_hit
    return best, best_t


def segment_clearance_to_building(
    a_lat: float,
    a_lon: float,
    a_alt: float,
    b_lat: float,
    b_lon: float,
    b_alt: float,
    building: "Building",
) -> dict:
    from .osm import clearance_to_building

    o_lat = (a_lat + b_lat) / 2
    o_lon = (a_lon + b_lon) / 2
    a = _to_enu(a_lat, a_lon, a_alt, o_lat, o_lon)
    b = _to_enu(b_lat, b_lon, b_alt, o_lat, o_lon)
    poly = _footprint_enu(building.footprint, o_lat, o_lon)
    h = building.height_m

    if segment_intersects_prism(a, b, poly, h):
        return {
            "building_id": building.id,
            "horizontal_m": 0.0,
            "roof_m": h,
            "altitude_m": (a_alt + b_alt) / 2,
            "clearance_m": 0.0,
            "penetrating": True,
            "over_footprint": True,
        }

    ts = {0.0, 1.0}
    if abs(b[2] - a[2]) > 1e-9:
        for z_plane in (h, 0.0):
            t = (z_plane - a[2]) / (b[2] - a[2])
            if 0.0 < t < 1.0:
                ts.add(t)
    _, t_closest = _min_dist_seg_poly2(a, b, poly)
    ts.add(t_closest)
    for i in range(len(poly)):
        p = poly[i]
        q = poly[(i + 1) % len(poly)]
        t = _seg_seg_t(a[0], a[1], b[0], b[1], p[0], p[1], q[0], q[1])
        if t is not None:
            ts.add(t)

    best = None
    for t in ts:
        lat = a_lat + (b_lat - a_lat) * t
        lon = a_lon + (b_lon - a_lon) * t
        alt = a_alt + (b_alt - a_alt) * t
        c = clearance_to_building(lat, lon, alt, building)
        if best is None or c["clearance_m"] < best["clearance_m"]:
            best = c
    return best or {
        "building_id": building.id,
        "horizontal_m": 0.0,
        "roof_m": h,
        "altitude_m": a_alt,
        "clearance_m": float("inf"),
        "penetrating": False,
        "over_footprint": False,
    }


def classify_trajectory_buildings(
    samples: list[dict],
    buildings: list["Building"],
    threshold_m: float,
) -> tuple[set[str], set[str]]:
    """Return (collision_ids, risk_ids) via segment∩prism analysis."""
    collision: set[str] = set()
    risk: set[str] = set()
    if not samples or not buildings:
        return collision, risk

    from .osm import clearance_to_building

    if len(samples) == 1:
        p = samples[0]
        for b in buildings:
            c = clearance_to_building(p["latitude"], p["longitude"], p["altitude"], b)
            if c["penetrating"]:
                collision.add(b.id)
            elif c["clearance_m"] < threshold_m:
                risk.add(b.id)
        risk -= collision
        return collision, risk

    for b in buildings:
        ever = False
        min_c = float("inf")
        for i in range(len(samples) - 1):
            a = samples[i]
            nxt = samples[i + 1]
            c = segment_clearance_to_building(
                a["latitude"], a["longitude"], a["altitude"],
                nxt["latitude"], nxt["longitude"], nxt["altitude"],
                b,
            )
            if c["penetrating"]:
                ever = True
                break
            min_c = min(min_c, c["clearance_m"])
        if ever:
            collision.add(b.id)
        elif min_c < threshold_m:
            risk.add(b.id)

    risk -= collision
    return collision, risk
