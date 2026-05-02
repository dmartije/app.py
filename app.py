import math
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ortools.sat.python import cp_model


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(page_title="Sample Prep Turn-Around-Time Optimization ", layout="wide")
st.title("OR-Tools Sample Preparation Optimizer")


# ============================================================
# CONSTANTS
# ============================================================

TOTAL_PLATES = 5
TIME_UNIT_MINUTES = 5
PLATE_IDS = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]


# ============================================================
# PROCESS RULES
# ============================================================

rules = {
    "Sublot": {"priority": 1, "minutes_per_cycle": 15, "personnel_per_sample": 4, "plate_capacity": 1},
    "Face": {"priority": 2, "minutes_per_cycle": 5, "personnel_per_sample": 1, "plate_capacity": 10},
    "Mine": {"priority": 3, "minutes_per_cycle": 10, "personnel_per_sample": 3, "plate_capacity": 2},
    "Lot Quality": {"priority": 4, "minutes_per_cycle": 15, "personnel_per_sample": 1, "plate_capacity": 1},
}


# ============================================================
# INPUT
# ============================================================

st.sidebar.header("Input Data")

start_datetime = st.sidebar.datetime_input(
    "Date and Time Received",
    value=datetime(2026, 5, 2, 8, 0)
)

total_personnel = st.sidebar.number_input(
    "Personnel Present",
    min_value=1,
    max_value=100,
    value=20
)

samples = {
    "Face": st.sidebar.number_input("Face Samples", min_value=0, value=100),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, value=15),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, value=3),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, value=1),
}

solver_time = st.sidebar.slider("Solver Time Limit (seconds)", 3, 60, 15)


# ============================================================
# GREEDY UPPER BOUND (for horizon)
# ============================================================

def fast_upper_bound(samples):
    total_minutes = 0
    for s, qty in samples.items():
        if qty == 0:
            continue
        rule = rules[s]
        capacity = min(
            TOTAL_PLATES * rule["plate_capacity"],
            total_personnel // rule["personnel_per_sample"]
        )
        cycles = math.ceil(qty / capacity)
        total_minutes += cycles * rule["minutes_per_cycle"]
    return max(1, total_minutes // TIME_UNIT_MINUTES)


# ============================================================
# SOLVER
# ============================================================

def solve_model(samples):
    model = cp_model.CpModel()

    horizon = fast_upper_bound(samples)

    variables = []
    all_jobs = []

    for s, qty in samples.items():
        if qty == 0:
            continue

        rule = rules[s]
        duration = rule["minutes_per_cycle"] // TIME_UNIT_MINUTES

        max_qty = min(
            qty,
            TOTAL_PLATES * rule["plate_capacity"],
            total_personnel // rule["personnel_per_sample"]
        )

        for t in range(horizon):
            for q in range(1, max_qty + 1):

                personnel = q * rule["personnel_per_sample"]
                plates = math.ceil(q / rule["plate_capacity"])

                if personnel > total_personnel or plates > TOTAL_PLATES:
                    continue

                var = model.NewBoolVar(f"{s}_{t}_{q}")

                variables.append(var)

                all_jobs.append({
                    "var": var,
                    "sample": s,
                    "start": t,
                    "end": t + duration,
                    "qty": q,
                    "personnel": personnel,
                    "plates": plates,
                    "priority": rule["priority"]
                })

    # sample completion constraint
    for s, qty in samples.items():
        if qty == 0:
            continue

        model.Add(
            sum(j["qty"] * j["var"] for j in all_jobs if j["sample"] == s) == qty
        )

    # resource constraints
    for t in range(horizon):
        model.Add(
            sum(j["personnel"] * j["var"] for j in all_jobs if j["start"] <= t < j["end"])
            <= total_personnel
        )

        model.Add(
            sum(j["plates"] * j["var"] for j in all_jobs if j["start"] <= t < j["end"])
            <= TOTAL_PLATES
        )

    # objective
    makespan = model.NewIntVar(0, horizon, "makespan")

    for j in all_jobs:
        model.Add(makespan >= j["end"]).OnlyEnforceIf(j["var"])

    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = solver_time

    status = solver.Solve(model)

    # =========================
    # SOLVER STATUS INDICATOR
    # =========================
    if status == cp_model.OPTIMAL:
        solver_status = "OPTIMAL"
        solver_msg = "✅ Optimal solution found."
    elif status == cp_model.FEASIBLE:
        solver_status = "FEASIBLE"
        solver_msg = "⚠️ Feasible solution (not guaranteed optimal)."
    else:
        raise ValueError("No solution found.")

    # extract solution
    jobs = []
    for j in all_jobs:
        if solver.Value(j["var"]) == 1:
            start = start_datetime + timedelta(minutes=j["start"] * TIME_UNIT_MINUTES)
            finish = start_datetime + timedelta(minutes=j["end"] * TIME_UNIT_MINUTES)

            jobs.append({
                "Sample Type": j["sample"],
                "Processed Samples": j["qty"],
                "Personnel": j["personnel"],
                "Plates Needed": j["plates"],
                "Start": start,
                "Finish": finish
            })

    return jobs, solver_status, solver_msg


# ============================================================
# RUN
# ============================================================

if st.button("Generate Optimized Schedule"):

    try:
        jobs, solver_status, solver_msg = solve_model(samples)

        df = pd.DataFrame(jobs)

        st.info(f"Solver Status: {solver_status}")
        st.write(solver_msg)

        final_finish = df["Finish"].max()

        st.success(f"All samples completed by: {final_finish}")

        st.dataframe(df, use_container_width=True)

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Sample Type",
            color="Sample Type",
            text="Processed Samples"
        )

        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(str(e))

else:
    st.info("Enter inputs and click Generate.")
