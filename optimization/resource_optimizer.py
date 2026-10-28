
from ortools.linear_solver import pywraplp


def optimize_resources(disasters, available_teams):
    solver = pywraplp.Solver.CreateSolver("SCIP")

    if solver is None:
        raise RuntimeError("OR-Tools SCIP solver is unavailable.")

    active = [
        d for d in disasters
        if str(d["status"]).strip().lower() == "active"
    ]

    if not active or available_teams <= 0:
        return [
            {
                "disaster_id": d["disaster_id"],
                "location": d["location"],
                "teams_assigned": 0
            }
            for d in active
        ]

    severity_weight = {"High": 100, "Medium": 50, "Low": 20}
    variables = []

    for i, disaster in enumerate(active):
        severity = str(disaster["severity"]).title()
        weight = severity_weight.get(severity, 10)
        affected = max(0, int(disaster["affected_people"]))

        max_needed = {
            "High": 4,
            "Medium": 2,
            "Low": 1
        }.get(severity, 1)

        variable = solver.IntVar(
            0,
            max_needed,
            f"teams_{i}"
        )

        variables.append((disaster, variable, weight, affected))

    solver.Add(
        sum(variable for _, variable, _, _ in variables)
        <= int(available_teams)
    )

    # Prioritize severity and affected population.
    solver.Maximize(
        sum(
            variable * (weight + min(affected, 10000) / 100)
            for _, variable, weight, affected in variables
        )
    )

    status = solver.Solve()

    if status not in (
        pywraplp.Solver.OPTIMAL,
        pywraplp.Solver.FEASIBLE
    ):
        raise RuntimeError("Resource optimization did not find a solution.")

    return [
        {
            "disaster_id": disaster["disaster_id"],
            "location": disaster["location"],
            "severity": disaster["severity"],
            "teams_assigned": int(variable.solution_value())
        }
        for disaster, variable, _, _ in variables
    ]
