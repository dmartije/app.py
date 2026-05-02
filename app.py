import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from itertools import product
import math

# ============================================================
# SAMPLE PREPARATION SCHEDULING OPTIMIZER
# ============================================================

st.set_page_config(page_title="Sample Preparation Scheduler", layout="wide")
st.title("Sample Preparation Scheduling Optimizer")

# ============================================================
# PROCESS RULES
# ============================================================

rules = {
    "Sublot": {
        "priority": 1,
        "minutes_per_cycle": 15,
        "personnel_per_sample": 4,
        "plate_capacity": 1
    },
    "Face": {
        "priority": 2,
        "minutes_per_cycle": 5,
        "personnel_per_sample": 1,
        "plate_capacity": 10
    },
    "Mine": {
        "priority": 3,
        "minutes_per_cycle": 10,
        "personnel_per_sample": 3,
        "plate_capacity": 2
    },
    "Lot Quality": {
        "priority": 4,
        "minutes_per_cycle": 15,
        "personnel_per_sample": 1,
        "plate_capacity": 1
    }
}

TOTAL_PLATES = 5

# ============================================================
# INPUT SECTION
# ============================================================

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
    "Face": st.sidebar.number_input("Face Samples", min_value=0, value=212, step=1),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, value=0, step=1),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, value=0, step=1),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, value=0, step=1)
}

# ============================================================
# FUNCTION: CALCULATE PROCESSING TIME BY CYCLES
# ============================================================
# Example for Face:
# 212 samples
# 20 personnel
# 1 personnel per sample
# 2 plates used because each plate holds 10 FS
#
# Simultaneous capacity = min(personnel capacity, plate capacity)
# personnel capacity = 20 / 1 = 20 samples
# plate capacity = 2 plates x 10 FS = 20 samples
# samples per cycle = 20
# cycles = ceil(212 / 20) = 11
# duration = 11 x 5 minutes = 55 minutes
# ============================================================

def calculate_duration(sample_type, sample_count, personnel, plates):
    rule = rules[sample_type]

    if sample_count <= 0 or personnel <= 0 or plates <= 0:
        return None

    personnel_capacity = personnel // rule["personnel_per_sample"]
    plate_capacity = plates * rule["plate_capacity"]

    samples_per_cycle = min(personnel_capacity, plate_capacity)

    if samples_per_cycle <= 0:
        return None

    cycles = math.ceil(sample_count / samples_per_cycle)
    duration_minutes = cycles * rule["minutes_per_cycle"]

    return duration_minutes, cycles, samples_per_cycle

# ============================================================
# OPTIMIZER
# ============================================================

def find_best_schedule(samples, total_personnel, total_plates, start_time):
    active_types = [sample_type for sample_type, qty in samples.items() if qty > 0]

    if not active_types:
        return [], None

    best_schedule = None
    best_finish = None
    best_score = None

    personnel_ranges = [range(1, total_personnel + 1) for _ in active_types]
    plate_ranges = [range(1, total_plates + 1) for _ in active_types]

    for personnel_allocation in product(*personnel_ranges):

        if sum(personnel_allocation) > total_personnel:
            continue

        for plate_allocation in product(*plate_ranges):

            if sum(plate_allocation) > total_plates:
                continue

            schedule = []
            latest_finish = start_time
            valid = True

            for sample_type, personnel, plates in zip(
                active_types,
                personnel_allocation,
                plate_allocation
            ):
                result = calculate_duration(
                    sample_type,
                    samples[sample_type],
                    personnel,
                    plates
                )

                if result is None:
                    valid = False
                    break

                duration_minutes, cycles, samples_per_cycle = result

                finish = start_time + timedelta(minutes=duration_minutes)

                schedule.append({
                    "Sample Type": sample_type,
                    "Samples": samples[sample_type],
                    "Personnel Assigned": personnel,
                    "Plates Assigned": plates,
                    "Samples Per Cycle": samples_per_cycle,
                    "Number of Cycles": cycles,
                    "Minutes Per Cycle": rules[sample_type]["minutes_per_cycle"],
                    "Duration Minutes": duration_minutes,
                    "Start": start_time,
                    "Finish": finish,
                    "Priority": rules[sample_type]["priority"]
                })

                if finish > latest_finish:
                    latest_finish = finish

            if not valid:
                continue

            total_duration = (latest_finish - start_time).total_seconds() / 60

            priority_score = sum(
                item["Priority"] * item["Duration Minutes"]
                for item in schedule
            )

            unused_personnel = total_personnel - sum(personnel_allocation)
            unused_plates = total_plates - sum(plate_allocation)

            # Best result is:
            # 1. shortest finish time
            # 2. better priority handling
            # 3. fewer unused personnel
            # 4. fewer unnecessary plates
            score = (
                total_duration,
                priority_score,
                unused_personnel,
                unused_plates
            )

            if best_score is None or score < best_score:
                best_score = score
                best_schedule = schedule
                best_finish = latest_finish

    return best_schedule, best_finish

# ============================================================
# ASSIGN ACTUAL PLATE NUMBERS
# ============================================================

def assign_plate_numbers(schedule):
    plate_number = 1
    rows = []

    for item in schedule:
        assigned_plates = []

        for _ in range(item["Plates Assigned"]):
            assigned_plates.append(f"Plate {plate_number}")
            plate_number += 1

        rows.append({
            "Sample Type": item["Sample Type"],
            "Assigned Plates": ", ".join(assigned_plates),
            "Personnel Assigned": item["Personnel Assigned"],
            "Samples Per Cycle": item["Samples Per Cycle"],
            "Number of Cycles": item["Number of Cycles"],
            "Start": item["Start"],
            "Finish": item["Finish"]
        })

    return pd.DataFrame(rows)

# ============================================================
# RUN APP
# ============================================================

if st.button("Generate Best Schedule"):

    schedule, final_finish = find_best_schedule(
        samples=samples,
        total_personnel=total_personnel,
        total_plates=TOTAL_PLATES,
        start_time=received_datetime
    )

    if not schedule:
        st.error("No valid schedule found. Please check your inputs.")
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
                    "Samples Per Cycle",
                    "Number of Cycles",
                    "Minutes Per Cycle",
                    "Duration Minutes",
                    "Start",
                    "Finish"
                ]
            ],
            use_container_width=True
        )

        st.success(
            f"All samples completed by: "
            f"{final_finish.strftime('%B %d, %Y %I:%M %p')}"
        )

        st.subheader("Physical Plate Assignment")

        plate_df = assign_plate_numbers(df.to_dict("records"))

        st.dataframe(
            plate_df,
            use_container_width=True
        )

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

        fig.update_layout(
            height=500,
            xaxis_title="Time",
            yaxis_title="Sample Type"
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter your sample data on the left, then click Generate Best Schedule.")
