"""Fetch and cache OpenStreetMap building footprints via Overpass."""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

DEFAULT_LEVEL_HEIGHT_M = 3.5
DEFAULT_BUILDING_HEIGHT_M = 12.0
MAX_BUILDINGS = 400


@dataclass
class Building:
    id: str
    footprint: list[list[float]]  # [[lat, lon], ...] closed ring
    height_m: float
    name: Optional[str] = None
    levels: Optional[float] = None


@dataclass
class BuildingCache:
    buildings: list[Building] = field(default_factory=list)
    bbox: Optional[tuple[float, float, float, float]] = None  # south, west, north, east
    source: str = "none"


class BuildingStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cache = BuildingCache()

    def clear(self) -> None:
        with self._lock:
            self._cache = BuildingCache()

    def get(self) -> BuildingCache:
        with self._lock:
            return BuildingCache(
                buildings=list(self._cache.buildings),
                bbox=self._cache.bbox,
                source=self._cache.source,
            )

    def set(self, buildings: list[Building], bbox: tuple[float, float, float, float], source: str) -> None:
        with self._lock:
            self._cache = BuildingCache(buildings=buildings, bbox=bbox, source=source)

    def to_dicts(self) -> list[dict]:
        cache = self.get()
        return [
            {
                "id": b.id,
                "footprint": b.footprint,
                "height_m": b.height_m,
                "name": b.name,
                "levels": b.levels,
            }
            for b in cache.buildings
        ]


building_store = BuildingStore()


def estimate_height(tags: dict) -> tuple[float, Optional[float]]:
    levels: Optional[float] = None
    if "building:levels" in tags:
        try:
            levels = float(str(tags["building:levels"]).split(";")[0])
        except ValueError:
            levels = None

    if "height" in tags:
        raw = str(tags["height"]).lower().replace("m", "").strip()
        try:
            # take first number (ignore ranges like 10-12)
            num = "".join(ch if ch in "0123456789." else " " for ch in raw).split()
            if num:
                return float(num[0]), levels
        except ValueError:
            pass

    if levels is not None and levels > 0:
        return levels * DEFAULT_LEVEL_HEIGHT_M, levels

    return DEFAULT_BUILDING_HEIGHT_M, levels


def _ring_area_approx(ring: list[list[float]]) -> float:
    """Shoelace in degrees — for sorting/filtering only."""
    if len(ring) < 3:
        return 0.0
    a = 0.0
    for i in range(len(ring) - 1):
        a += ring[i][1] * ring[i + 1][0] - ring[i + 1][1] * ring[i][0]
    return abs(a) * 0.5


def parse_overpass(data: dict) -> list[Building]:
    elements = data.get("elements", [])
    nodes: dict[int, tuple[float, float]] = {}
    ways: list[dict] = []

    for el in elements:
        if el.get("type") == "node":
            nodes[el["id"]] = (float(el["lat"]), float(el["lon"]))
        elif el.get("type") == "way" and "nodes" in el:
            ways.append(el)

    buildings: list[Building] = []
    for way in ways:
        tags = way.get("tags") or {}
        if "building" not in tags:
            continue
        ring: list[list[float]] = []
        for nid in way["nodes"]:
            if nid not in nodes:
                continue
            lat, lon = nodes[nid]
            ring.append([lat, lon])
        if len(ring) < 3:
            continue
        if ring[0] != ring[-1]:
            ring.append(ring[0][:])
        height, levels = estimate_height(tags)
        buildings.append(
            Building(
                id=f"way/{way['id']}",
                footprint=ring,
                height_m=height,
                name=tags.get("name"),
                levels=levels,
            )
        )

    # Prefer larger footprints; cap count for scene performance
    buildings.sort(key=lambda b: _ring_area_approx(b.footprint), reverse=True)
    return buildings[:MAX_BUILDINGS]


def fetch_buildings_bbox(
    south: float,
    west: float,
    north: float,
    east: float,
) -> list[Building]:
    # Clamp tiny pads so Overpass always has a valid box
    if north <= south:
        north = south + 0.002
    if east <= west:
        east = west + 0.002

    query = f"""
    [out:json][timeout:45];
    (
      way["building"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_err: Exception | None = None

    for url in OVERPASS_URLS:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "AegisEdgeATC/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return parse_overpass(payload)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            continue

    raise RuntimeError(f"Overpass fetch failed: {last_err}")


def bbox_from_points(lats: list[float], lons: list[float], pad_deg: float = 0.003) -> tuple[float, float, float, float]:
    south = min(lats) - pad_deg
    north = max(lats) + pad_deg
    west = min(lons) - pad_deg
    east = max(lons) + pad_deg
    return south, west, north, east


def point_in_ring(lat: float, lon: float, ring: list[list[float]]) -> bool:
    """Ray casting; ring is [[lat, lon], ...]."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        yi, xi = ring[i][0], ring[i][1]
        yj, xj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def horizontal_distance_m(lat: float, lon: float, ring: list[list[float]]) -> float:
    """Min distance from point to polygon edge (or 0 if inside)."""
    if point_in_ring(lat, lon, ring):
        return 0.0

    cos_lat = math.cos(math.radians(lat))
    best = float("inf")
    for i in range(len(ring) - 1):
        a_lat, a_lon = ring[i]
        b_lat, b_lon = ring[i + 1]
        # Local meters
        ax = (a_lon - lon) * 111320 * cos_lat
        ay = (a_lat - lat) * 111320
        bx = (b_lon - lon) * 111320 * cos_lat
        by = (b_lat - lat) * 111320
        abx, aby = bx - ax, by - ay
        ab2 = abx * abx + aby * aby
        if ab2 < 1e-9:
            dist = math.hypot(ax, ay)
        else:
            t = max(0.0, min(1.0, (-ax * abx - ay * aby) / ab2))
            cx = ax + t * abx
            cy = ay + t * aby
            dist = math.hypot(cx, cy)
        if dist < best:
            best = dist
    return best if best < float("inf") else 0.0


def clearance_to_building(
    lat: float,
    lon: float,
    alt_m: float,
    building: Building,
) -> dict:
    """
    Distance to vertical prism (footprint × [0, roof_m]).
    Negative clearance means the sample is inside the solid.
    """
    horiz = horizontal_distance_m(lat, lon, building.footprint)
    roof = building.height_m
    over = horiz <= 0.5
    below_roof = alt_m < roof
    above_roof = alt_m >= roof

    penetrating = False
    if over:
        if alt_m < 0:
            clearance = -alt_m
            penetrating = True
        elif below_roof:
            clearance = alt_m - roof
            penetrating = True
        else:
            clearance = alt_m - roof
    elif alt_m >= 0 and below_roof:
        clearance = horiz
    elif above_roof:
        clearance = math.hypot(horiz, alt_m - roof)
    else:
        clearance = math.hypot(horiz, -alt_m)
        penetrating = alt_m < 0

    return {
        "building_id": building.id,
        "horizontal_m": horiz,
        "roof_m": roof,
        "altitude_m": alt_m,
        "clearance_m": float(clearance),
        "penetrating": penetrating,
        "over_footprint": over,
    }
