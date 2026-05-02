# ============================================================
# OR-TOOLS SAMPLE PREPARATION OPTIMIZER
# ============================================================
# This app creates an optimized sample preparation schedule.
#
# It considers:
# - 5 fixed working plates
# - available personnel
# - sample priority
# - dynamic reassignment of personnel
# - dynamic reuse of plates
# - staggered starts
# - least overall completion time
#
# Optimization engine:
# - Google OR-Tools CP-SAT Solver
# ============================================================

import math
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ortools.sat.python import cp_model


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(page_title="OR-Tools Sample Scheduler", layout="wide")
st.title("OR-Tools Sample Preparation Optimizer")


# ============================================================
# FIXED RESOURCES
# ============================================================

TOTAL_PLATES = 5
TIME_UNIT_MINUTES = 5
PLATE_IDS = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]


# ============================================================
# PROCESSING RULES
# ============================================================
# priority:
#   Lower number = higher priority
#
# minutes_per_cycle:
#   One cycle duration
#
# personnel_per_sample:
#   Number of personnel needed to process 1 sample at the same time
#
# plate_capacity:
#   Number of samples one plate can hold per cycle
# ============================================================

rules = {
    "Sublot": {
        "priority": 1,
        "minutes_per_cycle": 15,
        "personnel_per_sample": 4,
        "plate_capacity": 1,
    },
    "Face": {
        "priority": 2,
        "minutes_per_cycle": 5,
        "personnel_per_sample": 1,
        "plate_capacity": 10,
    },
    "Mine": {
        "priority": 3,
        "minutes_per_cycle": 10,
        "personnel_per_sample": 3,
        "plate_capacity": 2,
    },
    "Lot Quality": {
        "priority": 4,
        "minutes_per_cycle": 15,
        "personnel_per_sample": 1,
        "plate_capacity": 1,
    },
}


# ============================================================
# USER INPUT
# ============================================================

st.sidebar.header("Input Data")

start_datetime = st.sidebar.datetime_input(
    "Date and Time Received",
    value=datetime(2026, 5, 2, 8, 0),
)

total_personnel = st.sidebar.number_input(
    "Personnel Present",
    min_value=1,
    max_value=100,
    value=20,
    step=1,
)

samples = {
    "Face": st.sidebar.number_input("Face Samples", min_value=0, value=100, step=1),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, value=15, step=1),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, value=3, step=1),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, value=1, step=1),
}

max_solver_seconds = st.sidebar.slider(
    "Solver Time Limit (seconds)",
    min_value=3,
    max_value=60,
    value=15,
    step=1,
)


# ============================================================
# FAST GREEDY SCHEDULE
# ------------------------------------------------------------
# Used only to create a reasonable time horizon for OR-Tools.
# ============================================================

def fast_greedy_upper_bound(samples, total_personnel):
    remaining = {k: v for k, v in samples.items() if v > 0}
    current_time_units = 0
    running = []

    while remaining or running:
        running = [job for job in running if job["finish"] > current_time_units]

        used_personnel = sum(job["personnel"] for job in running)
        used_plates = sum(job["plates"] for job in running)

        available_personnel = total_personnel - used_personnel
        available_plates = TOTAL_PLATES - used_plates

        started = False

        for sample_type in sorted(rules.keys(), key=lambda x: rules[x]["priority"]):
            if sample_type not in remaining:
                continue

            rule = rules[sample_type]

            max_by_personnel = available_personnel // rule["personnel_per_sample"]
            max_by_plates = available_plates * rule["plate_capacity"]

            qty = min(remaining[sample_type], max_by_personnel, max_by_plates)

            if qty <= 0:
                continue

            personnel_needed = qty * rule["personnel_per_sample"]
            plates_needed = math.ceil(qty / rule["plate_capacity"])
            duration_units = rule["minutes_per_cycle"] // TIME_UNIT_MINUTES

            running.append({
                "finish": current_time_units + duration_units,
                "personnel": personnel_needed,
                "plates": plates_needed,
            })

            remaining[sample_type] -= qty

            if remaining[sample_type] <= 0:
                del remaining[sample_type]

            available_personnel -= personnel_needed
            available_plates -= plates_needed

            started = True

        if running:
            current_time_units = min(job["finish"] for job in running)
        elif not started and remaining:
            return None

    return current_time_units


