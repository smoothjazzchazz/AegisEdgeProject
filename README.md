# AegisEdge ATC

Drone air-traffic control MVP: multi-aircraft 3D situational awareness, time replay, pairwise collision risk, congestion zones, and safe corridor generation.

**Stack:** React + Three.js + shadcn-style UI + Recharts (frontend) · FastAPI + NumPy/SciPy (backend)

The original Palantir Foundry / Dash prototype lives in [`legacy/`](legacy/) for reference and is not used at runtime.

## Quick start

From the repo root (Windows):

```powershell
.\quickstart.ps1
```

Or double-click / run `quickstart.bat`.
Or run `./quickstart.sh` on Linux/macOS.

That installs deps if needed and opens two terminals:

- API — http://127.0.0.1:8000 (docs at `/docs`)
- UI — http://127.0.0.1:5173

Stop everything:

```powershell
.\quickstart.ps1 -Stop
```
```bash
./quickstart.sh --stop
```
Skip reinstalls on subsequent runs:

```powershell
.\quickstart.ps1 -SkipInstall
```
```bash
./quickstart.sh --skip-install
```

### Manual

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npx vite --host 127.0.0.1 --port 5173
```

Demo CSV loads automatically from `backend/app/demo/demo_drone_data.csv`.
Vite proxies `/api` and `/ws` to the backend.

## Features

| Capability | Where |
|------------|--------|
| Fleet list + multi-select | Left rail |
| 3D trajectories / aircraft | Center Three.js viewport |
| Time replay (play / speed / scrub) | Bottom timeline |
| Altitude / heading / separation charts | Collapsible Recharts strip |
| Pairwise collision + threshold | Collision drawer |
| Safe corridor + risk zones | Corridor drawer |
| CSV upload / reload demo | Data drawer |
| WebSocket telemetry channel | `/ws/telemetry` (live-ready; UI uses local replay by default) |

## Telemetry CSV schema

```text
aircraft_id,timestamp,latitude,longitude,altitude,heading
PATROL01,2024-01-01T12:00:00Z,40.7829,-73.9654,150,90
```

## OSM buildings

Open the **Buildings** drawer → **Load buildings for airspace**. The API queries Overpass for OSM `building=*` ways in a padded bbox around current telemetry, estimates height from `height` / `building:levels` (default 12 m), and caches low-poly solids.

- Scene: extruded footprint meshes (steel gray; red when at-risk)
- **Analyze building risk**: clearance vs roof/walls for a selected aircraft
- Corridor generation also deflects/climbs to avoid loaded building solids

Requires outbound HTTPS to Overpass (`overpass-api.de` or fallback).


```bash
cd backend/app/demo
python generate_demo_data.py
```

Then hit **Reload demo dataset** in the Data drawer, or restart the API.

## WebSocket (future live)

Connect to `ws://127.0.0.1:8000/ws/telemetry`.

Client → server:

```json
{ "type": "subscribe", "mode": "replay" | "live", "playing": true, "speed": 2 }
```

Server → client:

```json
{
  "type": "tick",
  "t": "2024-01-01T12:05:00+00:00",
  "positions": [{ "aircraft_id": "PATROL01", "lat": 40.78, "lon": -73.96, "alt": 150, "heading": 90 }],
  "mode": "replay"
}
```

`mode: "live"` is stubbed for a future simulated publisher; the ops console already opens the socket via `useTelemetrySocket`.

## Project layout

```text
backend/app/          FastAPI app, algorithms, store, WS
frontend/src/         Ops console, Three.js scene, drawers
legacy/               Original Foundry Dash monolith
```
