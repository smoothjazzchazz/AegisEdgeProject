"""Telemetry REST routes: fleet, trajectories, upload, reload demo."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ..data_loader import load_csv_bytes
from ..models import FleetResponse, HealthResponse, TrajectoriesResponse, UploadResponse
from ..store import store

router = APIRouter(prefix="/api", tags=["telemetry"])

DEMO_CSV = Path(__file__).resolve().parent.parent / "demo" / "demo_drone_data.csv"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    summary = store.fleet_summary()
    return HealthResponse(
        status="ok",
        drones=len(summary["drones"]),
        points=summary["total_points"],
    )


@router.get("/fleet", response_model=FleetResponse)
def get_fleet() -> FleetResponse:
    return FleetResponse(**store.fleet_summary())


@router.get("/trajectories", response_model=TrajectoriesResponse)
def get_trajectories(
    ids: str | None = Query(default=None, description="Comma-separated aircraft IDs"),
    t0: str | None = None,
    t1: str | None = None,
    max_points: int = Query(default=15000, ge=100, le=100000),
) -> TrajectoriesResponse:
    id_list = [x.strip() for x in ids.split(",") if x.strip()] if ids else None
    result = store.trajectories(ids=id_list, t0=t0, t1=t1, max_points=max_points)
    return TrajectoriesResponse(**result)


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")
    content = await file.read()
    try:
        df = load_csv_bytes(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}") from e

    added = store.merge_dataframe(df)
    summary = store.fleet_summary()
    drones = sorted(df["aircraft_id"].astype(str).unique().tolist())
    return UploadResponse(
        success=True,
        message=f"Merged {added} records from {file.filename}",
        total_points=summary["total_points"],
        drones_added=drones,
        t_min=summary["t_min"],
        t_max=summary["t_max"],
    )


@router.post("/demo/reload", response_model=UploadResponse)
def reload_demo() -> UploadResponse:
    if not DEMO_CSV.exists():
        raise HTTPException(status_code=404, detail="Demo CSV not found.")
    store.clear()
    count = store.load_demo(str(DEMO_CSV))
    summary = store.fleet_summary()
    return UploadResponse(
        success=True,
        message=f"Loaded demo dataset ({count} points)",
        total_points=summary["total_points"],
        drones_added=[d["aircraft_id"] for d in summary["drones"]],
        t_min=summary["t_min"],
        t_max=summary["t_max"],
    )
