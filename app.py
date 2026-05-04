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
st.title("Sample Preparation Optimizer (Sorting + OR-Tools + Drying Gantts)")

TOTAL_PLATES = 5
TIME_UNIT = 5
PLATES = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]

# Reduction step rules
rules = {
    "Sublot": {"priority": 1, "minutes": 30, "personnel": 4, "capacity": 1},
    "Face": {"priority": 2, "minutes": 5, "personnel": 1, "capacity": 10},
    "Mine": {"priority": 3, "minutes": 10, "personnel": 3, "capacity": 2},
    "Lot Quality": {"priority": 4, "minutes": 30, "personnel": 1, "capacity": 1},
}

# Sorting time before reduction can start
sorting_minutes = {
    "Face": 60,
    "Mine": 30,
    "Sublot": 35,
    "Lot Quality": 30,
}

# Drying rules
drying_minutes = {
    "Sublot": 480,
    "Face": 480,
    "Mine": 480,
    "Lot Quality": 480,
}

SHELVES_PER_OVEN = 8
drying_capacity_per_shelf = {
    "Sublot": 4,
    "Face": 26,
    "Mine": 8,
    "Lot Quality": 1,
}

crushing_minutes_per_sample = {
    "Face": 3,
    "Mine": 3,
    "Sublot": 7,
    "Lot Quality": 10,
}


# ============================================================
# INPUT
# ============================================================

st.sidebar.header("Input")

