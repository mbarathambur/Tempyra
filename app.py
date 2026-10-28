
import streamlit as st
import pandas as pd
import folium

from pathlib import Path
from streamlit_folium import st_folium

from optimization.resource_allocator import allocate_resources
from optimization.resource_optimizer import optimize_resources
from models.severity_predictor import predict_severity
from geospatial.disaster_zones import find_nearby_disasters
from geospatial.route_planner import plan_road_route
from agents.response_workflow import run_response_workflow
from storage.disaster_store import (
    DisasterStoreError,
    VALID_STATUSES,
    add_disaster,
    initialize_store,
    list_disasters,
    next_disaster_id,
    update_disaster_status,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Tempyra | Disaster Response",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Tempyra")
st.subheader("Autonomous Disaster Response Coordination")

st.caption(
    "Multi-Agent AI • Geospatial Intelligence • "
    "Dynamic Resource Allocation"
)

st.warning(
    "Prototype only: CSV records are demonstration data. "
    "Predictions, allocations and routes are not validated "
    "for real emergency response."
)


# --------------------------------------------------
# SESSION STATE HELPERS
# --------------------------------------------------

def clear_result(key):
    """Remove an earlier result before processing a new request."""
    st.session_state.pop(key, None)


def show_result_error(label, exc):
    """Display an error without preserving an old result."""
    st.error(f"{label}: {exc}")


# --------------------------------------------------
# LOAD PERSISTENT DISASTER DATA
# --------------------------------------------------

try:
    initialize_store()
    df = pd.DataFrame(list_disasters())

    if df.empty:
        st.info("No disaster records are available. Add a report below to begin.")
        df = pd.DataFrame(columns=[
            "disaster_id", "location", "disaster_type", "severity",
            "affected_people", "latitude", "longitude", "status",
        ])
except (OSError, ValueError, TypeError, pd.errors.ParserError) as exc:
    st.error(f"Could not load disaster records: {exc}")
    st.stop()


# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

st.sidebar.title("⚙️ Configuration")

available_teams = st.sidebar.number_input(
    "Available rescue teams",
    min_value=0,
    max_value=10000,
    value=12,
    step=1,
)

st.sidebar.caption(
    "Team counts are simulated for this prototype."
)


# --------------------------------------------------
# DASHBOARD OVERVIEW
# --------------------------------------------------

active_df = df[
    df["status"].astype(str).str.strip().str.lower()
    == "active"
]

