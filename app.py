import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from itertools import product
import math
import copy

# ============================================================
# SAMPLE PREPARATION DYNAMIC SCHEDULER
# ============================================================
# This app dynamically schedules sample preparation work.
#
# It considers:
# - fixed 5 working plates
# - available personnel
# - sample priority
# - different processing times
# - different personnel requirements
# - different plate capacities
# - dynamic reassignment after each cycle finishes
#
# Important:
# This is an industrial-style dynamic optimizer using beam search.
# It is much better than fixed allocation because resources are reused
# after every 5/10/15-minute cycle.
# ============================================================

st.set_page_config(page_title="Dynamic Sample Scheduler", layout="wide")
st.title("Dynamic Sample Preparation Scheduler")

TOTAL_PLATES = 5
PLATE_IDS = [f"Plate {i}" for i in range(1, TOTAL_PLATES + 1)]

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

# ============================================================
# USER INPUT
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

beam_width = st.sidebar.slider(
    "Optimization Search Strength",
    min_value=50,
    max_value=1000,
    value=300,
    step=50
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def useful_options(sample_type, remaining_qty, available_personnel, available_plates):
    """
    Generates useful personnel/plate combinations for one sample type.
    It avoids useless combinations, such as assigning 2 plates to 1 Lot Quality sample.
    """

    if remaining_qty <= 0:
        return [(0, 0)]

    rule = rules[sample_type]
    options = [(0, 0)]

    for plates in range(1, available_plates + 1):
        max_samples_by_plate = plates * rule["plate_capacity"]
        max_samples_this_cycle = min(remaining_qty, max_samples_by_plate)

        for samples_this_cycle in range(1, max_samples_this_cycle + 1):
            personnel_needed = samples_this_cycle * rule["personnel_per_sample"]

            if personnel_needed <= available_personnel:
                options.append((personnel_needed, plates))

    return options


def cycle_capacity(sample_type, personnel, plates):
    """
    Calculates how many samples can be processed in one cycle.
    """

    rule = rules[sample_type]

    personnel_capacity = personnel // rule["personnel_per_sample"]
    plate_capacity = plates * rule["plate_capacity"]

    return min(personnel_capacity, plate_capacity)


def resources_used(running_jobs):
    """
    Calculates currently occupied personnel and plates.
    """

    used_personnel = sum(job["Personnel"] for job in running_jobs)
    used_plates = []

    for job in running_jobs:
        used_plates.extend(job["Plates"])

    return used_personnel, used_plates


def next_finish_time(running_jobs):
    """
    Finds the nearest finishing job time.
    """

    if not running_jobs:
        return None

    return min(job["Finish"] for job in running_jobs)


def complete_finished_jobs(state):
    """
    Completes all jobs finishing at the current time.
    """

    current_time = state["time"]

    still_running = []

    for job in state["running"]:
        if job["Finish"] <= current_time:
            state["remaining"][job["Sample Type"]] -= job["Processed Samples"]
            state["schedule"].append(job)
        else:
            still_running.append(job)

    state["running"] = still_running

    return state


def all_done(state):
    """
    Checks if all samples are completed and no jobs are running.
    """

    return all(qty <= 0 for qty in state["remaining"].values()) and not state["running"]


def optimistic_lower_bound_minutes(remaining, total_personnel):
    """
    Estimates the best possible remaining time.
    This helps the optimizer keep better schedules during beam search.
    """

    max_required_minutes = 0

    for sample_type, qty in remaining.items():
        if qty <= 0:
            continue

        rule = rules[sample_type]

        max_personnel_capacity = total_personnel // rule["personnel_per_sample"]
        max_plate_capacity = TOTAL_PLATES * rule["plate_capacity"]

        max_capacity = min(max_personnel_capacity, max_plate_capacity)

        if max_capacity <= 0:
            return 999999

        cycles = math.ceil(qty / max_capacity)
        required_minutes = cycles * rule["minutes_per_cycle"]

        max_required_minutes = max(max_required_minutes, required_minutes)

    return max_required_minutes


def state_score(state, total_personnel):
    """
    Scores a state.
    Lower score is better.
    """

    lower_bound = optimistic_lower_bound_minutes(state["remaining"], total_personnel)

    weighted_remaining = sum(
        qty * rules[sample_type]["priority"]
        for sample_type, qty in state["remaining"].items()
    )

    running_count = len(state["running"])

    return (
        state["time"] + timedelta(minutes=lower_bound),
        weighted_remaining,
        running_count
    )


def generate_allocations(state, total_personnel):
    """
    Generates possible new assignments using currently available personnel and plates.
    Allows staggered processing by allowing some sample types to wait.
    """

    used_personnel, used_plate_ids = resources_used(state["running"])

    available_personnel = total_personnel - used_personnel
    available_plate_ids = [p for p in PLATE_IDS if p not in used_plate_ids]
    available_plates = len(available_plate_ids)

    if available_personnel <= 0 or available_plates <= 0:
        return []

    running_types = {job["Sample Type"] for job in state["running"]}

    candidate_types = [
        sample_type
        for sample_type, qty in state["remaining"].items()
        if qty > 0 and sample_type not in running_types
    ]

    candidate_types = sorted(candidate_types, key=lambda x: rules[x]["priority"])

    if not candidate_types:
        return []

    option_lists = []

    for sample_type in candidate_types:
        option_lists.append(
            useful_options(
                sample_type,
                state["remaining"][sample_type],
                available_personnel,
                available_plates
            )
        )

    allocations = []

    for combination in product(*option_lists):
        total_p = sum(item[0] for item in combination)
        total_pl = sum(item[1] for item in combination)

        if total_p == 0 or total_pl == 0:
            continue

        if total_p > available_personnel or total_pl > available_plates:
            continue

        allocation = {}

        plate_index = 0

        for sample_type, (personnel, plates) in zip(candidate_types, combination):
            if personnel > 0 and plates > 0:
                assigned_plates = available_plate_ids[plate_index:plate_index + plates]
                plate_index += plates

                allocation[sample_type] = {
                    "Personnel": personnel,
                    "Plates": assigned_plates
                }

        allocations.append(allocation)

    return allocations


def start_jobs_from_allocation(state, allocation):
    """
    Starts one cycle for each assigned sample type.
    """

    new_state = copy.deepcopy(state)

    for sample_type, assign in allocation.items():
        personnel = assign["Personnel"]
        plates = assign["Plates"]

        capacity = cycle_capacity(sample_type, personnel, len(plates))

        if capacity <= 0:
            continue

        processed = min(new_state["remaining"][sample_type], capacity)

        finish_time = new_state["time"] + timedelta(
            minutes=rules[sample_type]["minutes_per_cycle"]
        )

        job = {
            "Sample Type": sample_type,
            "Processed Samples": processed,
            "Personnel": personnel,
            "Plates": plates,
            "Start": new_state["time"],
            "Finish": finish_time,
            "Duration Minutes": rules[sample_type]["minutes_per_cycle"],
            "Priority": rules[sample_type]["priority"]
        }

        new_state["running"].append(job)

    return new_state


# ============================================================
# MAIN OPTIMIZER
# ============================================================

def dynamic_optimize(samples, total_personnel, start_time, beam_width):
    """
    Dynamic beam-search scheduler.

    It repeatedly:
    1. checks remaining samples
    2. checks available personnel
    3. checks available plates
    4. considers priority
    5. starts the best next processing cycles
    6. advances time to the next completed cycle
    7. reuses personnel and plates
    """

    initial_state = {
        "time": start_time,
        "remaining": dict(samples),
        "running": [],
        "schedule": []
    }

    beam = [initial_state]
    completed_states = []

    max_iterations = 1000

    for _ in range(max_iterations):

        next_beam = []

        for state in beam:
            state = copy.deepcopy(state)
            state = complete_finished_jobs(state)

            if all_done(state):
                completed_states.append(state)
                continue

            allocations = generate_allocations(state, total_personnel)

            if allocations:
                for allocation in allocations:
                    new_state = start_jobs_from_allocation(state, allocation)
                    next_beam.append(new_state)
            else:
                nft = next_finish_time(state["running"])

                if nft is not None:
                    state["time"] = nft
                    next_beam.append(state)

        if completed_states:
            break

        if not next_beam:
            break

        next_beam = sorted(
            next_beam,
            key=lambda s: state_score(s, total_personnel)
        )

        beam = next_beam[:beam_width]

    if not completed_states:
        return None

    best_state = sorted(
        completed_states,
        key=lambda s: (
            max(job["Finish"] for job in s["schedule"]),
            sum(job["Priority"] * job["Duration Minutes"] for job in s["schedule"])
        )
    )[0]

    return best_state


# ============================================================
# RUN APP
# ============================================================

if st.button("Generate Dynamic Optimized Schedule"):

    active_samples = {k: v for k, v in samples.items() if v > 0}

    if not active_samples:
        st.warning("Please enter at least one sample.")
    else:
        result = dynamic_optimize(
            samples=active_samples,
            total_personnel=total_personnel,
            start_time=start_datetime,
            beam_width=beam_width
        )

        if result is None:
            st.error("No valid schedule found. Check personnel and sample quantity.")
        else:
            schedule_df = pd.DataFrame(result["schedule"])

            schedule_df["Plates"] = schedule_df["Plates"].apply(lambda x: ", ".join(x))

            schedule_df = schedule_df.sort_values(["Start", "Priority"])

            final_finish = schedule_df["Finish"].max()

            st.success(
                f"All samples completed by: {final_finish.strftime('%B %d, %Y %I:%M %p')}"
            )

            st.subheader("Detailed Dynamic Schedule")

            st.dataframe(
                schedule_df[
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

            summary_df = (
                schedule_df
                .groupby("Sample Type")
                .agg(
                    Total_Samples_Processed=("Processed Samples", "sum"),
                    First_Start=("Start", "min"),
                    Final_Finish=("Finish", "max"),
                    Total_Cycles=("Sample Type", "count")
                )
                .reset_index()
            )

            st.dataframe(summary_df, use_container_width=True)

            st.subheader("Gantt Chart")

            gantt_df = schedule_df.copy()
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

else:
    st.info("Input your sample quantities, personnel, and start time, then click Generate Dynamic Optimized Schedule.")
