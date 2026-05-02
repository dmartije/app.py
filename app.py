# ============================================================
# FAST SAMPLE PREPARATION SCHEDULER
# ============================================================
# This app:
# - Accepts sample quantities and personnel count
# - Uses 5 fixed working plates
# - Prioritizes Sublot > Face > Mine > Lot Quality
# - Reuses personnel and plates after each cycle
# - Generates a schedule table and Gantt chart
#
# This is a FAST practical scheduler.
# It is designed to run quickly and avoid the slow optimization error.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import math

# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(page_title="Fast Sample Scheduler", layout="wide")
st.title("Fast Sample Preparation Scheduler")

# ============================================================
# FIXED RESOURCES
# ============================================================

TOTAL_PLATES = 5
PLATE_IDS = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]

# ============================================================
# PROCESSING RULES
# ============================================================
# priority:
#   lower number = higher priority
#
# minutes_per_cycle:
#   duration of one cycle
#
# personnel_per_sample:
#   personnel needed to process 1 sample at the same time
#
# plate_capacity:
#   sample capacity per plate
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

# ============================================================
# INPUT SECTION
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
    value=20,
    step=1
)

samples = {
    "Face": st.sidebar.number_input("Face Samples", min_value=0, value=100, step=1),
    "Mine": st.sidebar.number_input("Mine Samples", min_value=0, value=15, step=1),
    "Sublot": st.sidebar.number_input("Sublot Samples", min_value=0, value=3, step=1),
    "Lot Quality": st.sidebar.number_input("Lot Quality Samples", min_value=0, value=1, step=1)
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_priority_order():
    """Returns sample types in priority order."""
    return sorted(rules.keys(), key=lambda x: rules[x]["priority"])


def max_samples_this_cycle(sample_type, remaining, available_personnel, available_plates):
    """
    Calculates how many samples can be processed in the current cycle.

    Limited by:
    - remaining samples
    - available personnel
    - available plates
    """

    rule = rules[sample_type]

    by_personnel = available_personnel // rule["personnel_per_sample"]
    by_plates = available_plates * rule["plate_capacity"]

    return min(remaining, by_personnel, by_plates)


def required_plates(sample_type, samples_to_process):
    """
    Calculates how many plates are needed for the samples to process.
    """

    rule = rules[sample_type]
    return math.ceil(samples_to_process / rule["plate_capacity"])


def required_personnel(sample_type, samples_to_process):
    """
    Calculates how many personnel are needed for the samples to process.
    """

    rule = rules[sample_type]
    return samples_to_process * rule["personnel_per_sample"]


def assign_plates(available_plates, number_needed):
    """
    Assigns physical plate numbers.
    """

    return available_plates[:number_needed]


# ============================================================
# FAST GREEDY SCHEDULER
# ============================================================
# How it works:
# 1. Start at received date/time.
# 2. Check remaining samples.
# 3. Assign available personnel and plates by priority.
# 4. Start cycles simultaneously.
# 5. Move time to the next finished cycle.
# 6. Free resources and repeat until all samples are done.
# ============================================================

def fast_schedule(samples, total_personnel, start_time):
    remaining = {k: v for k, v in samples.items() if v > 0}
    current_time = start_time
    running_jobs = []
    completed_jobs = []

    max_loop = 10000
    loop_count = 0

    while remaining or running_jobs:
        loop_count += 1

        if loop_count > max_loop:
            raise RuntimeError("Scheduler stopped because maximum loop limit was reached.")

        # ----------------------------------------------------
        # Step 1: Complete jobs that finish at current_time
        # ----------------------------------------------------
        still_running = []

        for job in running_jobs:
            if job["Finish"] <= current_time:
                completed_jobs.append(job)
            else:
                still_running.append(job)

        running_jobs = still_running

        # ----------------------------------------------------
        # Step 2: Calculate available resources
        # ----------------------------------------------------
        used_personnel = sum(job["Personnel"] for job in running_jobs)

        used_plates = []
        for job in running_jobs:
            used_plates.extend(job["Plates"])

        available_personnel = total_personnel - used_personnel
        available_plates = [p for p in PLATE_IDS if p not in used_plates]

        # ----------------------------------------------------
        # Step 3: Assign new work by priority
        # ----------------------------------------------------
        started_any_job = False

        for sample_type in get_priority_order():

            if sample_type not in remaining:
                continue

            if remaining[sample_type] <= 0:
                continue

            if available_personnel <= 0 or len(available_plates) <= 0:
                break

            samples_can_process = max_samples_this_cycle(
                sample_type=sample_type,
                remaining=remaining[sample_type],
                available_personnel=available_personnel,
                available_plates=len(available_plates)
            )

            if samples_can_process <= 0:
                continue

            plates_needed = required_plates(sample_type, samples_can_process)
            personnel_needed = required_personnel(sample_type, samples_can_process)

            assigned_plates = assign_plates(available_plates, plates_needed)

            finish_time = current_time + timedelta(
                minutes=rules[sample_type]["minutes_per_cycle"]
            )

            job = {
                "Sample Type": sample_type,
                "Processed Samples": samples_can_process,
                "Personnel": personnel_needed,
                "Plates": assigned_plates,
                "Start": current_time,
                "Finish": finish_time,
                "Duration Minutes": rules[sample_type]["minutes_per_cycle"],
                "Priority": rules[sample_type]["priority"]
            }

            running_jobs.append(job)

            remaining[sample_type] -= samples_can_process

            if remaining[sample_type] <= 0:
                del remaining[sample_type]

            available_personnel -= personnel_needed

            for plate in assigned_plates:
                available_plates.remove(plate)

            started_any_job = True

        # ----------------------------------------------------
        # Step 4: Advance time
        # ----------------------------------------------------
        if running_jobs:
            next_finish = min(job["Finish"] for job in running_jobs)

            if next_finish > current_time:
                current_time = next_finish
        elif not started_any_job and remaining:
            raise RuntimeError("No work could be scheduled. Check personnel and plate rules.")

    return completed_jobs


# ============================================================
# RUN APP
# ============================================================

if st.button("Generate Fast Schedule"):

    try:
        jobs = fast_schedule(
            samples=samples,
            total_personnel=total_personnel,
            start_time=start_datetime
        )

        if not jobs:
            st.warning("No samples entered.")
        else:
            df = pd.DataFrame(jobs)
            df["Plates"] = df["Plates"].apply(lambda x: ", ".join(x))
            df = df.sort_values(["Start", "Priority"])

            final_finish = df["Finish"].max()

            st.success(
                f"All samples completed by: {final_finish.strftime('%B %d, %Y %I:%M %p')}"
            )

            st.subheader("Detailed Schedule")

            st.dataframe(
                df[
                    [
                        "Sample Type",
                        "Processed Samples",
                        "Personnel",
                        "Plates",
                        "Start",
                        "Finish",
                        "Duration Minutes"
                    ]
                ],
                use_container_width=True
            )

            st.subheader("Summary by Sample Type")

            summary = (
                df.groupby("Sample Type")
                .agg(
                    Total_Samples_Processed=("Processed Samples", "sum"),
                    First_Start=("Start", "min"),
                    Final_Finish=("Finish", "max"),
                    Total_Cycles=("Sample Type", "count")
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
                text="Processed Samples"
            )

            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                height=650,
                xaxis_title="Time",
                yaxis_title="Processing Task"
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Enter your sample data, then click Generate Fast Schedule.")