high_count = int(
    (active_df["severity"] == "High").sum()
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Disasters", len(df))
col2.metric("Active Disasters", len(active_df))
col3.metric("High Severity", high_count)
col4.metric(
    "People Affected",
    int(df["affected_people"].sum()),
)


# --------------------------------------------------
# DISASTER MAP
# --------------------------------------------------

st.divider()
st.header("📍 Disaster Map")

disaster_map = folium.Map(
    location=[
        float(df["latitude"].mean()),
        float(df["longitude"].mean()),
    ],
    zoom_start=6,
)

severity_colors = {
    "High": "red",
    "Medium": "orange",
    "Low": "green",
}

for _, row in df.iterrows():
    folium.Marker(
        location=[
            float(row["latitude"]),
            float(row["longitude"]),
        ],
        tooltip=f"{row['location']} - {row['severity']}",
        popup=(
            f"ID: {row['disaster_id']}<br>"
            f"Type: {row['disaster_type']}<br>"
            f"Status: {row['status']}<br>"
            f"Affected: {row['affected_people']}"
        ),
        icon=folium.Icon(
            color=severity_colors.get(
                row["severity"],
                "blue",
            )
        ),
    ).add_to(disaster_map)

st_folium(
    disaster_map,
    use_container_width=True,
    height=420,
    key="disaster_overview_map",
)


# --------------------------------------------------
# DISASTER DATA TABLE
# --------------------------------------------------

st.header("📋 Disaster Records")

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# DISASTER RECORD MANAGEMENT (SQLITE PERSISTENCE)
# --------------------------------------------------

st.divider()
st.header("📝 Disaster Report Management")
st.caption(
    "Create disaster reports and update their status. Records are saved in a local SQLite database, "
    "so changes remain after refreshing or restarting the app."
)

with st.expander("➕ Register a New Disaster", expanded=False):
    with st.form("add_disaster_form", clear_on_submit=True):
        new_id = st.text_input("Disaster ID", value=next_disaster_id(), help="Unique ID, for example D004.")
        new_location = st.text_input("Location", placeholder="e.g. Chennai")
        new_type = st.selectbox(
            "Disaster type",
            ["Flood", "Storm", "Cyclone", "Earthquake", "Fire", "Landslide", "Other"],
        )
        new_severity = st.selectbox("Severity", ["High", "Medium", "Low"])
        new_affected = st.number_input("Affected people", min_value=0, max_value=100000000, value=0, step=1)
        coord1, coord2 = st.columns(2)
        new_latitude = coord1.number_input("Latitude", min_value=-90.0, max_value=90.0, value=13.0827, format="%.5f")
        new_longitude = coord2.number_input("Longitude", min_value=-180.0, max_value=180.0, value=80.2707, format="%.5f")
        new_status = st.selectbox("Initial status", ["Active", "Monitoring", "Resolved"])
        submit_disaster = st.form_submit_button("Save Disaster Report", type="primary")

    if submit_disaster:
        try:
            add_disaster({
                "disaster_id": new_id,
                "location": new_location,
                "disaster_type": new_type,
                "severity": new_severity,
                "affected_people": new_affected,
                "latitude": new_latitude,
                "longitude": new_longitude,
                "status": new_status,
            })
            st.success(f"Disaster report {new_id.strip()} saved.")
            st.rerun()
        except (DisasterStoreError, OSError) as exc:
            st.error(f"Could not save disaster report: {exc}")

if not df.empty:
    with st.expander("🔄 Update a Disaster Status", expanded=False):
        status_records = df[["disaster_id", "location", "status"]].to_dict(orient="records")
        record_labels = {
            f"{item['disaster_id']} — {item['location']} (current: {item['status']})": item["disaster_id"]
            for item in status_records
        }
        with st.form("update_disaster_status_form"):
            selected_label = st.selectbox("Select disaster", list(record_labels))
            updated_status = st.selectbox("New status", sorted(VALID_STATUSES))
            update_status_button = st.form_submit_button("Update Status")

        if update_status_button:
            selected_id = record_labels[selected_label]
            try:
                update_disaster_status(selected_id, updated_status)
                st.success(f"Status for {selected_id} updated to {updated_status}.")
                st.rerun()
            except (DisasterStoreError, OSError) as exc:
                st.error(f"Could not update disaster status: {exc}")


# --------------------------------------------------
# RULE-BASED RESOURCE ALLOCATION
# --------------------------------------------------

st.divider()
st.header("🚑 Basic Resource Allocation")

try:
    basic_allocations = allocate_resources(
        df,
        available_teams=int(available_teams),
    )

    st.dataframe(
        basic_allocations,
        use_container_width=True,
        hide_index=True,
    )

    assigned_basic = int(
        basic_allocations["teams_assigned"].sum()
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Available Teams", int(available_teams))
    c2.metric("Assigned Teams", assigned_basic)
    c3.metric(
        "Remaining Teams",
        max(0, int(available_teams) - assigned_basic),
    )

except Exception as exc:
    st.error(f"Basic allocation failed: {exc}")


# --------------------------------------------------
# OR-TOOLS OPTIMIZATION
# --------------------------------------------------

st.divider()
st.header("🧮 Optimized Resource Allocation")

if st.button(
    "Optimize Rescue Team Allocation",
    key="optimize_resources_button",
):
    clear_result("tempyra_optimized_result")

    try:
        optimized = optimize_resources(
            df.to_dict(orient="records"),
            int(available_teams),
        )

        st.session_state["tempyra_optimized_result"] = optimized

    except Exception as exc:
        show_result_error("Optimization failed", exc)

optimized_result = st.session_state.get(
    "tempyra_optimized_result"
)

if optimized_result is not None:
    try:
        optimized_df = pd.DataFrame(optimized_result)

        st.subheader("Optimization Results")

        st.dataframe(
            optimized_df,
            use_container_width=True,
            hide_index=True,
        )

        if (
            not optimized_df.empty
            and "teams_assigned" in optimized_df.columns
        ):
            optimized_count = int(
                optimized_df["teams_assigned"].sum()
            )
        else:
            optimized_count = 0

        st.metric(
            "Teams Assigned by Optimizer",
            optimized_count,
        )

        st.success("Optimization completed.")

    except Exception as exc:
        clear_result("tempyra_optimized_result")
        show_result_error("Could not display optimization", exc)


# --------------------------------------------------
# MACHINE LEARNING SEVERITY PREDICTION
# --------------------------------------------------

st.divider()
st.header("🤖 Disaster Severity Prediction")

st.caption(
    "Demonstration model trained on synthetic data. "
    "Predictions are not validated forecasts."
)

with st.form("severity_prediction_form"):
    affected_people = st.number_input(
        "Affected people",
        min_value=0,
        value=1000,
        step=100,
        key="severity_affected_people",
    )

    rainfall_mm = st.number_input(
        "Rainfall (mm)",
        min_value=0.0,
        value=100.0,
        key="severity_rainfall",
    )

    wind_speed_kmph = st.number_input(
        "Wind speed (km/h)",
        min_value=0.0,
        value=40.0,
        key="severity_wind_speed",
    )

    water_level_m = st.number_input(
        "Water level (m)",
        min_value=0.0,
        value=2.0,
        key="severity_water_level",
    )

    predict_button = st.form_submit_button(
        "Predict Severity"
    )

if predict_button:
    clear_result("tempyra_severity_result")

    try:
        prediction = predict_severity(
            affected_people,
            rainfall_mm,
            wind_speed_kmph,
            water_level_m,
        )

        st.session_state["tempyra_severity_result"] = prediction

    except Exception as exc:
        show_result_error("Prediction failed", exc)

prediction_result = st.session_state.get(
    "tempyra_severity_result"
)

if prediction_result is not None:
    st.subheader(
        "Predicted Severity: "
        f"{prediction_result['predicted_severity']}"
    )

    st.write(
        "Model confidence: "
        f"{prediction_result['model_confidence']:.1%}"
    )

    st.info(prediction_result["data_type"])


# --------------------------------------------------
# NEARBY DISASTER ANALYSIS
# --------------------------------------------------

st.divider()
st.header("🗺️ Nearby Disaster-Zone Analysis")

with st.form("nearby_disaster_form"):
    search_lat = st.number_input(
        "Search latitude",
        min_value=-90.0,
        max_value=90.0,
        value=13.0827,
        format="%.5f",
        key="nearby_search_lat",
    )

    search_lon = st.number_input(
        "Search longitude",
        min_value=-180.0,
        max_value=180.0,
        value=80.2707,
        format="%.5f",
        key="nearby_search_lon",
    )

    radius_km = st.number_input(
        "Search radius (km)",
        min_value=0.0,
        max_value=500.0,
        value=50.0,
        key="nearby_radius_km",
    )

    search_button = st.form_submit_button(
        "Find Nearby Disasters"
    )

if search_button:
    clear_result("tempyra_nearby_result")

    try:
        nearby = find_nearby_disasters(
            df.to_dict(orient="records"),
            search_lat,
            search_lon,
            radius_km,
        )

        st.session_state["tempyra_nearby_result"] = nearby

    except Exception as exc:
        show_result_error("Geospatial analysis failed", exc)

nearby_result = st.session_state.get(
    "tempyra_nearby_result"
)

if nearby_result is not None:
    if nearby_result:
        st.dataframe(
            pd.DataFrame(nearby_result),
            use_container_width=True,
            hide_index=True,
        )

        st.success(
            f"Found {len(nearby_result)} active disaster(s)."
        )
    else:
        st.info("No active disasters found within this radius.")


# --------------------------------------------------
# ROAD ROUTE PLANNER
# --------------------------------------------------

st.divider()
st.header("🚒 Road Route Planner")

st.caption(
    "Uses the OSRM routing service with OpenStreetMap road data. "
    "An internet connection is required."
)

with st.form("route_planner_form"):
    st.subheader("Starting Point")

    start_lat = st.number_input(
        "Start latitude",
        value=13.0827,
        min_value=-90.0,
        max_value=90.0,
        format="%.5f",
        key="route_start_lat",
    )

    start_lon = st.number_input(
        "Start longitude",
        value=80.2707,
        min_value=-180.0,
        max_value=180.0,
        format="%.5f",
        key="route_start_lon",
    )

    st.subheader("Destination")

    end_lat = st.number_input(
        "Destination latitude",
        value=13.0569,
        min_value=-90.0,
        max_value=90.0,
        format="%.5f",
        key="route_end_lat",
    )

    end_lon = st.number_input(
        "Destination longitude",
        value=80.2425,
        min_value=-180.0,
        max_value=180.0,
        format="%.5f",
        key="route_end_lon",
    )

    calculate_route = st.form_submit_button(
        "Calculate Road Route"
    )

if calculate_route:
    # Clear the previous route before attempting a new one.
    clear_result("tempyra_route_data")

    try:
        with st.spinner("Calculating the road route..."):
            result = plan_road_route(
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )

        st.session_state["tempyra_route_data"] = {
            "result": result,
            "start": [start_lat, start_lon],
            "end": [end_lat, end_lon],
        }

    except Exception as exc:
        show_result_error("Route planning failed", exc)

saved_route = st.session_state.get("tempyra_route_data")

if saved_route:
    route_result = saved_route["result"]

    if route_result.get("status") == "success":
        st.metric(
            "Road Distance (km)",
            route_result["distance_km"],
        )

        if "duration_minutes" in route_result:
            st.metric(
                "Estimated Driving Time (minutes)",
                route_result["duration_minutes"],
            )

        coordinates = route_result.get(
            "route_coordinates",
            [],
        )

        if coordinates:
            route_map = folium.Map(
                location=coordinates[0],
                zoom_start=13,
            )

            folium.Marker(
                saved_route["start"],
                tooltip="Starting Point",
                icon=folium.Icon(color="green"),
            ).add_to(route_map)

            folium.Marker(
                saved_route["end"],
                tooltip="Destination",
                icon=folium.Icon(color="red"),
            ).add_to(route_map)

            if len(coordinates) > 1:
                folium.PolyLine(
                    coordinates,
                    color="blue",
                    weight=5,
                    tooltip="Calculated road route",
                ).add_to(route_map)

            route_map_key = (
                "route_map_"
                f"{saved_route['start'][0]}_"
                f"{saved_route['start'][1]}_"
                f"{saved_route['end'][0]}_"
                f"{saved_route['end'][1]}"
            )

            st_folium(
                route_map,
                use_container_width=True,
                height=450,
                key=route_map_key,
            )

        else:
            st.warning(
                "The routing service returned no route geometry."
            )

    else:
        st.warning(
            route_result.get(
                "message",
                "No route could be calculated.",
            )
        )


# --------------------------------------------------
# MULTI-AGENT RESPONSE COORDINATION
# --------------------------------------------------

st.divider()
st.header("🧠 Multi-Agent Response Coordination")

st.caption(
    "Coordinates disaster analysis, geographic checks, "
    "resource allocation and response-plan generation."
)

if st.button(
    "Run Multi-Agent Analysis",
    key="run_multi_agent_button",
):
    clear_result("tempyra_agent_result")

    try:
        with st.spinner("Running response workflow..."):
            agent_result = run_response_workflow(
                disasters=df.to_dict(orient="records"),
                available_teams=int(available_teams),
            )

        st.session_state["tempyra_agent_result"] = agent_result

    except Exception as exc:
        show_result_error("Agent workflow failed", exc)

agent_result = st.session_state.get("tempyra_agent_result")

if agent_result is not None:
    st.success("Agent workflow completed.")

    allocations = agent_result.get("allocations", [])

    if allocations:
        allocation_df = pd.DataFrame(allocations)

        st.subheader("📋 Resource Allocation Summary")

        st.dataframe(
            allocation_df,
            use_container_width=True,
            hide_index=True,
        )

        if "teams_assigned" in allocation_df.columns:
            assigned = int(
                allocation_df["teams_assigned"].sum()
            )
        else:
            assigned = 0

        remaining = max(
            0,
            int(available_teams) - assigned,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Available Teams", int(available_teams))
        c2.metric("Assigned Teams", assigned)
        c3.metric("Remaining Teams", remaining)

    response_plan = agent_result.get("response_plan", [])

    if response_plan:
        st.subheader("🚨 Response Plan")

        for item in response_plan:
            st.write(f"• {item}")

    with st.expander("View Detailed Agent Results"):
        for key in [
            "analysis",
            "geo_summary",
            "disasters",
        ]:
            if key in agent_result:
                st.subheader(
                    key.replace("_", " ").title()
                )
                st.json(agent_result[key])


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Tempyra | Academic prototype | "
    "Demonstration data only — not an operational emergency system."
)
