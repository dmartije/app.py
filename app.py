import math
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from ortools.sat.python import cp_model


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(page_title="Sample Scheduler", layout="wide")
st.title("Sample Preparation Optimizer (OR-Tools + Plate Gantt)")

TOTAL_PLATES = 5
TIME_UNIT = 5
PLATES = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]

rules = {
    "Sublot": {"priority": 1, "minutes": 30, "personnel": 4, "capacity": 1},
    "Face": {"priority": 2, "minutes": 5, "personnel": 1, "capacity": 10},
    "Mine": {"priority": 3, "minutes": 10, "personnel": 3, "capacity": 2},
    "Lot Quality": {"priority": 4, "minutes": 30, "personnel": 1, "capacity": 1},
}


# ============================================================
# INPUT
# ============================================================

st.sidebar.header("Input")

start_time = st.sidebar.datetime_input(
    "Date and Time Received",
    value=datetime(2026, 5, 2, 8, 0)
)

personnel_total = st.sidebar.number_input(
    "Personnel Present",
    min_value=1,
    max_value=100,
    value=20
)

samples = {
    "Face": st.sidebar.number_input("Face Samples", min_value=0, max_value=1000, value=100),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, max_value=1000, value=15),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, max_value=1000, value=3),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, max_value=1000, value=1),
}

time_limit = st.sidebar.slider(
    "Solver Time Limit (seconds)",
    min_value=3,
    max_value=60,
    value=15
)


# ============================================================
# SOLVER
# ============================================================

def solve(samples):
    model = cp_model.CpModel()
    horizon = 200  # 200 units x 5 minutes = 1000 minutes maximum schedule window

    jobs = []

    for sample_type, qty in samples.items():
        if qty == 0:
            continue

        rule = rules[sample_type]
        duration_units = rule["minutes"] // TIME_UNIT

        max_batch = min(
            qty,
            personnel_total // rule["personnel"],
            TOTAL_PLATES * rule["capacity"],
        )

        for t in range(horizon):
            for q in range(1, max_batch + 1):
                personnel_needed = q * rule["personnel"]
                plates_needed = math.ceil(q / rule["capacity"])

                if personnel_needed > personnel_total or plates_needed > TOTAL_PLATES:
                    continue

                var = model.NewBoolVar(f"{sample_type}_{t}_{q}")

                jobs.append({
                    "var": var,
                    "type": sample_type,
                    "start": t,
                    "end": t + duration_units,
                    "qty": q,
                    "personnel": personnel_needed,
                    "plates": plates_needed,
                    "priority": rule["priority"],
                    "duration_minutes": rule["minutes"]
                })

    # Complete exact required sample quantity
    for sample_type, qty in samples.items():
        if qty == 0:
            continue

        model.Add(
            sum(j["qty"] * j["var"] for j in jobs if j["type"] == sample_type) == qty
        )

    # Personnel and plate constraints per time slot
    for t in range(horizon):
        model.Add(
            sum(
                j["personnel"] * j["var"]
                for j in jobs
                if j["start"] <= t < j["end"]
            ) <= personnel_total
        )

        model.Add(
            sum(
                j["plates"] * j["var"]
                for j in jobs
                if j["start"] <= t < j["end"]
            ) <= TOTAL_PLATES
        )

    # Makespan objective
    makespan = model.NewIntVar(0, horizon, "makespan")

    for j in jobs:
        model.Add(makespan >= j["end"]).OnlyEnforceIf(j["var"])

    # Strict priority objective:
    # 1. Minimize Sublot finish time
    # 2. Minimize Face finish time
    # 3. Minimize Mine finish time
    # 4. Minimize Lot Quality finish time
    # 5. Minimize overall finish time

    type_finish = {}

    for sample_type in rules.keys():
        if samples.get(sample_type, 0) > 0:
            type_finish[sample_type] = model.NewIntVar(0, horizon, f"{sample_type}_finish")

            for j in jobs:
                if j["type"] == sample_type:
                    model.Add(type_finish[sample_type] >= j["end"]).OnlyEnforceIf(j["var"])

    objective_terms = []

    if "Sublot" in type_finish:
        objective_terms.append(type_finish["Sublot"] * 100000000)

    if "Face" in type_finish:
        objective_terms.append(type_finish["Face"] * 1000000)

    if "Mine" in type_finish:
        objective_terms.append(type_finish["Mine"] * 10000)

    if "Lot Quality" in type_finish:
        objective_terms.append(type_finish["Lot Quality"] * 100)

    objective_terms.append(makespan)

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        status_text = "OPTIMAL"
        status_message = "✅ Optimal solution found. The solver proved this is the best schedule within the model rules."
    elif status == cp_model.FEASIBLE:
        status_text = "FEASIBLE"
        status_message = "⚠️ Feasible solution found. It may be near-optimal, but not mathematically proven within the time limit."
    else:
        raise ValueError("No valid schedule found. Try increasing solver time or check personnel/sample inputs.")

    result = []

    for j in jobs:
        if solver.Value(j["var"]) == 1:
            start_dt = start_time + timedelta(minutes=j["start"] * TIME_UNIT)
            finish_dt = start_time + timedelta(minutes=j["end"] * TIME_UNIT)

            result.append({
                "Type": j["type"],
                "Qty": j["qty"],
                "Personnel": j["personnel"],
                "PlatesNeeded": j["plates"],
                "Start": start_dt,
                "Finish": finish_dt,
                "Duration Minutes": j["duration_minutes"],
                "Priority": j["priority"]
            })

    return result, status_text, status_message