receipt_time = st.sidebar.datetime_input(
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


st.sidebar.subheader("Drying Oven Availability")
default_shift_start = datetime(2026, 5, 2, 14, 0).time()
default_shift_end = datetime(2026, 5, 3, 6, 0).time()

window_start = st.sidebar.time_input("Higher-capacity window start", value=default_shift_start)
window_end = st.sidebar.time_input("Higher-capacity window end", value=default_shift_end)
ovens_high = st.sidebar.selectbox("Ovens operating during higher-capacity window", [1, 2], index=1)
ovens_low = st.sidebar.selectbox("Ovens operating outside that window", [1, 2], index=0)
max_face_drying_batch = st.sidebar.number_input("Max Face drying transfer batch", min_value=1, max_value=1000, value=150)


# ============================================================
# HELPER: CALCULATE HORIZON
# ============================================================

def calculate_horizon(samples):
    max_sort_units = max(
        sorting_minutes[sample_type] // TIME_UNIT
        for sample_type, qty in samples.items()
        if qty > 0
    ) if any(qty > 0 for qty in samples.values()) else 0

    total_reduction_units = 0

    for sample_type, qty in samples.items():
        if qty <= 0:
            continue

        rule = rules[sample_type]

        max_capacity = min(
            personnel_total // rule["personnel"],
            TOTAL_PLATES * rule["capacity"]
        )

        if max_capacity <= 0:
            continue

        cycles = math.ceil(qty / max_capacity)
        duration_units = rule["minutes"] // TIME_UNIT
        total_reduction_units += cycles * duration_units

    return max(200, max_sort_units + total_reduction_units + 50)


# ============================================================
# SOLVER
# ============================================================

def solve(samples):
    model = cp_model.CpModel()
    horizon = calculate_horizon(samples)

    jobs = []

    for sample_type, qty in samples.items():
        if qty == 0:
            continue

        rule = rules[sample_type]
        duration_units = rule["minutes"] // TIME_UNIT

        # Reduction cannot start until sorting is finished
        sorting_units = sorting_minutes[sample_type] // TIME_UNIT

        max_batch = min(
            qty,
            personnel_total // rule["personnel"],
            TOTAL_PLATES * rule["capacity"],
        )

        if max_batch <= 0:
            raise ValueError(f"Not enough personnel to process {sample_type}.")

        for t in range(sorting_units, horizon):
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
                    "duration_minutes": rule["minutes"],
                    "sorting_minutes": sorting_minutes[sample_type],
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

    # Strict priority objective
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
            sorting_end = receipt_time + timedelta(minutes=j["sorting_minutes"])
            reduction_start = receipt_time + timedelta(minutes=j["start"] * TIME_UNIT)
            reduction_finish = receipt_time + timedelta(minutes=j["end"] * TIME_UNIT)

            result.append({
                "Type": j["type"],
                "Qty": j["qty"],
                "Personnel": j["personnel"],
                "PlatesNeeded": j["plates"],
                "Receipt Time": receipt_time,
                "Sorting Minutes": j["sorting_minutes"],
                "Sorting End": sorting_end,
                "Start": reduction_start,
                "Finish": reduction_finish,
                "Duration Minutes": j["duration_minutes"],
                "Priority": j["priority"]
            })

    return result, status_text, status_message


# ============================================================
# ASSIGN PHYSICAL PLATES
# ============================================================

def assign_plates(jobs):
    plate_free = {plate: receipt_time for plate in PLATES}
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




def is_within_daily_window(ts, start_t, end_t):
    t = ts.time()
    if start_t <= end_t:
        return start_t <= t < end_t
    return t >= start_t or t < end_t


def ovens_available_at(ts, start_t, end_t, high, low):
    return high if is_within_daily_window(ts, start_t, end_t) else low


def allocate_drying_jobs(reduction_jobs):
    drying_jobs = []

    reduction_df = pd.DataFrame(reduction_jobs)
    if reduction_df.empty:
        return drying_jobs

    batch_limits = {
        "Face": int(max_face_drying_batch),
        "Mine": 10**9,
        "Sublot": 10**9,
        "Lot Quality": 10**9,
    }

    # Split reduction outputs into transfer batches that can start drying as soon as reduced.
    transfer_batches = []
    for _, r in reduction_df.sort_values(["Finish", "Priority", "Type"]).iterrows():
        sample_type = r["Type"]
        remaining = int(r["Qty"])
        cap = batch_limits.get(sample_type, 10**9)

        while remaining > 0:
            take = min(remaining, cap)
            transfer_batches.append({
                "Type": sample_type,
                "Qty": take,
                "Priority": int(r["Priority"]),
                "Ready Time": r["Finish"],
            })
            remaining -= take

    transfer_batches = sorted(transfer_batches, key=lambda x: (x["Ready Time"], x["Priority"]))

    batch_counter = {}
    for batch in transfer_batches:
        batch_counter[batch["Type"]] = batch_counter.get(batch["Type"], 0) + 1
        batch["Batch No"] = batch_counter[batch["Type"]]

    for batch in transfer_batches:
        sample_type = batch["Type"]
        qty = batch["Qty"]
        ready_time = batch["Ready Time"]

        shelf_capacity = drying_capacity_per_shelf[sample_type]
        shelves_needed = math.ceil(qty / shelf_capacity)
        duration = timedelta(minutes=drying_minutes[sample_type])

        current = ready_time
        assigned_shelves = []

        while not assigned_shelves:
            available_ovens = ovens_available_at(current, window_start, window_end, ovens_high, ovens_low)
            oven_candidates = [f"Oven {i}" for i in range(1, available_ovens + 1)]

            active_slots = []
            for dj in drying_jobs:
                if not (current + duration <= dj["Start"] or current >= dj["Finish"]):
                    active_slots.extend(dj["Shelf Allocations"])

            free_slots = []
            for oven in oven_candidates:
                for shelf in range(1, SHELVES_PER_OVEN + 1):
                    slot = f"{oven}-Shelf {shelf}"
                    if slot not in active_slots:
                        free_slots.append(slot)

            assigned_shelves = free_slots[:shelves_needed]

            if len(assigned_shelves) < shelves_needed:
                assigned_shelves = []
                current += timedelta(minutes=TIME_UNIT)

        drying_jobs.append({
            "Type": sample_type,
            "Qty": qty,
            "Batch No": batch["Batch No"],
            "Priority": batch["Priority"],
            "Reduction Finish": ready_time,
            "Start": current,
            "Finish": current + duration,
            "Duration Minutes": drying_minutes[sample_type],
            "Shelves Needed": shelves_needed,
            "Shelf Allocations": assigned_shelves,
        })

    return drying_jobs


def active_reduction_personnel_at(ts, reduction_jobs):
    total = 0
    for job in reduction_jobs:
        if job["Start"] <= ts < job["Finish"]:
            total += job["Personnel"]
    return total


def active_crushing_personnel_at(ts, crushing_jobs):
    total = 0
    for job in crushing_jobs:
        if job["Start"] <= ts < job["Finish"]:
            total += job["Assigned Personnel"]
    return total


def allocate_crushing_jobs(drying_jobs, reduction_jobs):
    crushing_jobs = []

    if not drying_jobs:
        return crushing_jobs

    for batch in sorted(drying_jobs, key=lambda x: (x["Finish"], x["Priority"])):
        sample_type = batch["Type"]
        qty = int(batch["Qty"])
        ready_time = batch["Finish"]
        minutes_per_sample = crushing_minutes_per_sample[sample_type]

        # Crushing is tied to the specific drying batch and cannot start before that batch dries.
        current = ready_time
        assigned_personnel = 0

        while assigned_personnel <= 0:
            used_reduction = active_reduction_personnel_at(current, reduction_jobs)
            used_crushing = active_crushing_personnel_at(current, crushing_jobs)
            available = personnel_total - used_reduction - used_crushing

            if available > 0:
                assigned_personnel = available
            else:
                current += timedelta(minutes=TIME_UNIT)

        duration_minutes = math.ceil((qty * minutes_per_sample) / assigned_personnel)
        finish = current + timedelta(minutes=duration_minutes)

        crushing_jobs.append({
            "Type": sample_type,
            "Qty": qty,
            "Batch No": batch.get("Batch No", 1),
            "Priority": batch["Priority"],
            "Drying Finish": ready_time,
            "Start": current,
            "Finish": finish,
            "Assigned Personnel": assigned_personnel,
            "Duration Minutes": duration_minutes,
        })

    return crushing_jobs
    
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
                        "Receipt Time",
                        "Sorting Minutes",
                        "Sorting End",
                        "Start",
                        "Finish",
                        "Duration Minutes",
                    ]
                ],
                use_container_width=True
            )

            drying_jobs = allocate_drying_jobs(jobs)
            drying_df = pd.DataFrame(drying_jobs)
            crushing_jobs = allocate_crushing_jobs(drying_jobs, jobs)
            crushing_df = pd.DataFrame(crushing_jobs)

            final_reduction_finish = df["Finish"].max()
            final_drying_finish = drying_df["Finish"].max() if not drying_df.empty else final_reduction_finish
            final_crushing_finish = crushing_df["Finish"].max() if not crushing_df.empty else final_drying_finish
            st.success(f"Reduction completed by: {final_reduction_finish}")
            st.success(f"Sorting + Reduction + Drying completed by: {final_drying_finish}")
            st.success(f"Sorting + Reduction + Drying + Crushing completed by: {final_crushing_finish}")
            
            st.subheader("Summary by Sample Type")

            summary_df = (
                df.groupby("Type")
                .agg(
                    Total_Samples_Processed=("Qty", "sum"),
                    Receipt_Time=("Receipt Time", "min"),
                    Sorting_End=("Sorting End", "min"),
                    First_Reduction_Start=("Start", "min"),
                    Final_Reduction_Finish=("Finish", "max"),
                    Total_Cycles=("Cycle No.", "max"),
                    Total_Reduction_Minutes=("Duration Minutes", "sum"),
                    Max_Personnel_Used_At_One_Time=("Personnel", "max"),
                )
                .reset_index()
            )
            if not drying_df.empty:
                drying_summary = drying_df.groupby("Type").agg(
                    First_Drying_Start=("Start", "min"),
                    Final_Drying_Finish=("Finish", "max"),
                ).reset_index()
                drying_summary["Total_Drying_Minutes"] = (
                    (drying_summary["Final_Drying_Finish"] - drying_summary["First_Drying_Start"])
                    .dt.total_seconds() // 60
                ).astype(int)
                summary_df = summary_df.merge(drying_summary, on="Type", how="left")

            if not crushing_df.empty:
                # Total crushing minutes = elapsed window from first crushing start to last crushing finish per sample type.
                # This is intentionally not a cumulative sum of batch durations.
                crushing_summary = crushing_df.groupby("Type").agg(
                    First_Crushing_Start=("Start", "min"),
                    Final_Crushing_Finish=("Finish", "max"),
                ).reset_index()
                crushing_summary["Total_Crushing_Minutes"] = (
                    (crushing_summary["Final_Crushing_Finish"] - crushing_summary["First_Crushing_Start"])
                    .dt.total_seconds()
                    .div(60)
                    .round()
                    .astype(int)
                )
                summary_df = summary_df.merge(crushing_summary, on="Type", how="left")

            st.dataframe(summary_df, use_container_width=True)

            st.subheader("Plate Gantt Chart")

            gantt_rows = []

            for _, row in df.iterrows():
                plates = row["Plate"].split(", ")
                total_qty = row["Qty"]
                plate_count = len(plates)

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

            st.subheader("Drying Oven Gantt Chart")
            drying_rows = []
            sample_short = {"Face": "FS", "Mine": "MS", "Sublot": "SS", "Lot Quality": "LQ"}
            for _, row in drying_df.iterrows():
                for slot in row["Shelf Allocations"]:
                    oven_name, shelf_name = slot.split("-Shelf ")
                    oven_num = oven_name.split(" ")[-1]
                    label = f"{sample_short.get(row['Type'], row['Type'][:2].upper())} {oven_num}-{shelf_name}"
                    drying_rows.append({
                        "Oven": oven_name,
                        "Shelf Slot": slot,
                        "Task": row["Type"],
                        "Start": row["Start"],
                        "Finish": row["Finish"],
                        "Label": label,
                    })

            if drying_rows:
                drying_gantt_df = pd.DataFrame(drying_rows)
                fig_dry = px.timeline(
                    drying_gantt_df,
                    x_start="Start",
                    x_end="Finish",
                    y="Shelf Slot",
                    color="Task",
                    text="Label",
                    color_discrete_map=color_map,
                )
                fig_dry.update_yaxes(autorange="reversed")
                fig_dry.update_layout(height=650, xaxis_title="Time", yaxis_title="Drying Oven Shelf")
                st.plotly_chart(fig_dry, use_container_width=True)

            st.subheader("Crushing Gantt Chart")
            if not crushing_df.empty:
                crushing_plot_df = crushing_df.copy()
                crushing_plot_df["Lane"] = crushing_plot_df.apply(
                    lambda r: f"{r['Type']} (P{r['Assigned Personnel']})", axis=1
                )
                fig_crush = px.timeline(
                    crushing_plot_df,
                    x_start="Start",
                    x_end="Finish",
                    y="Lane",
                    color="Type",
                    text="Qty",
                    color_discrete_map=color_map,
                    hover_data={"Assigned Personnel": True, "Qty": True}
                )
                fig_crush.update_yaxes(autorange="reversed")
                fig_crush.update_layout(height=500, xaxis_title="Time", yaxis_title="Crushing Allocation")
                st.plotly_chart(fig_crush, use_container_width=True)

            st.subheader("Overall Step Gantt by Sample Type")
            overall_rows = []
            for sample_type in summary_df["Type"]:
                type_rows = df[df["Type"] == sample_type]
                if type_rows.empty:
                    continue
                sorting_start = type_rows["Receipt Time"].min()
                sorting_end = type_rows["Sorting End"].min()
                reduction_start = type_rows["Start"].min()
                reduction_end = type_rows["Finish"].max()

                overall_rows.append({"Type": sample_type, "Step": "Sorting", "Start": sorting_start, "Finish": sorting_end})
                overall_rows.append({"Type": sample_type, "Step": "Reduction", "Start": reduction_start, "Finish": reduction_end})

                drows = drying_df[drying_df["Type"] == sample_type]
                if not drows.empty:
                    overall_rows.append({"Type": sample_type, "Step": "Drying", "Start": drows["Start"].min(), "Finish": drows["Finish"].max()})

                crows = crushing_df[crushing_df["Type"] == sample_type]
                if not crows.empty:
                    overall_rows.append({"Type": sample_type, "Step": "Crushing", "Start": crows["Start"].min(), "Finish": crows["Finish"].max()})

            if overall_rows:
                overall_df = pd.DataFrame(overall_rows)
                fig_overall = px.timeline(overall_df, x_start="Start", x_end="Finish", y="Type", color="Step", text="Step")
                fig_overall.update_yaxes(autorange="reversed")
                fig_overall.update_layout(height=450, xaxis_title="Time", yaxis_title="Sample Type")
                st.plotly_chart(fig_overall, use_container_width=True)
                
    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Enter inputs then click Generate Optimized Schedule.")
