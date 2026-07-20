"""WebSocket telemetry stream — replay ticks now, live-ready later."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..store import store

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    mode = "replay"
    speed = 1.0
    playing = False
    t_ms: float | None = None

    summary = store.fleet_summary()
    t_min = summary.get("t_min")
    t_max = summary.get("t_max")

    if t_min:
        t_ms = datetime.fromisoformat(t_min).timestamp() * 1000

    try:
        await websocket.send_json(
            {
                "type": "hello",
                "t_min": t_min,
                "t_max": t_max,
                "mode": mode,
            }
        )

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "subscribe":
                    mode = msg.get("mode", mode)
                    speed = float(msg.get("speed", speed))
                    playing = bool(msg.get("playing", playing))
                    if "t" in msg and msg["t"]:
                        t_ms = datetime.fromisoformat(msg["t"]).timestamp() * 1000
                elif mtype == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                raise
            except Exception:
                continue

            if mode == "live":
                # Placeholder for future live sim publisher
                await websocket.send_json(
                    {
                        "type": "tick",
                        "t": datetime.now(timezone.utc).isoformat(),
                        "positions": store.positions_at(
                            datetime.now(timezone.utc).isoformat()
                        ),
                        "mode": "live",
                        "note": "live_sim_not_connected",
                    }
                )
                await asyncio.sleep(1.0)
                continue

            # Replay mode
            if playing and t_min and t_max and t_ms is not None:
                t_max_ms = datetime.fromisoformat(t_max).timestamp() * 1000
                t_min_ms = datetime.fromisoformat(t_min).timestamp() * 1000
                # Advance ~100ms of wall clock * speed in sim time
                step_ms = 100.0 * speed
                t_ms = min(t_ms + step_ms, t_max_ms)
                t_iso = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).isoformat()
                await websocket.send_json(
                    {
                        "type": "tick",
                        "t": t_iso,
                        "positions": store.positions_at(t_iso),
                        "mode": "replay",
                    }
                )
                if t_ms >= t_max_ms:
                    playing = False
                    await websocket.send_json({"type": "ended", "t": t_iso})
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        return