# ============================================================
# OR-TOOLS OPTIMIZER
# ============================================================

def solve_with_ortools(samples, total_personnel, start_datetime, max_seconds):
    active_samples = {k: v for k, v in samples.items() if v > 0}

    if not active_samples:
        return []

    greedy_horizon = fast_greedy_upper_bound(active_samples, total_personnel)

    if greedy_horizon is None:
        raise ValueError("No valid schedule is possible with the given personnel and plate limits.")

    horizon = max(greedy_horizon, 1)

    model = cp_model.CpModel()

    start_vars = {}
    all_options = []

    # --------------------------------------------------------
    # Create possible cycle options
    # --------------------------------------------------------

    for sample_type, qty_required in active_samples.items():
        rule = rules[sample_type]

        duration_units = rule["minutes_per_cycle"] // TIME_UNIT_MINUTES

        max_qty_per_cycle = min(
            qty_required,
            total_personnel // rule["personnel_per_sample"],
            TOTAL_PLATES * rule["plate_capacity"],
        )

        if max_qty_per_cycle <= 0:
            raise ValueError(f"Not enough personnel to process {sample_type}.")

        for t in range(0, horizon - duration_units + 1):
            for qty in range(1, max_qty_per_cycle + 1):
                personnel_needed = qty * rule["personnel_per_sample"]
                plates_needed = math.ceil(qty / rule["plate_capacity"])

                if personnel_needed > total_personnel:
                    continue

                if plates_needed > TOTAL_PLATES:
                    continue

                var = model.NewBoolVar(f"{sample_type}_t{t}_q{qty}")

                option = {
                    "sample_type": sample_type,
                    "start": t,
                    "end": t + duration_units,
                    "duration_units": duration_units,
                    "qty": qty,
                    "personnel": personnel_needed,
                    "plates": plates_needed,
                    "var": var,
                    "priority": rule["priority"],
                }

                start_vars[(sample_type, t, qty)] = var
                all_options.append(option)

    # --------------------------------------------------------
    # Exact sample completion constraint
    # --------------------------------------------------------

    for sample_type, qty_required in active_samples.items():
        model.Add(
            sum(
                opt["qty"] * opt["var"]
                for opt in all_options
                if opt["sample_type"] == sample_type
            ) == qty_required
        )

    # --------------------------------------------------------
    # Resource constraints per 5-minute slot
    # --------------------------------------------------------

    for slot in range(horizon):
        model.Add(
            sum(
                opt["personnel"] * opt["var"]
                for opt in all_options
                if opt["start"] <= slot < opt["end"]
            ) <= total_personnel
        )

        model.Add(
            sum(
                opt["plates"] * opt["var"]
                for opt in all_options
                if opt["start"] <= slot < opt["end"]
            ) <= TOTAL_PLATES
        )

    # --------------------------------------------------------
    # Completion time variables
    # --------------------------------------------------------

    makespan = model.NewIntVar(0, horizon, "makespan")

    type_completion = {}

    for sample_type in active_samples:
        type_completion[sample_type] = model.NewIntVar(0, horizon, f"{sample_type}_completion")

    for opt in all_options:
        model.Add(makespan >= opt["end"]).OnlyEnforceIf(opt["var"])
        model.Add(type_completion[opt["sample_type"]] >= opt["end"]).OnlyEnforceIf(opt["var"])

    # --------------------------------------------------------
    # Objective
    # --------------------------------------------------------
    # Main target:
    #   minimize overall finish time
    #
    # Secondary target:
    #   higher priority samples finish earlier
    #
    # Third target:
    #   reduce unnecessary fragmentation/cycles
    # --------------------------------------------------------

    objective_terms = [makespan * 100000]

    for sample_type, completion_var in type_completion.items():
        priority = rules[sample_type]["priority"]
        objective_terms.append(completion_var * priority * 1000)

    objective_terms.append(sum(opt["var"] for opt in all_options))

    model.Minimize(sum(objective_terms))

    # --------------------------------------------------------
    # Solve
    # --------------------------------------------------------

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        raise ValueError("Solver could not find a valid schedule.")

    jobs = []

    for opt in all_options:
        if solver.Value(opt["var"]) == 1:
            start = start_datetime + timedelta(minutes=opt["start"] * TIME_UNIT_MINUTES)
            finish = start_datetime + timedelta(minutes=opt["end"] * TIME_UNIT_MINUTES)

            jobs.append({
                "Sample Type": opt["sample_type"],
                "Processed Samples": opt["qty"],
                "Personnel": opt["personnel"],
                "Plates Needed": opt["plates"],
                "Start": start,
                "Finish": finish,
                "Duration Minutes": opt["duration_units"] * TIME_UNIT_MINUTES,
                "Priority": opt["priority"],
            })

    jobs = sorted(jobs, key=lambda x: (x["Start"], x["Priority"]))

    return jobs


