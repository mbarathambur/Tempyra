
from typing import TypedDict
import math

import pandas as pd
from langgraph.graph import StateGraph, START, END

from optimization.resource_allocator import allocate_resources
from geospatial.disaster_zones import find_nearby_disasters


# --------------------------------------------------
# WORKFLOW CONFIGURATION
# --------------------------------------------------

NEARBY_RADIUS_KM = 50.0

REQUIRED_FIELDS = [
    "disaster_id",
    "location",
    "disaster_type",
    "severity",
    "affected_people",
    "latitude",
    "longitude",
    "status",
]

VALID_SEVERITIES = {"High", "Medium", "Low"}

SEVERITY_PRIORITY = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
}


# --------------------------------------------------
# WORKFLOW STATE
# --------------------------------------------------

class DisasterState(TypedDict, total=False):
    disasters: list[dict]
    available_teams: int
    analysis: list[dict]
    geo_summary: list[dict]
    allocations: list[dict]
    response_plan: list[str]


# --------------------------------------------------
# INPUT VALIDATION
# --------------------------------------------------

def validate_disasters(disasters: list[dict]) -> list[dict]:
    """Validate and normalize disaster records."""

    if not isinstance(disasters, list):
        raise ValueError("Disasters must be supplied as a list.")

    validated = []
    seen_ids = set()

    for index, disaster in enumerate(disasters):
        if not isinstance(disaster, dict):
            raise ValueError(
                f"Disaster record {index + 1} must be a dictionary."
            )

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in disaster
            or pd.isna(disaster[field])
        ]

        if missing:
            raise ValueError(
                f"Disaster record {index + 1} is missing: "
                f"{', '.join(missing)}"
            )

        disaster_id = str(disaster["disaster_id"]).strip()
        location = str(disaster["location"]).strip()
        disaster_type = str(disaster["disaster_type"]).strip()
        severity = str(disaster["severity"]).strip().title()
        status = str(disaster["status"]).strip().title()

        if not disaster_id:
            raise ValueError("Disaster ID cannot be empty.")

        if disaster_id in seen_ids:
            raise ValueError(
                f"Duplicate disaster ID: {disaster_id}"
            )

        seen_ids.add(disaster_id)

        if not location:
            raise ValueError("Disaster location cannot be empty.")

        if not disaster_type:
            raise ValueError("Disaster type cannot be empty.")

        if severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity for {location}: {severity}. "
                "Use High, Medium, or Low."
            )

        if not status:
            raise ValueError(
                f"Status cannot be empty for {location}."
            )

        try:
            affected_raw = float(disaster["affected_people"])
            latitude = float(disaster["latitude"])
            longitude = float(disaster["longitude"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid numeric data for {location}."
            ) from None

        if (
            not math.isfinite(affected_raw)
            or affected_raw < 0
            or not affected_raw.is_integer()
        ):
            raise ValueError(
                f"Affected people must be a non-negative whole "
                f"number for {location}."
            )

        if not math.isfinite(latitude) or not -90 <= latitude <= 90:
            raise ValueError(f"Invalid latitude for {location}.")

        if not math.isfinite(longitude) or not -180 <= longitude <= 180:
            raise ValueError(f"Invalid longitude for {location}.")

        validated.append({
            **disaster,
            "disaster_id": disaster_id,
            "location": location,
            "disaster_type": disaster_type,
            "severity": severity,
            "affected_people": int(affected_raw),
            "latitude": latitude,
            "longitude": longitude,
            "status": status,
        })

    return validated


# --------------------------------------------------
# AGENT 1: DISASTER ANALYSIS
# --------------------------------------------------

def disaster_analysis_agent(state: DisasterState) -> dict:
    """Prioritize disasters by severity and affected population."""

    results = []

    for disaster in state["disasters"]:
        severity = disaster["severity"]

        results.append({
            "disaster_id": disaster["disaster_id"],
            "location": disaster["location"],
            "disaster_type": disaster["disaster_type"],
            "severity": severity,
            "affected_people": disaster["affected_people"],
            "status": disaster["status"],
            "priority": SEVERITY_PRIORITY[severity],
        })

    results.sort(
        key=lambda item: (
            item["priority"],
            item["affected_people"],
        ),
        reverse=True,
    )

    return {"analysis": results}


# --------------------------------------------------
# AGENT 2: GEOSPATIAL ASSESSMENT
# --------------------------------------------------

def geospatial_agent(state: DisasterState) -> dict:
    """
    Find nearby active disasters within the configured radius.

    The current disaster is excluded from its own nearby list.
    """

    disasters = state["disasters"]
    results = []

    for disaster in disasters:
        nearby = find_nearby_disasters(
            disasters=disasters,
            latitude=disaster["latitude"],
            longitude=disaster["longitude"],
            radius_km=NEARBY_RADIUS_KM,
        )

        # Do not report the disaster itself as a nearby incident.
        nearby = [
            item
            for item in nearby
            if item["disaster_id"] != disaster["disaster_id"]
        ]

        nearby_details = [
            {
                "disaster_id": item["disaster_id"],
                "location": item["location"],
                "disaster_type": item["disaster_type"],
                "severity": item["severity"],
                "distance_km": item["distance_km"],
            }
            for item in nearby
        ]

        results.append({
            "disaster_id": disaster["disaster_id"],
            "location": disaster["location"],
            "latitude": disaster["latitude"],
            "longitude": disaster["longitude"],
            "coordinates_valid": True,
            "status": disaster["status"],
            "nearby_radius_km": NEARBY_RADIUS_KM,
            "nearby_disaster_count": len(nearby_details),
            "nearby_disasters": nearby_details,
        })

    return {"geo_summary": results}


# --------------------------------------------------
# AGENT 3: RESOURCE ALLOCATION
# --------------------------------------------------

def resource_allocation_agent(state: DisasterState) -> dict:
    """Allocate simulated rescue teams to active disasters."""

    disasters = state["disasters"]
    available_teams = state["available_teams"]

    if not disasters:
        return {"allocations": []}

    disaster_df = pd.DataFrame(disasters)

    allocated = allocate_resources(
        disaster_df,
        available_teams=available_teams,
    )

    required_output = [
        "disaster_id",
        "location",
        "severity",
        "teams_assigned",
        "allocation_status",
    ]

    missing = [
        field for field in required_output
        if field not in allocated.columns
    ]

    if missing:
        raise ValueError(
            "Resource allocator returned an unexpected format. "
            f"Missing columns: {', '.join(missing)}"
        )

    records = allocated[required_output].to_dict(orient="records")
    assigned_total = 0

    for record in records:
        try:
            assigned = int(record["teams_assigned"])
        except (TypeError, ValueError):
            raise ValueError(
                "Resource allocator returned an invalid team count."
            ) from None

        if assigned < 0:
            raise ValueError(
                "Resource allocator returned a negative team count."
            )

        record["teams_assigned"] = assigned
        assigned_total += assigned

    if assigned_total > available_teams:
        raise ValueError(
            "Resource allocation exceeded the available team limit."
        )

    return {"allocations": records}


# --------------------------------------------------
# AGENT 4: RESPONSE PLANNING
# --------------------------------------------------

def response_planning_agent(state: DisasterState) -> dict:
    """Generate recommendations using allocation and proximity results."""

    allocations = state.get("allocations", [])
    geo_summary = state.get("geo_summary", [])

    nearby_by_id = {
        item["disaster_id"]: item
        for item in geo_summary
    }

    plans = []

    for item in allocations:
        status = str(
            item.get("allocation_status", "")
        ).strip()

        if status.casefold() == "not active":
            continue

        severity = str(item.get("severity", "Unknown"))
        location = str(item.get("location", "Unknown location"))
        disaster_id = item.get("disaster_id")
        assigned = int(item.get("teams_assigned", 0))

        plan = (
            f"{location}: {severity} priority, "
            f"{assigned} rescue team(s) assigned. "
            f"Status: {status}."
        )

        geo = nearby_by_id.get(disaster_id)

        if geo and geo.get("nearby_disasters"):
            nearby_locations = [
                f"{nearby['location']} "
                f"({nearby['distance_km']} km)"
                for nearby in geo["nearby_disasters"]
            ]

            plan += (
                " Nearby active incidents within "
                f"{NEARBY_RADIUS_KM:g} km: "
                f"{', '.join(nearby_locations)}."
            )

        plans.append(plan)

    if not plans:
        plans.append(
            "No active disaster requires team allocation."
        )

    return {"response_plan": plans}


# --------------------------------------------------
# BUILD LANGGRAPH WORKFLOW
# --------------------------------------------------

workflow = StateGraph(DisasterState)

workflow.add_node("disaster_analysis", disaster_analysis_agent)
workflow.add_node("geospatial_assessment", geospatial_agent)
workflow.add_node("resource_allocation", resource_allocation_agent)
workflow.add_node("response_planning", response_planning_agent)

workflow.add_edge(START, "disaster_analysis")
workflow.add_edge("disaster_analysis", "geospatial_assessment")
workflow.add_edge("geospatial_assessment", "resource_allocation")
workflow.add_edge("resource_allocation", "response_planning")
workflow.add_edge("response_planning", END)

response_graph = workflow.compile()


# --------------------------------------------------
# PUBLIC WORKFLOW FUNCTION
# --------------------------------------------------

def run_response_workflow(
    disasters: list[dict],
    available_teams: int,
) -> dict:
    """Validate inputs and execute the response workflow."""

    if isinstance(available_teams, bool):
        raise ValueError(
            "Available teams must be a non-negative integer."
        )

    try:
        team_value = float(available_teams)
    except (TypeError, ValueError):
        raise ValueError(
            "Available teams must be a non-negative integer."
        ) from None

    if (
        not math.isfinite(team_value)
        or team_value < 0
        or not team_value.is_integer()
    ):
        raise ValueError(
            "Available teams must be a non-negative integer."
        )

    normalized_disasters = validate_disasters(disasters)

    return response_graph.invoke({
        "disasters": normalized_disasters,
        "available_teams": int(team_value),
    })