# ============================================================
# ASSIGN PHYSICAL PLATES
# ============================================================

def assign_plates(jobs):
    plate_free = {plate: start_time for plate in PLATES}
    output = []

    for job in sorted(jobs, key=lambda x: (x["Start"], x["Priority"])):
        needed = job["PlatesNeeded"]
        assigned = []

        for plate in PLATES:
            if plate_free[plate] <= job["Start"]:
                assigned.append(plate)
                if len(assigned) == needed:
                    break

        if len(assigned) < needed:
            assigned += ["Unassigned"] * (needed - len(assigned))

        for plate in assigned:
            if plate != "Unassigned":
                plate_free[plate] = job["Finish"]

        job_copy = job.copy()
        job_copy["Plate"] = ", ".join(assigned)
        output.append(job_copy)

    return output


# ============================================================
# RUN APP
# ============================================================

if st.button("Generate Optimized Schedule"):

    try:
        jobs, status, status_message = solve(samples)

        jobs = assign_plates(jobs)
        df = pd.DataFrame(jobs)

        if df.empty:
            st.warning("No samples entered.")
        else:
            st.info(f"Solver Status: {status}")
            st.write(status_message)

            # Add cycle number per sample type
            df = df.sort_values(["Type", "Start"])
            df["Cycle No."] = df.groupby("Type").cumcount() + 1
            df = df.sort_values(["Start", "Priority", "Type"])

            st.subheader("Detailed Schedule")

            st.dataframe(
                df[
                    [
                        "Type",
                        "Qty",
                        "Personnel",
                        "PlatesNeeded",
                        "Plate",
                        "Cycle No.",
                        "Start",
                        "Finish",
                        "Duration Minutes",
                    ]
                ],
                use_container_width=True
            )

            final_finish = df["Finish"].max()
            st.success(f"All samples completed by: {final_finish}")

            # ========================================================
            # SUMMARY BY SAMPLE TYPE
            # ========================================================

            st.subheader("Summary by Sample Type")

            summary_df = (
                df.groupby("Type")
                .agg(
                    Total_Samples_Processed=("Qty", "sum"),
                    First_Start=("Start", "min"),
                    Final_Finish=("Finish", "max"),
                    Total_Cycles=("Cycle No.", "max"),
                    Total_Duration_Minutes=("Duration Minutes", "sum"),
                    Max_Personnel_Used_At_One_Time=("Personnel", "max"),
                )
                .reset_index()
            )

            st.dataframe(summary_df, use_container_width=True)

            # ========================================================
            # PLATE GANTT CHART
            # ========================================================

            st.subheader("Plate Gantt Chart")

            gantt_rows = []

            for _, row in df.iterrows():
                plates = row["Plate"].split(", ")
                total_qty = row["Qty"]
                plate_count = len(plates)

                # distribute samples across plates
                base_qty = total_qty // plate_count
                remainder = total_qty % plate_count

                for i, plate in enumerate(plates):
                    qty_on_plate = base_qty + (1 if i < remainder else 0)

                    gantt_rows.append({
                        "Plate": plate,
                        "Task": row["Type"],
                        "Start": row["Start"],
                        "Finish": row["Finish"],
                        "Label": f"{row['Type']} ({qty_on_plate})",
                        "Cycle No.": row["Cycle No."],
                        "Personnel": row["Personnel"],
                    })

            gantt_df = pd.DataFrame(gantt_rows)

            color_map = {
                "Mine": "green",
                "Sublot": "orange",
                "Face": "blue",
                "Lot Quality": "red",
            }

            fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="Plate",
                color="Task",
                text="Label",
                color_discrete_map=color_map,
                hover_data={
                    "Cycle No.": True,
                    "Personnel": True,
                    "Start": True,
                    "Finish": True,
                }
            )

            fig.update_yaxes(autorange="reversed")
            fig.update_traces(textposition="inside", textfont_size=12)

            fig.update_layout(
                height=700,
                xaxis_title="Time",
                yaxis_title="Working Plate",
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Enter inputs then click Generate Optimized Schedule.")