# ============================================================
# PHYSICAL PLATE ASSIGNMENT
# ------------------------------------------------------------
# OR-Tools optimizes plate count.
# This function assigns actual Plate 1 to Plate 5 without overlap.
# ============================================================

def assign_physical_plates(jobs):
    plate_available_time = {plate: datetime.min for plate in PLATE_IDS}
    assigned_jobs = []

    for job in sorted(jobs, key=lambda x: (x["Start"], x["Priority"])):
        needed = job["Plates Needed"]
        assigned = []

        for plate in PLATE_IDS:
            if plate_available_time[plate] <= job["Start"]:
                assigned.append(plate)

                if len(assigned) == needed:
                    break

        if len(assigned) < needed:
            assigned = assigned + ["Unassigned"] * (needed - len(assigned))

        for plate in assigned:
            if plate != "Unassigned":
                plate_available_time[plate] = job["Finish"]

        new_job = dict(job)
        new_job["Plates"] = ", ".join(assigned)
        assigned_jobs.append(new_job)

    return assigned_jobs


# ============================================================
# RUN APP
# ============================================================

if st.button("Generate OR-Tools Optimized Schedule"):
    try:
        jobs = solve_with_ortools(
            samples=samples,
            total_personnel=total_personnel,
            start_datetime=start_datetime,
            max_seconds=max_solver_seconds,
        )

        jobs = assign_physical_plates(jobs)

        df = pd.DataFrame(jobs)

        if df.empty:
            st.warning("No samples entered.")
        else:
            df = df.sort_values(["Start", "Priority"])
            final_finish = df["Finish"].max()

            st.success(
                f"All samples completed by: {final_finish.strftime('%B %d, %Y %I:%M %p')}"
            )

            st.subheader("Optimized Detailed Schedule")

            st.dataframe(
                df[
                    [
                        "Sample Type",
                        "Processed Samples",
                        "Personnel",
                        "Plates",
                        "Start",
                        "Finish",
                        "Duration Minutes",
                    ]
                ],
                use_container_width=True,
            )

            st.subheader("Summary by Sample Type")

            summary = (
                df.groupby("Sample Type")
                .agg(
                    Total_Samples_Processed=("Processed Samples", "sum"),
                    First_Start=("Start", "min"),
                    Final_Finish=("Finish", "max"),
                    Total_Cycles=("Sample Type", "count"),
                )
                .reset_index()
            )

            st.dataframe(summary, use_container_width=True)

            st.subheader("Gantt Chart")

            gantt_df = df.copy()
            gantt_df["Task"] = gantt_df["Sample Type"] + " - " + gantt_df["Plates"]

            fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="Task",
                color="Sample Type",
                text="Processed Samples",
            )

            fig.update_yaxes(autorange="reversed")

            fig.update_layout(
                height=700,
                xaxis_title="Time",
                yaxis_title="Processing Task",
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Enter your sample data, then click Generate OR-Tools Optimized Schedule.")
