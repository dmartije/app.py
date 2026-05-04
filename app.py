import math
import time
from datetime import datetime, timedelta
from itertools import permutations

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sample Scheduler", layout="wide")
st.title("Sample Preparation Optimizer")

# Global scheduling constraints.
TIME_UNIT = 5
TOTAL_PLATES = 5
SHELVES_PER_OVEN = 8

# Processing rules per sample type (capacity, durations, and labor assumptions).
rules = {
    "Face": {
        "priority": 2,
        "reduction_minutes": 5,
        "reduction_personnel": 1,
        "plate_capacity": 10,
        "sorting_minutes": 60,
        "drying_minutes": 480,
        "drying_per_shelf": 26,
        "crushing_per_sample": 3,
        "pulv_per_sample": 6,
    },
    "Mine": {
        "priority": 3,
        "reduction_minutes": 10,
        "reduction_personnel": 3,
        "plate_capacity": 2,
        "sorting_minutes": 30,
        "drying_minutes": 480,
        "drying_per_shelf": 8,
        "crushing_per_sample": 3,
        "pulv_per_sample": 8,
    },
    "Sublot": {
        "priority": 1,
        "reduction_minutes": 30,
        "reduction_personnel": 4,
        "plate_capacity": 1,
        "sorting_minutes": 35,
        "drying_minutes": 480,
        "drying_per_shelf": 4,
        "crushing_per_sample": 7,
        "pulv_per_sample": 10,
    },
    "Lot Quality": {
        "priority": 4,
        "reduction_minutes": 30,
        "reduction_personnel": 1,
        "plate_capacity": 1,
        "sorting_minutes": 30,
        "drying_minutes": 480,
        "drying_per_shelf": 1,
        "crushing_per_sample": 10,
        "pulv_per_sample": 15,
    },
}

st.sidebar.header("Shared Capacity Inputs")
personnel_total = st.sidebar.number_input("Personnel Present", min_value=1, max_value=100, value=20)
window_start = st.sidebar.time_input("Higher-capacity window start", value=datetime(2026, 5, 4, 14, 0).time())
window_end = st.sidebar.time_input("Higher-capacity window end", value=datetime(2026, 5, 5, 6, 0).time())
ovens_high = st.sidebar.selectbox("Ovens operating during higher-capacity window", [1, 2], index=1)
ovens_low = st.sidebar.selectbox("Ovens operating outside that window", [1, 2], index=0)
pulverizer_count = st.sidebar.selectbox("Pulverizers operating", [1, 2], index=1)
solver_time_limit = st.sidebar.slider("Solver Time Limit (seconds)", min_value=3, max_value=60, value=15)

# Persist batches across Streamlit reruns.
if "batches" not in st.session_state:
    st.session_state.batches = []

st.sidebar.subheader("Append Batch")
with st.sidebar.form("add_batch_form", clear_on_submit=True):
    new_batch_id = st.text_input("Batch Number / Sample ID", value="")
    new_type = st.selectbox("Sample Type", list(rules.keys()))
    new_qty = st.number_input("Number of Samples", min_value=1, max_value=10000, value=1)
    new_received = st.datetime_input("Date and Time Received", value=datetime(2026, 5, 4, 8, 0))
    add_clicked = st.form_submit_button("Add Batch")

if add_clicked and new_batch_id.strip():
    st.session_state.batches.append(
        {
            "batch_id": new_batch_id.strip(),
            "sample_type": new_type,
            "qty": int(new_qty),
            "received_at": pd.Timestamp(new_received),
        }
    )
    st.rerun()

st.subheader("Batch List Table")
if st.session_state.batches:
    edit_df = pd.DataFrame(st.session_state.batches)
    edit_df["delete"] = False
    edited = st.data_editor(edit_df, use_container_width=True, num_rows="dynamic")
    if st.button("Apply Batch Edits / Deletes"):
        kept = edited[~edited["delete"]].drop(columns=["delete"]).copy()
        kept["qty"] = kept["qty"].astype(int)
        kept["received_at"] = pd.to_datetime(kept["received_at"])
        st.session_state.batches = kept.to_dict("records")
        st.rerun()
