"""In-memory telemetry store for the ATC MVP."""
from __future__ import annotations

from threading import Lock
from typing import Optional

import pandas as pd

from .data_loader import dataframe_to_records, load_csv_path, process_dataframe


class TelemetryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._df = pd.DataFrame(
            columns=["aircraft_id", "timestamp", "latitude", "longitude", "altitude", "heading"]
        )

    def clear(self) -> None:
        with self._lock:
            self._df = pd.DataFrame(
                columns=["aircraft_id", "timestamp", "latitude", "longitude", "altitude", "heading"]
            )

    def load_demo(self, path: str) -> int:
        df = load_csv_path(path)
        with self._lock:
            self._df = df
        return len(df)

    def merge_dataframe(self, df: pd.DataFrame) -> int:
        clean = process_dataframe(df) if "timestamp" in df.columns else df
        with self._lock:
            if self._df.empty:
                self._df = clean
            else:
                self._df = pd.concat([self._df, clean], ignore_index=True)
                self._df.sort_values(by="timestamp", inplace=True)
                self._df.reset_index(drop=True, inplace=True)
            return len(clean)

    def snapshot(self) -> pd.DataFrame:
        with self._lock:
            return self._df.copy()

    def drone_ids(self) -> list[str]:
        df = self.snapshot()
        if df.empty:
            return []
        return sorted(df["aircraft_id"].astype(str).unique().tolist())

    def fleet_summary(self) -> dict:
        df = self.snapshot()
        if df.empty:
            return {"drones": [], "t_min": None, "t_max": None, "total_points": 0}

        drones = []
        for drone_id, group in df.groupby("aircraft_id"):
            drones.append(
                {
                    "aircraft_id": str(drone_id),
                    "point_count": int(len(group)),
                    "t_min": group["timestamp"].min().isoformat(),
                    "t_max": group["timestamp"].max().isoformat(),
                    "alt_min": float(group["altitude"].min()),
                    "alt_max": float(group["altitude"].max()),
                    "alt_avg": float(group["altitude"].mean()),
                }
            )
        drones.sort(key=lambda d: d["aircraft_id"])
        return {
            "drones": drones,
            "t_min": df["timestamp"].min().isoformat(),
            "t_max": df["timestamp"].max().isoformat(),
            "total_points": int(len(df)),
        }

    def trajectories(
        self,
        ids: Optional[list[str]] = None,
        t0: Optional[str] = None,
        t1: Optional[str] = None,
        max_points: int = 15000,
    ) -> dict:
        df = self.snapshot()
        if df.empty:
            return {"points": [], "sampled": False, "total_before_sample": 0}

        if ids:
            df = df[df["aircraft_id"].isin(ids)]
        if t0:
            df = df[df["timestamp"] >= pd.to_datetime(t0, utc=True)]
        if t1:
            df = df[df["timestamp"] <= pd.to_datetime(t1, utc=True)]

        total = len(df)
        sampled = False
        if total > max_points:
            step = max(1, total // max_points)
            df = df.iloc[::step]
            sampled = True

        return {
            "points": dataframe_to_records(df),
            "sampled": sampled,
            "total_before_sample": total,
        }

    def positions_at(self, t_iso: str) -> list[dict]:
        """Nearest sample per aircraft at or before timestamp t."""
        df = self.snapshot()
        if df.empty:
            return []
        t = pd.to_datetime(t_iso, utc=True)
        positions = []
        for drone_id, group in df.groupby("aircraft_id"):
            prior = group[group["timestamp"] <= t]
            row = prior.iloc[-1] if not prior.empty else group.iloc[0]
            positions.append(
                {
                    "aircraft_id": str(drone_id),
                    "lat": float(row["latitude"]),
                    "lon": float(row["longitude"]),
                    "alt": float(row["altitude"]),
                    "heading": float(row["heading"]) if pd.notna(row["heading"]) else 0.0,
                }
            )
        return positions


store = TelemetryStore()
