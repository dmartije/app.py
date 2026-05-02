import math
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ortools.sat.python import cp_model


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(page_title="OR-Tools Scheduler", layout="wide")
st.title("Sample Preparation Optimizer with Plate Gantt")

TOTAL_PLATES = 5
TIME_UNIT = 5
PLATES = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]

rules = {
    "Sublot": {"priority": 1, "minutes": 15, "personnel": 4, "capacity": 1},
    "Face": {"priority": 2, "minutes": 5, "personnel": 1, "capacity": 10},
    "Mine": {"priority": 3, "minutes": 10, "personnel": 3, "capacity": 2},
    "Lot Quality": {"priority": 4, "minutes": 15, "personnel": 1, "capacity": 1},
}


# ============================================================
# INPUT
# ============================================================

st.sidebar.header("Input")

start_time = st.sidebar.datetime_input(
    "Start Time", value=datetime(2026, 5, 2, 8, 0)
)

personnel_total = st.sidebar.number_input("Personnel", 1, 100, 20)

samples = {
    "Face": st.sidebar.number_input("Face", 0, 500, 100),
    "Mine": st.sidebar.number_input("Mine", 0, 500, 15),
    "Sublot": st.sidebar.number_input("Sublot", 0, 100, 3),
    "Lot Quality": st.sidebar.number_input("Lot Quality", 0, 100, 1),
}

time_limit = st.sidebar.slider("Solver Time (sec)", 3, 60, 15)


# ============================================================
# SOLVER
# ============================================================

def solve(samples):
    model = cp_model.CpModel()

    horizon = 200  # safe limit

    jobs = []

    for s, qty in samples.items():
        if qty == 0:
            continue

        r = rules[s]
        dur = r["minutes"] // TIME_UNIT

        max_batch = min(
            qty,
            personnel_total // r["personnel"],
            TOTAL_PLATES * r["capacity"],
        )

        for t in range(horizon):
            for q in range(1, max_batch + 1):
                p = q * r["personnel"]
                pl = math.ceil(q / r["capacity"])

                if p > personnel_total or pl > TOTAL_PLATES:
                    continue

                v = model.NewBoolVar(f"{s}_{t}_{q}")

                jobs.append({
                    "var": v,
                    "type": s,
                    "start": t,
                    "end": t + dur,
                    "qty": q,
                    "personnel": p,
                    "plates": pl,
                })

    # fulfill samples
    for s, qty in samples.items():
        if qty == 0:
            continue

        model.Add(sum(j["qty"] * j["var"] for j in jobs if j["type"] == s) == qty)

    # resource constraints
    for t in range(horizon):
        model.Add(sum(j["personnel"] * j["var"] for j in jobs if j["start"] <= t < j["end"]) <= personnel_total)
        model.Add(sum(j["plates"] * j["var"] for j in jobs if j["start"] <= t < j["end"]) <= TOTAL_PLATES)

    makespan = model.NewIntVar(0, horizon, "makespan")

    for j in jobs:
        model.Add(makespan >= j["end"]).OnlyEnforceIf(j["var"])

    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        status_text = "OPTIMAL"
    elif status == cp_model.FEASIBLE:
        status_text = "FEASIBLE"
    else:
        raise ValueError("No solution")

    result = []
    for j in jobs:
        if solver.Value(j["var"]) == 1:
            stime = start_time + timedelta(minutes=j["start"] * TIME_UNIT)
            ftime = start_time + timedelta(minutes=j["end"] * TIME_UNIT)

            result.append({
                "Type": j["type"],
                "Qty": j["qty"],
                "Personnel": j["personnel"],
                "PlatesNeeded": j["plates"],
                "Start": stime,
                "Finish": ftime
            })

    return result, status_text


# ============================================================
# ASSIGN PHYSICAL PLATES
# ============================================================

def assign_plates(jobs):
    plate_free = {p: start_time for p in PLATES}
    out = []

    for j in sorted(jobs, key=lambda x: x["Start"]):
        needed = j["PlatesNeeded"]
        assigned = []

        for p in PLATES:
            if plate_free[p] <= j["Start"]:
                assigned.append(p)
                if len(assigned) == needed:
                    break

        for p in assigned:
            plate_free[p] = j["Finish"]

        j2 = j.copy()
        j2["Plate"] = ", ".join(assigned)
        out.append(j2)

    return out


# ============================================================
# RUN
# ============================================================

if st.button("Generate Schedule"):

    jobs, status = solve(samples)

    st.info(f"Solver Status: {status}")

    jobs = assign_plates(jobs)

    df = pd.DataFrame(jobs)

    st.dataframe(df, use_container_width=True)

    st.success(f"Finish Time: {df['Finish'].max()}")

    # ========================================================
    # GANTT PER PLATE
    # ========================================================

    gantt = []

    for _, r in df.iterrows():
        plates = r["Plate"].split(", ")
        for p in plates:
            gantt.append({
                "Plate": p,
                "Task": r["Type"],
                "Start": r["Start"],
                "Finish": r["Finish"]
            })

    gantt_df = pd.DataFrame(gantt)

    fig = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="Plate",
        color="Task"
    )

    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter inputs then click Generate")
