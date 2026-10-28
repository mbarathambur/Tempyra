
import math

import pandas as pd


SEVERITY_PRIORITY = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

REQUIRED_TEAMS = {
    "High": 4,
    "Medium": 2,
    "Low": 1,
}

REQUIRED_COLUMNS = {
    "disaster_id",
    "location",
    "severity",
    "affected_people",
    "status",
}


def allocate_resources(disasters, available_teams=12):
    """
    Allocate simulated rescue teams to active disasters.

    High severity requires 4 teams, Medium requires 2, and
    Low requires 1. Higher severity and larger affected
    populations receive priority.

    Inactive incidents remain in the output but receive no teams.
    """

    # Validate the team budget.
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

    available_teams = int(team_value)

    if not isinstance(disasters, pd.DataFrame):
        raise ValueError("Disasters must be supplied as a DataFrame.")

    missing_columns = REQUIRED_COLUMNS - set(disasters.columns)

    if missing_columns:
        raise ValueError(
            "Disaster data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    df = disasters.copy()

    if df.empty:
        df["priority"] = pd.Series(dtype="int64")
        df["teams_assigned"] = pd.Series(dtype="int64")
        df["allocation_status"] = pd.Series(dtype="object")
        return df

    # Normalize and validate severity and status.
    df["severity"] = (
        df["severity"].astype("string").str.strip().str.title()
    )
    df["status"] = (
        df["status"].astype("string").str.strip().str.title()
    )

    invalid_severity = ~df["severity"].isin(SEVERITY_PRIORITY)

    if invalid_severity.any():
        invalid_values = (
            df.loc[invalid_severity, "severity"]
            .drop_duplicates()
            .tolist()
        )
        raise ValueError(
            f"Invalid severity values: {invalid_values}. "
            "Use High, Medium, or Low."
        )

    if df["status"].isna().any() or df["status"].eq("").any():
        raise ValueError("Every disaster must have a valid status.")

    # Affected population must be a non-negative whole number.
    try:
        affected = pd.to_numeric(
            df["affected_people"], errors="raise"
        ).astype(float)
    except (TypeError, ValueError):
        raise ValueError(
            "Affected people must be non-negative whole numbers."
        ) from None

    if (
        not affected.map(math.isfinite).all()
        or (affected < 0).any()
        or not affected.map(float.is_integer).all()
    ):
        raise ValueError(
            "Affected people must be non-negative whole numbers."
        )

    df["affected_people"] = affected.astype("int64")
    df["priority"] = df["severity"].map(SEVERITY_PRIORITY).astype(int)

    # Sort by severity first, then by affected population.
    df = df.sort_values(
        by=["priority", "affected_people"],
        ascending=[False, False],
        kind="stable",
    ).reset_index(drop=True)

    df["teams_assigned"] = 0
    remaining_teams = available_teams

    for index, row in df.iterrows():
        is_active = str(row["status"]).casefold() == "active"

        if not is_active or remaining_teams == 0:
            continue

        required = REQUIRED_TEAMS[row["severity"]]
        assigned = min(required, remaining_teams)

        df.at[index, "teams_assigned"] = assigned
        remaining_teams -= assigned

    def determine_allocation_status(row):
        if str(row["status"]).casefold() != "active":
            return "Not Active"

        assigned = int(row["teams_assigned"])
        required = REQUIRED_TEAMS[row["severity"]]

        if assigned == 0:
            return "Unassigned"

        if assigned == required:
            return "Fully Allocated"

        return "Partially Allocated"

    df["allocation_status"] = df.apply(
        determine_allocation_status,
        axis=1,
    )

    # Defensive guarantee: never exceed the available team budget.
    if int(df["teams_assigned"].sum()) > available_teams:
        raise RuntimeError(
            "Resource allocation exceeded the available team limit."
        )

    return df
