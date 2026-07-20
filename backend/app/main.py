"""AegisEdge ATC API — FastAPI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analysis, buildings, telemetry, ws
from .store import store

DEMO_CSV = Path(__file__).resolve().parent / "demo" / "demo_drone_data.csv"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if DEMO_CSV.exists():
        count = store.load_demo(str(DEMO_CSV))
        print(f"Loaded demo telemetry: {count} points")
    else:
        print(f"Warning: demo CSV not found at {DEMO_CSV}")
    yield


app = FastAPI(
    title="AegisEdge ATC",
    description="Drone air traffic control MVP API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry.router)
app.include_router(analysis.router)
app.include_router(buildings.router)
app.include_router(ws.router)


@app.get("/")
def root():
    return {"name": "AegisEdge ATC", "docs": "/docs"}
