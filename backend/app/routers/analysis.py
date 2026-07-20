"""Analysis routes: collision, congestion, corridor."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..algorithms.collision import analyze_collision
from ..algorithms.congestion import analyze_traffic_density
from ..algorithms.corridor import build_corridor
from ..models import (
    CollisionRequest,
    CollisionResponse,
    CongestionRequest,
    CongestionResponse,
    CorridorRequest,
    CorridorResponse,
)
from ..store import store

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/collision", response_model=CollisionResponse)
def collision(req: CollisionRequest) -> CollisionResponse:
    df = store.snapshot()
    try:
        result = analyze_collision(df, req.drone_a, req.drone_b, req.threshold_m)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CollisionResponse(**result)


@router.post("/congestion", response_model=CongestionResponse)
def congestion(req: CongestionRequest) -> CongestionResponse:
    df = store.snapshot()
    if req.drone_ids:
        df = df[df["aircraft_id"].isin(req.drone_ids)]
    zones = analyze_traffic_density(df, req.grid_size, req.density_threshold)
    return CongestionResponse(zones=zones)


@router.post("/corridor", response_model=CorridorResponse)
def corridor(req: CorridorRequest) -> CorridorResponse:
    df = store.snapshot()
    try:
        result = build_corridor(
            df,
            req.start.lat,
            req.start.lon,
            req.end.lat,
            req.end.lon,
            req.altitude_m,
            req.drone_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CorridorResponse(**result)
