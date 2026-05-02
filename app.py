# ============================================================
# SAMPLE PREPARATION SCHEDULING OPTIMIZER
# ------------------------------------------------------------
# This Streamlit app allows you to input:
# - number of samples received per type
# - date and time received
# - number of personnel present
#
# The program will:
# - calculate the best personnel allocation
# - calculate estimated finish time
# - assign available plates
# - generate a Gantt chart
#
# Sample Types:
# 1. Sublot
# 2. Face
# 3. Mine
# 4. Lot Quality
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from itertools import product
import math


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Sample Preparation Scheduler",
    layout="wide"
)

st.title("Sample Preparation Scheduling Optimizer")


# ============================================================
# RULES / PROCESSING STANDARDS
# ------------------------------------------------------------
# You can edit this part if processing standards change.
#
# minutes:
#   processing time per sample/group
#
# group_size:
#   number of personnel required to make 1 working group
#
# plate_capacity:
#   how many samples can be placed in one plate
#
# priority:
#   lower number = higher priority
# ============================================================

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


# ============================================================
# USER INPUT SECTION
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

total_plates = 5


# ============================================================
# PROCESSING TIME CALCULATION
# ------------------------------------------------------------
# This function calculates the processing duration.
#
# Face:
#   samples / personnel * 5 minutes
#
# Mine:
#   samples / number of 3-person groups * 10 minutes
#
# Sublot:
#   samples / number of 4-person groups * 15 minutes
#
# Lot Quality:
#   samples / personnel * 15 minutes
#
# Plate capacity is NOT used as a speed multiplier.
# It is used only to check how many plates are needed.
# ============================================================

def calculate_duration(sample_type, sample_count, personnel):
    rule = rules[sample_type]

    if sample_count <= 0 or personnel <= 0:
        return None

    group_size = rule["group_size"]
    groups = personnel // group_size

    if groups <= 0:
        return None

    duration_minutes = math.ceil((sample_count / groups) * rule["minutes"])

    return duration_minutes


# ============================================================
# REQUIRED PLATE CALCULATION
# ------------------------------------------------------------
# This calculates the minimum number of plates needed based on
# sample quantity and plate capacity.
#
# Example:
# Face = 10 samples per plate
# 212 Face samples = ceil(212 / 10) = 22 plate-loads
#
# Since only 5 plates exist, this does not mean 22 physical plates.
# It means several plate cycles may be needed.
# ============================================================

def calculate_plate_loads(sample_type, sample_count):
    capacity = rules[sample_type]["plate_capacity"]

    if sample_count <= 0:
        return 0

    return math.ceil(sample_count / capacity)


# ============================================================
# OPTIMIZER
# ------------------------------------------------------------
# This tries different personnel allocations and chooses the
# allocation with the least total processing time.
#
# The program also prefers:
# 1. faster total completion
# 2. higher priority samples finishing earlier
# 3. using more available personnel
#
# Important:
# This is a practical optimizer, not yet a full industrial
# scheduling engine. But it already follows the correct
# processing time logic.
# ============================================================

def find_best_schedule(samples, total_personnel, total_plates, start_time):
    active_types = [sample_type for sample_type, qty in samples.items() if qty > 0]

    if not active_types:
        return [], None

    best_schedule = None
    best_finish_time = None
    best_score = None

    personnel_ranges = [
        range(1, total_personnel + 1)
        for _ in active_types
    ]

    for personnel_allocation in product(*personnel_ranges):

        # Do not exceed total available personnel
        if sum(personnel_allocation) > total_personnel:
            continue

        schedule = []
        valid = True
        latest_finish = start_time

        for sample_type, personnel in zip(active_types, personnel_allocation):

            duration_minutes = calculate_duration(
                sample_type,
                samples[sample_type],
                personnel
            )

            if duration_minutes is None:
                valid = False
                break

            start = start_time
            finish = start + timedelta(minutes=duration_minutes)

            required_plate_loads = calculate_plate_loads(
                sample_type,
                samples[sample_type]
            )

            schedule.append({
                "Sample Type": sample_type,
                "Samples": samples[sample_type],
                "Personnel Assigned": personnel,
                "Plate Loads Required": required_plate_loads,
                "Start": start,
                "Finish": finish,
                "Duration Minutes": duration_minutes,
                "Priority": rules[sample_type]["priority"]
            })

            if finish > latest_finish:
                latest_finish = finish

        if not valid:
            continue

        # Score determines the "best" schedule
        total_minutes = (latest_finish - start_time).total_seconds() / 60

        priority_score = sum(
            item["Priority"] * item["Duration Minutes"]
            for item in schedule
        )

        unused_personnel = total_personnel - sum(personnel_allocation)

        score = (
            total_minutes,
            priority_score,
            unused_personnel
        )

        if best_score is None or score < best_score:
            best_score = score
            best_schedule = schedule
            best_finish_time = latest_finish

    return best_schedule, best_finish_time


# ============================================================
# PLATE ASSIGNMENT
# ------------------------------------------------------------
# This assigns available physical plates from Plate 1 to Plate 5.
#
# Since plates can be reused after a cycle, this shows the
# working plates assigned to each active sample type.
# ============================================================

def assign_plates(schedule, total_plates):
    plate_rows = []

    plate_number = 1

    for item in schedule:
        sample_type = item["Sample Type"]

        # Assign at least 1 physical plate per active sample type
        assigned_plate = f"Plate {plate_number}"

        plate_rows.append({
            "Sample Type": sample_type,
            "Assigned Plate": assigned_plate,
            "Personnel Assigned": item["Personnel Assigned"],
            "Plate Loads Required": item["Plate Loads Required"],
            "Start": item["Start"],
            "Finish": item["Finish"]
        })

        plate_number += 1

        if plate_number > total_plates:
            plate_number = 1

    return pd.DataFrame(plate_rows)


# ============================================================
# RUN BUTTON
# ============================================================

if st.button("Generate Best Schedule"):

    schedule, final_finish = find_best_schedule(
        samples=samples,
        total_personnel=total_personnel,
        total_plates=total_plates,
        start_time=received_datetime
    )

    if not schedule:
        st.error("No valid schedule found. Please check your inputs.")
    else:
        df = pd.DataFrame(schedule)
        df = df.sort_values("Priority")

        # ====================================================
        # RESULT TABLE
        # ====================================================

        st.subheader("Best Personnel Allocation")

        st.dataframe(
            df[
                [
                    "Sample Type",
                    "Samples",
                    "Personnel Assigned",
                    "Plate Loads Required",
                    "Start",
                    "Finish",
                    "Duration Minutes"
                ]
            ],
            use_container_width=True
        )

        st.success(
            f"All samples completed by: "
            f"{final_finish.strftime('%B %d, %Y %I:%M %p')}"
        )

        # ====================================================
        # PLATE ASSIGNMENT TABLE
        # ====================================================

        st.subheader("Plate Assignment")

        plate_df = assign_plates(df.to_dict("records"), total_plates)

        st.dataframe(
            plate_df,
            use_container_width=True
        )

        # ====================================================
        # GANTT CHART
        # ====================================================

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