else:
    st.info("No batches yet. Add a batch from the sidebar.")


def within_window(ts):
    """Return True when timestamp falls inside the high-capacity oven window."""
    t = ts.time()
    if window_start <= window_end:
        return window_start <= t < window_end
    return t >= window_start or t < window_end


def ovens_available(ts):
    """Select active oven count based on the configured time window."""
    return ovens_high if within_window(ts) else ovens_low


def schedule_batches(batches):
    """
    Build a full schedule for all batches in sequence.

    Stages are scheduled in order:
    1) Sorting + reduction (plate and personnel constrained)
    2) Drying (oven shelf constrained, with time-window-dependent oven count)
    3) Crushing (personnel constrained)
    4) Pulverizing/sieving (machine constrained)
    """
    if not batches:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    reduction_rows, drying_rows, crushing_rows, pulv_rows = [], [], [], []

    plate_free = {f"Plate {i}": pd.Timestamp.min for i in range(1, TOTAL_PLATES + 1)}
    oven_jobs = []
    crushing_jobs = []
    pulv_free = {f"Pulverizer {i}": pd.Timestamp.min for i in range(1, int(pulverizer_count) + 1)}

    def active_crushing_personnel(ts):
        return sum(j["personnel"] for j in crushing_jobs if j["start"] <= ts < j["finish"])

    # Schedule each batch end-to-end before moving to the next.
    for b in batches:
        r = rules[b["sample_type"]]
        bid = b["batch_id"]
        qty = int(b["qty"])
        recv = pd.Timestamp(b["received_at"])

        sorting_start = recv
        sorting_end = recv + timedelta(minutes=r["sorting_minutes"])

        # Find first time where enough plates are free for reduction.
        red_start = sorting_end
        while True:
            plates_need = math.ceil(qty / r["plate_capacity"])
            plates_need = min(plates_need, TOTAL_PLATES)
            free_plates = [p for p, t in plate_free.items() if t <= red_start]
            personnel_need = min(
                personnel_total, max(1, math.ceil(qty / r["plate_capacity"]) * r["reduction_personnel"])
            )
            if len(free_plates) >= plates_need:
                break
            red_start += timedelta(minutes=TIME_UNIT)

        red_finish = red_start + timedelta(minutes=r["reduction_minutes"])
        used_plates = free_plates[:plates_need]
        for p in used_plates:
            plate_free[p] = red_finish

        reduction_rows.append(
            {
                "Batch": bid,
                "Type": b["sample_type"],
                "Qty": qty,
                "Sorting Start": sorting_start,
                "Sorting End": sorting_end,
                "Reduction Start": red_start,
                "Reduction Finish": red_finish,
                "Personnel": personnel_need,
                "Plate": ", ".join(used_plates),
            }
        )

        # Find shelf slots where entire drying duration can fit.
        dry_start = red_finish
        shelves_need = math.ceil(qty / r["drying_per_shelf"])
        duration = timedelta(minutes=r["drying_minutes"])
        assigned_slots = []

        while not assigned_slots:
            ovens = ovens_available(dry_start)
            candidates = [f"Oven {i}" for i in range(1, ovens + 1)]
            active_slots = []
            for dj in oven_jobs:
                if not (dry_start + duration <= dj["start"] or dry_start >= dj["finish"]):
                    active_slots.extend(dj["slots"])

            free_slots = []
            for o in candidates:
                for shelf in range(1, SHELVES_PER_OVEN + 1):
                    slot = f"{o}-Shelf {shelf}"
                    if slot not in active_slots:
                        free_slots.append(slot)

            assigned_slots = free_slots[:shelves_need]
            if len(assigned_slots) < shelves_need:
                assigned_slots = []
                dry_start += timedelta(minutes=TIME_UNIT)

        dry_finish = dry_start + duration
        oven_jobs.append({"start": dry_start, "finish": dry_finish, "slots": assigned_slots})
        drying_rows.append(
            {
                "Batch": bid,
                "Type": b["sample_type"],
                "Qty": qty,
                "Start": dry_start,
                "Finish": dry_finish,
                "Slots": assigned_slots,
            }
        )

        # Crushing starts when drying is done and some personnel is available.
        crush_start = dry_finish
        while personnel_total - active_crushing_personnel(crush_start) <= 0:
            crush_start += timedelta(minutes=TIME_UNIT)

        crush_personnel = max(1, personnel_total - active_crushing_personnel(crush_start))
        crush_minutes = math.ceil((qty * r["crushing_per_sample"]) / crush_personnel)
        crush_finish = crush_start + timedelta(minutes=crush_minutes)

        crushing_jobs.append({"start": crush_start, "finish": crush_finish, "personnel": crush_personnel})
        crushing_rows.append(
            {
                "Batch": bid,
                "Type": b["sample_type"],
                "Qty": qty,
                "Start": crush_start,
                "Finish": crush_finish,
                "Personnel": crush_personnel,
            }
        )

        # Split quantity across pulverizers, preferring the earliest-available machine.
        machines = sorted(list(pulv_free.keys()), key=lambda m: pulv_free[m])
        q_base = qty // len(machines)
        q_rem = qty % len(machines)

        for i, m in enumerate(machines):
            q_m = q_base + (1 if i < q_rem else 0)
            if q_m <= 0:
                continue
            p_start = max(crush_finish, pulv_free[m])
            p_minutes = math.ceil(q_m * r["pulv_per_sample"])
            p_finish = p_start + timedelta(minutes=p_minutes)
            pulv_free[m] = p_finish
            pulv_rows.append(
                {
                    "Batch": bid,
                    "Type": b["sample_type"],
                    "Qty": q_m,
                    "Machine": m,
                    "Start": p_start,
                    "Finish": p_finish,
                }
            )

    red_df = pd.DataFrame(reduction_rows)
    dry_df = pd.DataFrame(drying_rows)
    crush_df = pd.DataFrame(crushing_rows)
    pulv_df = pd.DataFrame(pulv_rows)

    # Build a consolidated step-level view (used by summary tables and Gantt charts).
    overall_rows = []
    for bid in red_df["Batch"].unique():
        rt = red_df[red_df["Batch"] == bid].iloc[0]
        overall_rows.extend(
            [
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Sorting",
                    "Start": rt["Sorting Start"],
                    "Finish": rt["Sorting End"],
                },
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Reduction",
                    "Start": rt["Reduction Start"],
                    "Finish": rt["Reduction Finish"],
                },
            ]
        )

        d = dry_df[dry_df["Batch"] == bid]
        c = crush_df[crush_df["Batch"] == bid]
        p = pulv_df[pulv_df["Batch"] == bid]

        if not d.empty:
            overall_rows.append(
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Drying",
                    "Start": d["Start"].min(),
                    "Finish": d["Finish"].max(),
                }
            )
        if not c.empty:
            overall_rows.append(
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Crushing",
                    "Start": c["Start"].min(),
                    "Finish": c["Finish"].max(),
                }
            )
        if not p.empty:
            overall_rows.append(
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Pulverizing & Sieving",
                    "Start": p["Start"].min(),
                    "Finish": p["Finish"].max(),
                }
            )

    overall_df = pd.DataFrame(overall_rows)
    return red_df, dry_df, crush_df, pulv_df, overall_df


