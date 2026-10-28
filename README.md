# Tempyra

## Autonomous Disaster Response Coordination using Multi-Agent AI, Geospatial Intelligence, and Dynamic Resource Allocation

Tempyra is an academic disaster-response coordination prototype. It combines an interactive Streamlit dashboard, geospatial analysis, rule-based resource allocation, OR-Tools optimization, a demonstration severity model, road-route lookup, and a LangGraph workflow.

> **Safety note:** Tempyra is a prototype, not an operational emergency-management system. The included records are sample data. Severity predictions are trained on synthetic data, allocations are simulated, and route results depend on an external routing service. A trained human coordinator must independently verify every result.

## Features

- **Dashboard:** Summary metrics and a table of disaster records.
- **Interactive map:** Plot incidents using latitude and longitude, with marker colors based on severity.
- **Persistent disaster reports:** Register incidents and update their status through the dashboard. Records are stored locally in SQLite and remain available after a browser refresh or app restart.
- **Input validation:** Validate disaster IDs, required fields, severity/status values, affected-person counts, and geographic coordinates before saving.
- **Basic resource allocation:** Produce a rule-based rescue-team allocation within the available team limit.
- **Optimized resource allocation:** Use OR-Tools to calculate a resource allocation under the configured team limit.
- **Demonstration severity prediction:** Estimate a severity class from affected population, rainfall, wind speed, and water level using a model trained on synthetic data.
- **Nearby disaster search:** Find active records within a selected radius using geographic distance.
- **Road-route planning:** Request a road route from OSRM using OpenStreetMap road data. An internet connection is required.
- **LangGraph workflow:** Run a deterministic multi-step workflow for disaster analysis, coordinate checks, resource allocation, and response-plan text generation. These are workflow agents, not independent LLM-powered agents.
- **Automated tests:** Test resource, geospatial, route, severity, workflow, and persistence behavior.

## Technology Stack

- Python, Pandas, NumPy
- Streamlit, Folium, Streamlit-Folium
- Scikit-learn
- OR-Tools
- LangGraph
- SQLite
- OSRM routing service and OpenStreetMap road data
- Pytest

## Project Structure

```text
Tempyra/
├── agents/
│   └── response_workflow.py
├── data/
│   └── disasters.csv              # Initial sample records
├── geospatial/
│   ├── disaster_zones.py
│   └── route_planner.py
├── models/
│   └── severity_predictor.py
├── optimization/
│   ├── resource_allocator.py
│   └── resource_optimizer.py
├── storage/
│   ├── __init__.py
│   └── disaster_store.py          # SQLite persistence and validation
├── tests/
│   ├── test_disaster_store.py
│   ├── test_disaster_zones.py
│   ├── test_optimizer.py
│   ├── test_response_workflow.py
│   ├── test_route_planner.py
│   └── test_severity_predictor.py
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

### 1. Get the source

```bash
git clone <your-repository-url>
cd Tempyra
```

If you are working from a downloaded source folder, open a terminal in that folder instead.

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Run the Application

```powershell
python -m streamlit run app.py
```

Open the local URL printed in the terminal.

## Use the Disaster Report Manager

1. On first launch, Tempyra imports the records from `data/disasters.csv` into `data/tempyra.db`.
2. Expand **Register a New Disaster** to add a record with a unique ID, location, type, severity, affected population, and coordinates.
3. Expand **Update a Disaster Status** to mark a record Active, Monitoring, or Resolved.
4. New records and status updates are saved to SQLite and remain after restart.

The CSV is only the initial seed. Once the SQLite database has records, changing the CSV does not overwrite or reset the database. To start a fresh local demo, stop the app and remove `data/tempyra.db`; the next launch will import the CSV again. Do not delete the database if you need to preserve locally entered reports.

## Run Automated Tests

```powershell
python -m pytest tests/ -v
```

The suite covers the project logic and SQLite persistence. A passing unit-test suite does not validate predictions or resource plans for real-world emergencies.

## Limitations and Next Improvements

- The dataset is a small static sample, not a verified live disaster feed.
- The severity model uses synthetic training data and is not a validated forecasting model.
- Resource assignments are simulated decision-support suggestions and need human review.
- The LangGraph workflow uses deterministic Python functions; it does not currently call an LLM or operate as autonomous real-world agents.
- Route planning relies on an external OSRM service and may fail if the network or service is unavailable.
- There is no authentication, multi-user access control, live resource tracking, production monitoring, or deployment hardening.
- The prototype has not been certified or validated for operational emergency response.

Future work should prioritize verified data sources, robust evaluation against historical incidents, integration testing, audit logs, access control, and failure handling before any real-world use.

## Project Status

A locally runnable academic prototype with a dashboard, map, disaster report persistence, resource allocation, optimization, demonstration severity prediction, route planning, a LangGraph workflow, and automated tests.
