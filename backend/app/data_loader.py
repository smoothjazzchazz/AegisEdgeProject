"""CSV parsing and telemetry validation."""
from __future__ import annotations

from io import StringIO
from typing import Union

import pandas as pd

REQUIRED_COLUMNS = [
    "aircraft_id",
    "timestamp",
    "latitude",
    "longitude",
    "altitude",
    "heading",
]


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize timestamps and drop incomplete rows."""
    df = df.copy()

    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].apply(
            lambda x: x.get("timestamp") if isinstance(x, dict) and "timestamp" in x else x
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    clean = df[REQUIRED_COLUMNS].dropna(
        subset=["aircraft_id", "latitude", "longitude", "altitude"]
    ).copy()
    clean.sort_values(by="timestamp", inplace=True)
    clean.reset_index(drop=True, inplace=True)
    return clean


def load_csv_bytes(content: Union[bytes, str]) -> pd.DataFrame:
    if isinstance(content, bytes):
        text = content.decode("utf-8")
    else:
        text = content
    df = pd.read_csv(StringIO(text))
    return process_dataframe(df)


def load_csv_path(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return process_dataframe(df)


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        ts = row["timestamp"]
        if pd.isna(ts):
            continue
        records.append(
            {
                "aircraft_id": str(row["aircraft_id"]),
                "timestamp": ts.isoformat(),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "altitude": float(row["altitude"]),
                "heading": float(row["heading"]) if pd.notna(row["heading"]) else 0.0,
            }
        )
    return records
