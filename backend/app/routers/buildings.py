"""OSM building load + building-risk analysis routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..algorithms.building_risk import analyze_building_risk
from ..buildings.osm import (
    bbox_from_points,
    building_store,
    fetch_buildings_bbox,
)
from ..models import (
    BuildingRiskRequest,
    BuildingRiskResponse,
    BuildingsLoadRequest,
    BuildingsResponse,
)
from ..store import store

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


@router.get("", response_model=BuildingsResponse)
def get_buildings() -> BuildingsResponse:
    cache = building_store.get()
    return BuildingsResponse(
        buildings=building_store.to_dicts(),
        count=len(cache.buildings),
        bbox=list(cache.bbox) if cache.bbox else None,
        source=cache.source,
    )


@router.post("/load", response_model=BuildingsResponse)
def load_buildings(req: BuildingsLoadRequest) -> BuildingsResponse:
    df = store.snapshot()

    if None not in (req.south, req.west, req.north, req.east):
        bbox = (float(req.south), float(req.west), float(req.north), float(req.east))
    elif not df.empty:
        bbox = bbox_from_points(
            df["latitude"].astype(float).tolist(),
            df["longitude"].astype(float).tolist(),
            pad_deg=req.pad_deg,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="No telemetry loaded and no explicit bbox provided.",
        )

    try:
        buildings = fetch_buildings_bbox(*bbox)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    building_store.set(buildings, bbox, source="overpass")
    return BuildingsResponse(
        buildings=building_store.to_dicts(),
        count=len(buildings),
        bbox=list(bbox),
        source="overpass",
    )


@router.delete("", response_model=BuildingsResponse)
def clear_buildings() -> BuildingsResponse:
    building_store.clear()
    return BuildingsResponse(buildings=[], count=0, bbox=None, source="none")


@router.post("/risk", response_model=BuildingRiskResponse)
def building_risk(req: BuildingRiskRequest) -> BuildingRiskResponse:
    df = store.snapshot()
    try:
        result = analyze_building_risk(df, req.aircraft_id, req.threshold_m)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return BuildingRiskResponse(**result)
