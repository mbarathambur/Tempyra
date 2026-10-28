"""SQLite persistence for disaster records used by the Tempyra prototype."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tempyra.db"
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "disasters.csv"
REQUIRED_COLUMNS = (
    "disaster_id",
    "location",
    "disaster_type",
    "severity",
    "affected_people",
    "latitude",
    "longitude",
    "status",
)
VALID_SEVERITIES = {"High", "Medium", "Low"}
VALID_STATUSES = {"Active", "Monitoring", "Resolved"}


class DisasterStoreError(ValueError):
    """Raised when a disaster record cannot safely be stored."""


def _validate_record(record: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_COLUMNS if key not in record]
    if missing:
        raise DisasterStoreError(f"Missing required fields: {', '.join(missing)}")

    normalized = {key: record[key] for key in REQUIRED_COLUMNS}
    for key in ("disaster_id", "location", "disaster_type"):
        normalized[key] = str(normalized[key]).strip()
        if not normalized[key]:
            raise DisasterStoreError(f"{key.replace('_', ' ').title()} cannot be empty.")

    normalized["severity"] = str(normalized["severity"]).strip().title()
    normalized["status"] = str(normalized["status"]).strip().title()
    if normalized["severity"] not in VALID_SEVERITIES:
        raise DisasterStoreError("Severity must be High, Medium, or Low.")
    if normalized["status"] not in VALID_STATUSES:
        raise DisasterStoreError("Status must be Active, Monitoring, or Resolved.")

    try:
        people_float = float(normalized["affected_people"])
        latitude = float(normalized["latitude"])
        longitude = float(normalized["longitude"])
    except (TypeError, ValueError):
        raise DisasterStoreError("Affected people and coordinates must be numeric.") from None

    if not math.isfinite(people_float) or people_float < 0 or not people_float.is_integer():
        raise DisasterStoreError("Affected people must be a non-negative whole number.")
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise DisasterStoreError("Latitude must be between -90 and 90.")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise DisasterStoreError("Longitude must be between -180 and 180.")

    normalized["affected_people"] = int(people_float)
    normalized["latitude"] = latitude
    normalized["longitude"] = longitude
    return normalized


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_store(
    db_path: str | Path = DEFAULT_DB_PATH,
    csv_path: str | Path = DEFAULT_CSV_PATH,
) -> None:
    """Create the database and import sample CSV rows only when it is empty."""
    with _connect(db_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS disasters (
                disaster_id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                disaster_type TEXT NOT NULL,
                severity TEXT NOT NULL CHECK (severity IN ('High', 'Medium', 'Low')),
                affected_people INTEGER NOT NULL CHECK (affected_people >= 0),
                latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
                longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
                status TEXT NOT NULL CHECK (status IN ('Active', 'Monitoring', 'Resolved')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        existing = connection.execute("SELECT COUNT(*) FROM disasters").fetchone()[0]
        if existing:
            return
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"Initial disaster dataset not found: {csv_file}")
        frame = pd.read_csv(csv_file)
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise DisasterStoreError(f"CSV is missing required columns: {', '.join(missing)}")
        seen: set[str] = set()
        for raw in frame[list(REQUIRED_COLUMNS)].to_dict(orient="records"):
            record = _validate_record(raw)
            if record["disaster_id"] in seen:
                raise DisasterStoreError(f"Duplicate disaster ID in CSV: {record['disaster_id']}")
            seen.add(record["disaster_id"])
            _insert_record(connection, record)


def _insert_record(connection: sqlite3.Connection, record: dict[str, Any]) -> None:
    connection.execute(
        """INSERT INTO disasters
           (disaster_id, location, disaster_type, severity, affected_people,
            latitude, longitude, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        tuple(record[key] for key in REQUIRED_COLUMNS),
    )


def list_disasters(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """SELECT disaster_id, location, disaster_type, severity,
                      affected_people, latitude, longitude, status
               FROM disasters ORDER BY disaster_id"""
        ).fetchall()
    return [dict(row) for row in rows]


def next_disaster_id(db_path: str | Path = DEFAULT_DB_PATH) -> str:
    records = list_disasters(db_path)
    numbers = []
    for record in records:
        disaster_id = record["disaster_id"]
        if disaster_id.startswith("D") and disaster_id[1:].isdigit():
            numbers.append(int(disaster_id[1:]))
    return f"D{max(numbers, default=0) + 1:03d}"


def add_disaster(
    record: dict[str, Any], db_path: str | Path = DEFAULT_DB_PATH
) -> dict[str, Any]:
    normalized = _validate_record(record)
    with _connect(db_path) as connection:
        try:
            _insert_record(connection, normalized)
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc) or "PRIMARY KEY" in str(exc):
                raise DisasterStoreError(
                    f"Disaster ID {normalized['disaster_id']} already exists."
                ) from None
            raise DisasterStoreError(f"Could not save disaster: {exc}") from None
    return normalized


def update_disaster_status(
    disaster_id: str,
    status: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    normalized_status = str(status).strip().title()
    if normalized_status not in VALID_STATUSES:
        raise DisasterStoreError("Status must be Active, Monitoring, or Resolved.")
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """UPDATE disasters SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE disaster_id = ?""",
            (normalized_status, str(disaster_id)),
        )
        if cursor.rowcount == 0:
            raise DisasterStoreError(f"Disaster ID {disaster_id} was not found.")
