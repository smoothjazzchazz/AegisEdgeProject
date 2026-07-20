"""Pydantic schemas for AegisEdge ATC API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    aircraft_id: str
    timestamp: str
    latitude: float
    longitude: float
    altitude: float
    heading: float


class DroneSummary(BaseModel):
    aircraft_id: str
    point_count: int
    t_min: str
    t_max: str
    alt_min: float
    alt_max: float
    alt_avg: float


class FleetResponse(BaseModel):
    drones: list[DroneSummary]
    t_min: Optional[str] = None
    t_max: Optional[str] = None
    total_points: int = 0


class TrajectoriesResponse(BaseModel):
    points: list[TelemetryPoint]
    sampled: bool = False
    total_before_sample: int = 0


class LatLon(BaseModel):
    lat: float
    lon: float


class CollisionRequest(BaseModel):
    drone_a: str
    drone_b: str
    threshold_m: float = Field(default=100.0, ge=1.0, le=5000.0)


class CollisionSample(BaseModel):
    timestamp: str
    distance_m: float
    risk: float


class CollisionResponse(BaseModel):
    samples: list[CollisionSample]
    min_distance_m: float
    avg_distance_m: float
    max_risk: float
    time_at_risk_pct: float


class CongestionRequest(BaseModel):
    drone_ids: Optional[list[str]] = None
    grid_size: int = Field(default=20, ge=5, le=50)
    density_threshold: int = Field(default=3, ge=1)


class RiskZone(BaseModel):
    vertices: list[list[float]]  # [lat, lon, alt] x 8
    density: int
    avg_altitude: float


class CongestionResponse(BaseModel):
    zones: list[RiskZone]


class CorridorRequest(BaseModel):
    start: LatLon
    end: LatLon
    altitude_m: float = 100.0
    drone_ids: Optional[list[str]] = None


class PathPoint(BaseModel):
    latitude: float
    longitude: float
    altitude: float


class CorridorResponse(BaseModel):
    direct_path: list[PathPoint]
    optimized_path: list[PathPoint]
    zones: list[RiskZone]
    direct_length_km: float
    optimized_length_km: float
    path_difference_pct: float
    avg_altitude: float
    risk_zones_avoided: int
    buildings_avoided: int = 0
    buildings_loaded: int = 0


class UploadResponse(BaseModel):
    success: bool
    message: str
    total_points: int
    drones_added: list[str]
    t_min: Optional[str] = None
    t_max: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    drones: int
    points: int


class Building(BaseModel):
    id: str
    footprint: list[list[float]]  # [[lat, lon], ...]
    height_m: float
    name: Optional[str] = None
    levels: Optional[float] = None


class BuildingsResponse(BaseModel):
    buildings: list[Building]
    count: int
    bbox: Optional[list[float]] = None  # [south, west, north, east]
    source: str = "none"


class BuildingsLoadRequest(BaseModel):
    pad_deg: float = Field(default=0.004, ge=0.001, le=0.05)
    south: Optional[float] = None
    west: Optional[float] = None
    north: Optional[float] = None
    east: Optional[float] = None


class BuildingRiskRequest(BaseModel):
    aircraft_id: str
    threshold_m: float = Field(default=30.0, ge=1.0, le=500.0)


class BuildingRiskSample(BaseModel):
    timestamp: str
    clearance_m: float
    horizontal_m: float
    risk: float
    penetrating: bool
    building_id: str
    over_footprint: bool


class BuildingRiskResponse(BaseModel):
    aircraft_id: str
    samples: list[BuildingRiskSample]
    min_clearance_m: float
    time_at_risk_pct: float
    penetration_count: int
    nearest_building_id: Optional[str] = None
    threshold_m: float
    buildings_checked: int
    trajectory_collisions: int = 0
    trajectory_risk_buildings: int = 0
