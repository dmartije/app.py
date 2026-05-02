import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from itertools import product

st.set_page_config(page_title="Sample Preparation Scheduler", layout="wide")

st.title("Sample Preparation Scheduling Optimizer")

# -----------------------------
# SAMPLE RULES
# -----------------------------
rules = {
    "Sublot": {
        "priority": 1,
        "minutes": 15,
        "group_size": 4,
        "plate_capacity": 1
    },
    "Face": {
        "priority": 2,
        "minutes": 5,
        "group_size": 1,
        "plate_capacity": 10
    },
    "Mine": {
        "priority": 3,
        "minutes": 10,
        "group_size": 3,
        "plate_capacity": 2
    },
    "Lot Quality": {
        "priority": 4,
        "minutes": 15,
        "group_size": 1,
        "plate_capacity": 1
    }
}

# -----------------------------
# INPUT FORM
# -----------------------------
st.sidebar.header("Input Data")

received_datetime = st.sidebar.datetime_input(
    "Date and Time Received",
    value=datetime(2026, 5, 2, 8, 0)
)

total_personnel = st.sidebar.number_input(
    "Personnel Present",
    min_value=1,
    max_value=100,
    value=20,
    step=1
)

samples = {
    "Face": st.sidebar.number_input("Face Samples", min_value=0, value=10, step=1),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, value=2, step=1),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, value=2, step=1),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, value=1, step=1)
}

total_plates = 5

active_types = [s for s, qty in samples.items() if qty > 0]

# -----------------------------
# PROCESSING TIME FUNCTION
# -----------------------------
def calculate_duration(sample_type, sample_count, personnel, plates):
    rule = rules[sample_type]

    if sample_count <= 0 or personnel <= 0 or plates <= 0:
        return None

    group_size = rule["group_size"]
    groups = personnel // group_size

    if groups <= 0:
        return None

    capacity_per_cycle = groups * plates * rule["plate_capacity"]

    if capacity_per_cycle <= 0:
        return None

    cycles = -(-sample_count // capacity_per_cycle)  # ceiling division
    duration_minutes = cycles * rule["minutes"]

    return duration_minutes

# -----------------------------
# BRUTE FORCE OPTIMIZER
# -----------------------------
def find_best_schedule(samples, total_personnel, total_plates, start_time):
    active = [s for s, qty in samples.items() if qty > 0]

    if not active:
        return [], None

    best_schedule = None
    best_finish = None
    best_score = None

    # Generate possible plate allocations
    plate_ranges = [range(1, total_plates + 1) for _ in active]

    for plate_allocation in product(*plate_ranges):
        if sum(plate_allocation) > total_plates:
            continue

        # Generate possible personnel allocations
        personnel_ranges = [range(1, total_personnel + 1) for _ in active]

        for personnel_allocation in product(*personnel_ranges):
            if sum(personnel_allocation) > total_personnel:
                continue

            schedule = []
            max_finish = start_time
            valid = True

            for sample_type, personnel, plates in zip(active, personnel_allocation, plate_allocation):
                duration = calculate_duration(
                    sample_type,
                    samples[sample_type],
                    personnel,
                    plates
                )

                if duration is None:
                    valid = False
                    break

                finish_time = start_time + timedelta(minutes=duration)

                schedule.append({
                    "Sample Type": sample_type,
                    "Samples": samples[sample_type],
                    "Personnel Assigned": personnel,
                    "Plates Assigned": plates,
                    "Start": start_time,
                    "Finish": finish_time,
                    "Duration Minutes": duration,
                    "Priority": rules[sample_type]["priority"]
                })

                if finish_time > max_finish:
                    max_finish = finish_time

            if not valid:
                continue

            # Objective:
            # 1. Minimize latest finish time
            # 2. Give slight preference to higher-priority samples finishing earlier
            priority_score = sum(
                item["Priority"] * item["Duration Minutes"]
                for item in schedule
            )

            total_minutes = (max_finish - start_time).total_seconds() / 60

            score = (total_minutes, priority_score)

            if best_score is None or score < best_score:
                best_score = score
                best_finish = max_finish
                best_schedule = schedule

    return best_schedule, best_finish

# -----------------------------
# RUN OPTIMIZER
# -----------------------------
if st.button("Generate Best Schedule"):
    schedule, final_finish = find_best_schedule(
        samples,
        total_personnel,
        total_plates,
        received_datetime
    )

    if not schedule:
        st.error("No valid schedule found. Please check personnel and sample inputs.")
    else:
        df = pd.DataFrame(schedule)
        df = df.sort_values("Priority")

        st.subheader("Best Personnel and Plate Allocation")
        st.dataframe(
            df[
                [
                    "Sample Type",
                    "Samples",
                    "Personnel Assigned",
                    "Plates Assigned",
                    "Start",
                    "Finish",
                    "Duration Minutes"
                ]
            ],
            use_container_width=True
        )

        st.success(f"All samples completed by: {final_finish.strftime('%B %d, %Y %I:%M %p')}")

        # Assign actual plate numbers
        st.subheader("Plate Assignment")

        plate_number = 1
        plate_rows = []

        for _, row in df.iterrows():
            assigned_plates = []
            for _ in range(int(row["Plates Assigned"])):
                assigned_plates.append(f"Plate {plate_number}")
                plate_number += 1

            plate_rows.append({
                "Sample Type": row["Sample Type"],
                "Assigned Plates": ", ".join(assigned_plates),
                "Personnel Assigned": row["Personnel Assigned"],
                "Start": row["Start"],
                "Finish": row["Finish"]
            })

        plate_df = pd.DataFrame(plate_rows)
        st.dataframe(plate_df, use_container_width=True)

        # Gantt chart
        st.subheader("Gantt Chart")

        gantt_df = df.copy()
        gantt_df["Task"] = gantt_df["Sample Type"]

        fig = px.timeline(
            gantt_df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Sample Type",
            text="Personnel Assigned"
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=500)

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter your sample data on the left, then click Generate Best Schedule.")
