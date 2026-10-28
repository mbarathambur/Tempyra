import pandas as pd
import pytest

from storage.disaster_store import (
    DisasterStoreError,
    add_disaster,
    initialize_store,
    list_disasters,
    next_disaster_id,
    update_disaster_status,
)


@pytest.fixture
def store_paths(tmp_path):
    csv_path = tmp_path / "disasters.csv"
    pd.DataFrame([
        {
            "disaster_id": "D001",
            "location": "Chennai",
            "disaster_type": "Flood",
            "severity": "High",
            "affected_people": 1200,
            "latitude": 13.0827,
            "longitude": 80.2707,
            "status": "Active",
        }
    ]).to_csv(csv_path, index=False)
    return tmp_path / "tempyra.db", csv_path


def test_initializes_from_csv_and_persists_records(store_paths):
    db_path, csv_path = store_paths
    initialize_store(db_path, csv_path)
    assert list_disasters(db_path)[0]["disaster_id"] == "D001"

    add_disaster({
        "disaster_id": "D002",
        "location": "Madurai",
        "disaster_type": "Storm",
        "severity": "Medium",
        "affected_people": 45,
        "latitude": 9.9252,
        "longitude": 78.1198,
        "status": "Monitoring",
    }, db_path)
    assert len(list_disasters(db_path)) == 2
    assert next_disaster_id(db_path) == "D003"


def test_status_update_persists(store_paths):
    db_path, csv_path = store_paths
    initialize_store(db_path, csv_path)
    update_disaster_status("D001", "Resolved", db_path)
    assert list_disasters(db_path)[0]["status"] == "Resolved"


def test_rejects_invalid_coordinates(store_paths):
    db_path, csv_path = store_paths
    initialize_store(db_path, csv_path)
    with pytest.raises(DisasterStoreError, match="Latitude"):
        add_disaster({
            "disaster_id": "D002",
            "location": "Invalid",
            "disaster_type": "Flood",
            "severity": "High",
            "affected_people": 2,
            "latitude": 91,
            "longitude": 0,
            "status": "Active",
        }, db_path)


def test_rejects_duplicate_ids(store_paths):
    db_path, csv_path = store_paths
    initialize_store(db_path, csv_path)
    with pytest.raises(DisasterStoreError, match="already exists"):
        add_disaster({
            "disaster_id": "D001",
            "location": "Duplicate",
            "disaster_type": "Flood",
            "severity": "Low",
            "affected_people": 1,
            "latitude": 0,
            "longitude": 0,
            "status": "Active",
        }, db_path)