def optimize_batch_order(batches, time_limit_seconds):
    """
    Try to minimize overall finish time by reordering batches.

    For up to 8 batches, evaluate permutations until time limit.
    For more than 8, fall back to a deterministic heuristic order.
    """
    if not batches:
        return batches, "FEASIBLE", "No batches."

    base = sorted(batches, key=lambda b: (b["received_at"], rules[b["sample_type"]]["priority"]))
    n = len(base)
    if n > 8:
        return base, "FEASIBLE", "Heuristic order used (too many batches for exhaustive search)."

    start_t = time.time()
    best_order = base
    best_finish = None
    tested = 0
    total = math.factorial(n)

    for perm in permutations(base):
        tested += 1
        _, _, _, _, overall_df = schedule_batches(list(perm))
        finish = overall_df["Finish"].max() if not overall_df.empty else pd.Timestamp.min
        if best_finish is None or finish < best_finish:
            best_finish = finish
            best_order = list(perm)

        if time.time() - start_t >= time_limit_seconds:
            return best_order, "FEASIBLE", f"Searched {tested}/{total} orders within {time_limit_seconds}s."

    return best_order, "OPTIMAL", f"Exhaustive search complete ({tested}/{total} orders)."


if st.button("Recalculate Full Schedule") or st.session_state.batches:
    best_order, solver_status, solver_message = optimize_batch_order(st.session_state.batches, solver_time_limit)
    red_df, dry_df, crush_df, pulv_df, overall_df = schedule_batches(best_order)

    if overall_df.empty:
        st.warning("No batches to schedule.")
    else:
        st.info(f"Solver Status: {solver_status}")
        st.caption(solver_message)

        st.subheader("Batch Completion Summary")
        finals["Estimated Sample Prep Hours"] = (
            ((finals["Finish"] - finals["Start"]).dt.total_seconds() / 3600).round(2)
        )
        finals["Total Duration Hours"] = (((finals["Finish"] - finals["Start"]).dt.total_seconds() / 3600).round(2))
        st.dataframe(finals, use_container_width=True)

        st.subheader("Summary per Processing Step (per Batch)")
        step_order = ["Sorting", "Reduction", "Drying", "Crushing", "Pulverizing & Sieving"]
        step_batch_summary = overall_df.copy()
        step_batch_summary["Step"] = pd.Categorical(step_batch_summary["Step"], categories=step_order, ordered=True)
        step_batch_summary = step_batch_summary.sort_values(["Batch", "Step"])
        step_batch_summary["Duration Minutes"] = (
            (step_batch_summary["Finish"] - step_batch_summary["Start"]).dt.total_seconds() / 60
        ).round().astype(int)
        step_batch_summary["Duration (Min/Hr)"] = (
            step_batch_summary["Duration Minutes"].astype(str)
            + " ("
            + (step_batch_summary["Duration Minutes"] / 60).round(2).astype(str)
            + " hr)"
        )
        step_batch_summary["Batch Label"] = step_batch_summary["Batch"] + " - " + step_batch_summary["Type"]
        st.dataframe(
            step_batch_summary[["Batch Label", "Step", "Start", "Finish", "Duration (Min/Hr)"]],
            use_container_width=True,
        )

        st.subheader("Overall Sample Prep and Laboratory Process Chart")
        overall_df["Label"] = overall_df["Batch"] + " - " + overall_df["Type"]
        fig_overall = px.timeline(overall_df, x_start="Start", x_end="Finish", y="Label", color="Step", text="Step")
        fig_overall.update_yaxes(autorange="reversed")
        fig_overall.update_yaxes(title_text="Batch No.")
        st.plotly_chart(fig_overall, use_container_width=True)

        st.subheader("Plate Allocation")
        fig_plate = px.timeline(
            red_df, x_start="Reduction Start", x_end="Reduction Finish", y="Plate", color="Type", text="Batch"
        )
        fig_plate.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_plate, use_container_width=True)

        st.subheader("Drying Oven Allocation")
        dry_plot = []
        for _, r in dry_df.iterrows():
            for slot in r["Slots"]:
                dry_plot.append(
                    {
                        "Slot": slot,
                        "Batch": r["Batch"],
                        "Type": r["Type"],
                        "Start": r["Start"],
                        "Finish": r["Finish"],
                    }
                )
        dry_plot_df = pd.DataFrame(dry_plot)
        fig_dry = px.timeline(dry_plot_df, x_start="Start", x_end="Finish", y="Slot", color="Type", text="Batch")
        fig_dry.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_dry, use_container_width=True)

        st.subheader("Crushing Personnel Allocation")
        crush_df["Lane"] = crush_df.apply(lambda x: f"{x['Batch']} ({x['Personnel']}P)", axis=1)
        fig_cr = px.timeline(crush_df, x_start="Start", x_end="Finish", y="Lane", color="Type", text="Qty")
        fig_cr.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_cr, use_container_width=True)

        st.subheader("Pulverizer Allocation")
        fig_p = px.timeline(pulv_df, x_start="Start", x_end="Finish", y="Machine", color="Type", text="Batch")
        fig_p.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_p, use_container_width=True)

        st.success(f"Overall estimated completion time: {overall_df['Finish'].max()}")
