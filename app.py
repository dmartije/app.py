import math
import time
from datetime import datetime, timedelta
from itertools import permutations
from zoneinfo import ZoneInfo
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sample Workflow Optimizer", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background-color: #081C15;
        color: #E9F5EF;
    }
    section[data-testid="stSidebar"] {
        background-color: #0B2E26 !important;
        border-right: 1px solid #2D6A4F;
    }
    section[data-testid="stSidebar"] * { color: #E9F5EF !important; }
    .block-container {
        background: #0B2E26;
        border: 1px solid #2D6A4F;
        border-radius: 14px;
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption { color: #E9F5EF !important; }
    .kmi-header {
        background: #1f2c1f;
        border: 1px solid #6f8a65;
        border-radius: 12px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 1rem;
    }
    .kmi-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        color: #d9e5cd;
        letter-spacing: 0.5px;
    }
    .kmi-subtitle {
        font-size: 1.05rem;
        margin: 0.2rem 0 0 0;
        color: #d9e5cd;
    }
    .kmi-author {
        font-size: 0.95rem;
        margin-top: 0.35rem;
        color: #d9e5cd;
    }
    input, textarea, select {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * { color: #000000 !important; }
    .stButton>button {
        background-color: #2D6A4F;
        color: white;
        border-radius: 10px;
    }
    .stButton>button:hover { background-color: #40916C; }
    [data-testid="stDataFrame"] {
        background-color: #0B2E26 !important;
        border: 1px solid #2D6A4F !important;
        border-radius: 12px;
    }
    [data-testid="stDataFrame"] * { color: #E9F5EF !important; }
    .stAlert { background: #1B4332 !important; border: 1px solid #95D5B2 !important; color: #E9F5EF !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="kmi-header">
        <p class="kmi-title">KAFUGAN MINING INCORPORATED</p>
        <p class="kmi-subtitle">Assay Department</p>
        <p class="kmi-author">Created by: Engr. Dame Augustine Martije</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col_logo, col_head = st.columns([1, 6])
with col_logo:
    logo_path = Path(r"C:\Users\damar\OneDrive\Documents\Dame Files\Dame Files\KMI header footer\viber_image_2024-02-27_14-50-04-299.jpg")
    if logo_path.exists():
        st.image(str(logo_path), width=120)
    else:
        st.warning("Logo not found")
with col_head:
    st.title("Sample Workflow Optimizer")
    st.caption("Assay Department")
PH_TZ = ZoneInfo("Asia/Manila")
ph_now = pd.Timestamp(datetime.now(PH_TZ)).tz_localize(None)
st.caption(f"Current Philippine Time: {ph_now.strftime('%Y-%m-%d %I:%M:%S %p')}")
BATCH_STORE = Path("batches_store.json")


def load_batches():
    if BATCH_STORE.exists():
        try:
            data = json.loads(BATCH_STORE.read_text())
            for r in data:
                r["received_at"] = pd.Timestamp(r["received_at"])
            return data
        except Exception:
            return []
    return []


def save_batches(records):
    serializable = []
    for r in records:
        row = dict(r)
        row["received_at"] = str(pd.Timestamp(row["received_at"]))
        serializable.append(row)
    BATCH_STORE.write_text(json.dumps(serializable, indent=2))

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
        "lab_drying_minutes": 60,
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
        "lab_drying_minutes": 60,
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
        "lab_drying_minutes": 120,
    },
    "Lot Quality": {
        "priority": 4,
        "reduction_minutes": 30,
        "reduction_personnel": 1,
        "plate_capacity": 1,
        "sorting_minutes": 30,
        "drying_minutes": 360,
        "drying_per_shelf": 1,
        "crushing_per_sample": 10,
        "pulv_per_sample": 15,
        "lab_drying_minutes": 120,
    },
}


def per_sample_minutes(step, sample_type, material):
    material = (material or "").strip().lower()
    matrix = {
        "reduction": {
            "Face": 5,
            "Mine": {"limonite": 30, "saprolite": 45},
            "Sublot": {"limonite": 45, "saprolite": 60},
            "Lot Quality": 30,
        },
        "crushing": {
            "Face": 7,
            "Mine": {"limonite": 10, "saprolite": 15},
            "Sublot": {"limonite": 15, "saprolite": 15},
            "Lot Quality": 10,
        },
        "pulverizing": {
            "Face": 7,
            "Mine": {"limonite": 15, "saprolite": 15},
            "Sublot": {"limonite": 30, "saprolite": 30},
            "Lot Quality": 15,
        },
        "weighing": {"Face": 3, "Mine": 3, "Sublot": 3, "Lot Quality": 3},
    }
    cfg = matrix[step][sample_type]
    if isinstance(cfg, dict):
        return cfg.get(material, next(iter(cfg.values())))
    return cfg


st.sidebar.markdown("### Shared Capacity Inputs")
personnel_total = st.sidebar.number_input("Personnel Present", min_value=1, max_value=100, value=20)
window_start = st.sidebar.time_input("Higher-capacity window start", value=datetime(2026, 5, 4, 14, 0).time())
window_end = st.sidebar.time_input("Higher-capacity window end", value=datetime(2026, 5, 5, 6, 0).time())

st.sidebar.markdown("### Equipment Settings")
ovens_high = st.sidebar.selectbox("Ovens operating during higher-capacity window", [1, 2], index=1)
ovens_low = st.sidebar.selectbox("Ovens operating outside that window", [1, 2], index=0)
pulverizer_count = st.sidebar.selectbox("Pulverizers operating", [1, 2], index=1)
xrf_machine_count = st.sidebar.selectbox("XRF machines operating", [1, 2], index=1)
solver_time_limit = st.sidebar.slider("Solver Time Limit (seconds)", min_value=3, max_value=60, value=15)

# Persist batches across Streamlit reruns.
if "batches" not in st.session_state:
    st.session_state.batches = load_batches()

st.sidebar.markdown("### Append Batch")
with st.sidebar.form("add_batch_form", clear_on_submit=True):
    new_batch_id = st.text_input("Batch Number / Sample ID", value="")
    new_type = st.selectbox("Sample Type", list(rules.keys()))
    new_material = st.selectbox("Material", ["Limonite", "Saprolite"], index=0)
    new_qty = st.number_input("Number of Samples", min_value=1, max_value=10000, value=1)
    new_received = st.datetime_input("Date and Time Received", value=datetime(2026, 5, 4, 8, 0))
    add_clicked = st.form_submit_button("Add Batch")

if add_clicked and new_batch_id.strip():
    st.session_state.batches.append(
        {
            "batch_id": new_batch_id.strip(),
            "sample_type": new_type,
            "qty": int(new_qty),
            "material": (new_material if new_type in ["Mine", "Sublot"] else "N/A"),
            "received_at": pd.Timestamp(new_received),
        }
    )
    try:
        save_batches(st.session_state.batches)
        st.success(f"Batch {new_batch_id.strip()} added.")
    except Exception as e:
        st.error(f"Batch added in session but failed to save to disk: {e}")

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
        save_batches(st.session_state.batches)
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
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

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
        material = b.get("material", "N/A")
        recv = pd.Timestamp(b["received_at"])

        sorting_start = recv
        sorting_end = recv + timedelta(minutes=r["sorting_minutes"])

        # Optional pre-drying for Lot Quality before reduction.
        red_start = sorting_end
        if b["sample_type"] == "Lot Quality":
            pre_start = sorting_end
            pre_duration = timedelta(minutes=240)
            pre_slots = []
            while not pre_slots:
                ovens = ovens_available(pre_start)
                candidates = [f"Oven {i}" for i in range(1, ovens + 1)]
                active_slots = []
                for dj in oven_jobs:
                    if not (pre_start + pre_duration <= dj["start"] or pre_start >= dj["finish"]):
                        active_slots.extend(dj["slots"])
                free_slots = []
                for o in candidates:
                    for shelf in range(1, SHELVES_PER_OVEN + 1):
                        slot = f"{o}-Shelf {shelf}"
                        if slot not in active_slots:
                            free_slots.append(slot)
                pre_slots = free_slots[:1]
                if not pre_slots:
                    pre_start += timedelta(minutes=TIME_UNIT)
            pre_finish = pre_start + pre_duration
            oven_jobs.append({"start": pre_start, "finish": pre_finish, "slots": pre_slots})
            drying_rows.append(
                {"Batch": bid, "Type": b["sample_type"], "Qty": qty, "Step": "Pre-Drying", "Start": pre_start, "Finish": pre_finish, "Slots": pre_slots}
            )
            red_start = pre_finish

        # Find first time where enough plates are free for reduction.
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

        reduction_per_sample = per_sample_minutes("reduction", b["sample_type"], material)
        used_plates = free_plates[:plates_need]
        effective_parallel_samples = max(1, len(used_plates) * r["plate_capacity"])
        reduction_cycles = math.ceil(qty / effective_parallel_samples)
        reduction_minutes = reduction_cycles * reduction_per_sample
        red_finish = red_start + timedelta(minutes=reduction_minutes)
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
                "Material": material,
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
                "Step": "Drying",
                "Slots": assigned_slots,
            }
        )

        # Crushing starts when drying is done and some personnel is available.
        crush_start = dry_finish
        while personnel_total - active_crushing_personnel(crush_start) <= 0:
            crush_start += timedelta(minutes=TIME_UNIT)

        crush_personnel = max(1, personnel_total - active_crushing_personnel(crush_start))
        crush_cycles = math.ceil(qty / crush_personnel)
        crush_per_sample = per_sample_minutes("crushing", b["sample_type"], material)
        crush_minutes = crush_cycles * crush_per_sample
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
            pulv_per_sample = per_sample_minutes("pulverizing", b["sample_type"], material)
            p_minutes = math.ceil(q_m * pulv_per_sample)
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
            pre = d[d["Step"] == "Pre-Drying"]
            if not pre.empty:
                overall_rows.append(
                    {"Batch": bid, "Type": rt["Type"], "Step": "Pre-Drying", "Start": pre["Start"].min(), "Finish": pre["Finish"].max()}
                )
            d_final = d[d["Step"] == "Drying"]
            if not d_final.empty:
                overall_rows.append(
                    {
                        "Batch": bid,
                        "Type": rt["Type"],
                        "Step": "Drying",
                        "Start": d_final["Start"].min(),
                        "Finish": d_final["Finish"].max(),
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
            pulv_finish = p["Finish"].max()
            overall_rows.append(
                {
                    "Batch": bid,
                    "Type": rt["Type"],
                    "Step": "Pulverizing & Sieving",
                    "Start": p["Start"].min(),
                    "Finish": pulv_finish,
                }
            )

            lab_sort_start = pulv_finish
            lab_sort_finish = lab_sort_start + timedelta(minutes=10)
            lab_dry_finish = lab_sort_finish + timedelta(minutes=rules[rt["Type"]]["lab_drying_minutes"])
            cool_finish = lab_dry_finish + timedelta(minutes=45)

            overall_rows.extend(
                [
                    {
                        "Batch": bid,
                        "Type": rt["Type"],
                        "Step": "Laboratory Sorting",
                        "Start": lab_sort_start,
                        "Finish": lab_sort_finish,
                    },
                    {
                        "Batch": bid,
                        "Type": rt["Type"],
                        "Step": "Laboratory Drying",
                        "Start": lab_sort_finish,
                        "Finish": lab_dry_finish,
                    },
                    {
                        "Batch": bid,
                        "Type": rt["Type"],
                        "Step": "Cooling in Desiccator",
                        "Start": lab_dry_finish,
                        "Finish": cool_finish,
                    },
                ]
            )

    overall_df = pd.DataFrame(overall_rows)

    # --- Weighing (2 balances, priority-aware), Pelletizing, XRF allocation ---
    cool_steps = overall_df[overall_df["Step"] == "Cooling in Desiccator"].copy()
    batch_lookup = {b["batch_id"]: b for b in batches}
    weighing_tasks = []
    for _, row in cool_steps.iterrows():
        qty = int(batch_lookup[row["Batch"]]["qty"])
        for sample_idx in range(1, qty + 1):
            weighing_tasks.append(
                {
                    "Batch": row["Batch"],
                    "Type": row["Type"],
                    "Sample": sample_idx,
                    "ready": row["Finish"],
                }
            )

    balances = {f"Balance {i}": pd.Timestamp.min for i in range(1, 3)}
    weighing_rows = []

    def task_priority(t):
        return (0 if t["Type"] == "Sublot" else 1, t["ready"], t["Batch"], t["Sample"])

    pending = weighing_tasks[:]
    while pending:
        machine = min(balances, key=lambda m: balances[m])
        current_t = balances[machine]
        ready = [t for t in pending if t["ready"] <= current_t]
        if not ready:
            next_ready = min(t["ready"] for t in pending)
            current_t = max(current_t, next_ready)
            ready = [t for t in pending if t["ready"] <= current_t]
        chosen = sorted(ready, key=task_priority)[0]
        start_t = current_t
        weigh_minutes = per_sample_minutes("weighing", chosen["Type"], batch_lookup[chosen["Batch"]].get("material", "N/A"))
        finish_t = start_t + timedelta(minutes=weigh_minutes)
        balances[machine] = finish_t
        pending.remove(chosen)
        weighing_rows.append(
            {
                "Batch": chosen["Batch"],
                "Type": chosen["Type"],
                "Sample": chosen["Sample"],
                "Balance": machine,
                "Start": start_t,
                "Finish": finish_t,
            }
        )

    weighing_df = pd.DataFrame(weighing_rows).sort_values("Finish")

    pellet_rows = []
    pellet_free = pd.Timestamp.min
    for _, w in weighing_df.iterrows():
        p_start = max(pellet_free, w["Finish"])
        p_finish = p_start + timedelta(minutes=3)
        pellet_free = p_finish
        pellet_rows.append(
            {
                "Batch": w["Batch"],
                "Type": w["Type"],
                "Sample": w["Sample"],
                "Start": p_start,
                "Finish": p_finish,
                "Machine": "Pelletizer 1",
            }
        )
    pellet_df = pd.DataFrame(pellet_rows)

    xrf_rows = []
    xrf_free = {f"XRF {i}": pd.Timestamp.min for i in range(1, int(xrf_machine_count) + 1)}
    for batch_id, grp in pellet_df.groupby("Batch"):
        grp = grp.sort_values("Finish")
        sample_finishes = list(grp["Finish"])
        batch_type = grp["Type"].iloc[0]
        for chunk_idx in range(0, len(sample_finishes), 10):
            chunk_samples = min(10, len(sample_finishes) - chunk_idx)
            ready_t = sample_finishes[chunk_idx + chunk_samples - 1]
            machine = min(xrf_free, key=lambda m: max(xrf_free[m], ready_t))
            x_start = max(xrf_free[machine], ready_t)
            x_finish = x_start + timedelta(minutes=30)
            xrf_free[machine] = x_finish
            xrf_rows.append(
                {
                    "Batch": batch_id,
                    "Type": batch_type,
                    "Chunk": f"{chunk_idx + 1}-{chunk_idx + chunk_samples}",
                    "Samples": chunk_samples,
                    "Machine": machine,
                    "Start": x_start,
                    "Finish": x_finish,
                }
            )
    xrf_df = pd.DataFrame(xrf_rows)

    for bid in overall_df["Batch"].unique():
        w = weighing_df[weighing_df["Batch"] == bid]
        pel = pellet_df[pellet_df["Batch"] == bid]
        x = xrf_df[xrf_df["Batch"] == bid]
        batch_type = overall_df[overall_df["Batch"] == bid]["Type"].iloc[0]
        if not w.empty:
            overall_df.loc[len(overall_df)] = [bid, batch_type, "Weighing", w["Start"].min(), w["Finish"].max()]
        if not pel.empty:
            overall_df.loc[len(overall_df)] = [bid, batch_type, "Pelletizing", pel["Start"].min(), pel["Finish"].max()]
        if not x.empty:
            overall_df.loc[len(overall_df)] = [bid, batch_type, "XRF Analysis", x["Start"].min(), x["Finish"].max()]

    return red_df, dry_df, crush_df, pulv_df, overall_df, weighing_df, pellet_df, xrf_df


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
        _, _, _, _, overall_df, _, _, _ = schedule_batches(list(perm))
        finish = overall_df["Finish"].max() if not overall_df.empty else pd.Timestamp.min
        if best_finish is None or finish < best_finish:
            best_finish = finish
            best_order = list(perm)

        if time.time() - start_t >= time_limit_seconds:
            return best_order, "FEASIBLE", f"Searched {tested}/{total} orders within {time_limit_seconds}s."

    return best_order, "OPTIMAL", f"Exhaustive search complete ({tested}/{total} orders)."


def batch_status_at_time(overall_df, ts):
    status_map = {
        "Pulverizing & Sieving": "Pulverizing and Sieving",
    }
    result = {}
    for bid, grp in overall_df.groupby("Batch"):
        grp = grp.sort_values("Start")
        if ts < grp["Start"].min():
            result[bid] = "Waiting to Start"
            continue
        active = grp[(grp["Start"] <= ts) & (ts < grp["Finish"])]
        if not active.empty:
            step = active.iloc[0]["Step"]
            result[bid] = status_map.get(step, step)
            continue
        if ts >= grp["Finish"].max():
            result[bid] = "Completed"
        else:
            nxt = grp[grp["Start"] > ts].iloc[0]["Step"]
            result[bid] = f"Waiting ({status_map.get(nxt, nxt)})"
    return result


refresh_clicked = st.button("Refresh Schedule")
if refresh_clicked or st.session_state.batches:
    best_order, solver_status, solver_message = optimize_batch_order(st.session_state.batches, solver_time_limit)
    red_df, dry_df, crush_df, pulv_df, overall_df, weighing_df, pellet_df, xrf_df = schedule_batches(best_order)

    if overall_df.empty:
        st.warning("No batches to schedule.")
    else:
        st.info(f"Solver Status: {solver_status}")
        st.caption(solver_message)

        st.subheader("Batch Completion Summary")
        sample_prep_steps = ["Sorting", "Pre-Drying", "Reduction", "Drying", "Crushing", "Pulverizing & Sieving"]
        lab_steps = [
            "Laboratory Sorting",
            "Laboratory Drying",
            "Cooling in Desiccator",
            "Weighing",
            "Pelletizing",
            "XRF Analysis",
        ]

        prep_df = overall_df[overall_df["Step"].isin(sample_prep_steps)].copy()
        lab_df = overall_df[overall_df["Step"].isin(lab_steps)].copy()

        prep_summary = (
            prep_df.groupby(["Batch", "Type"])
            .agg(PrepStart=("Start", "min"), PrepFinish=("Finish", "max"))
            .reset_index()
        )
        lab_summary = (
            lab_df.groupby(["Batch", "Type"])
            .agg(LabStart=("Start", "min"), LabFinish=("Finish", "max"))
            .reset_index()
        )
        lab_active_hours = (
            lab_df.assign(
                StepHours=(lab_df["Finish"] - lab_df["Start"]).dt.total_seconds() / 3600
            )
            .groupby(["Batch", "Type"])["StepHours"]
            .sum()
            .reset_index(name="Estimated Laboratory Hours")
        )

        finals = prep_summary.merge(lab_summary, on=["Batch", "Type"], how="left")
        finals["Estimated Sample Prep Hours"] = (
            ((finals["PrepFinish"] - finals["PrepStart"]).dt.total_seconds() / 3600).round(2)
        )
        finals = finals.merge(lab_active_hours, on=["Batch", "Type"], how="left")
        finals["Estimated Laboratory Hours"] = finals["Estimated Laboratory Hours"].fillna(0).round(2)
        finals["Total Processing Hours"] = (
            finals["Estimated Sample Prep Hours"] + finals["Estimated Laboratory Hours"]
        ).round(2)
        statuses = batch_status_at_time(overall_df, ph_now)
        finals["Status"] = finals["Batch"].map(statuses).fillna("Waiting to Start")
        st.dataframe(finals, use_container_width=True)

        st.subheader("Process Time Specifications")
        spec_rows = [
            {
                "Process Step": "Sorting",
                "Face": rules["Face"]["sorting_minutes"],
                "Mine": rules["Mine"]["sorting_minutes"],
                "Sublot": rules["Sublot"]["sorting_minutes"],
                "Lot Quality": rules["Lot Quality"]["sorting_minutes"],
                "Processing Basis": "Per Batch",
                "Resource Used": "Personnel",
                "Notes": "Fixed per batch by sample type.",
            },
            {
                "Process Step": "Reduction",
                "Face": per_sample_minutes("reduction", "Face", "N/A"),
                "Mine": "Limonite 30 / Saprolite 45",
                "Sublot": "Limonite 45 / Saprolite 60",
                "Lot Quality": rules["Lot Quality"]["reduction_minutes"],
                "Processing Basis": "Per Batch",
                "Resource Used": "Personnel / Plate",
                "Notes": f"Personnel headcount constrained by user input ({personnel_total}).",
            },
            {
                "Process Step": "Drying",
                "Face": rules["Face"]["drying_minutes"],
                "Mine": rules["Mine"]["drying_minutes"],
                "Sublot": rules["Sublot"]["drying_minutes"],
                "Lot Quality": rules["Lot Quality"]["drying_minutes"],
                "Processing Basis": "Per Cycle",
                "Resource Used": "Oven",
                "Notes": f"Cycle time fixed; capacity varies by oven window ({ovens_high}/{ovens_low} ovens).",
            },
            {
                "Process Step": "Crushing",
                "Face": per_sample_minutes("crushing", "Face", "N/A"),
                "Mine": "Limonite 10 / Saprolite 15",
                "Sublot": "Limonite 15 / Saprolite 15",
                "Lot Quality": rules["Lot Quality"]["crushing_per_sample"],
                "Processing Basis": "Per Sample",
                "Resource Used": "Personnel",
                "Notes": f"Parallelized by available personnel ({personnel_total} max).",
            },
            {
                "Process Step": "Pulverizing & Sieving",
                "Face": per_sample_minutes("pulverizing", "Face", "N/A"),
                "Mine": "Limonite 15 / Saprolite 15",
                "Sublot": "Limonite 30 / Saprolite 30",
                "Lot Quality": rules["Lot Quality"]["pulv_per_sample"],
                "Processing Basis": "Per Sample",
                "Resource Used": "Pulverizer",
                "Notes": f"Distributed in parallel across {pulverizer_count} pulverizer(s).",
            },
            {
                "Process Step": "Laboratory Sorting",
                "Face": 10,
                "Mine": 10,
                "Sublot": 10,
                "Lot Quality": 10,
                "Processing Basis": "Per Batch",
                "Resource Used": "Personnel",
                "Notes": "Fixed per batch.",
            },
            {
                "Process Step": "Laboratory Drying",
                "Face": rules["Face"]["lab_drying_minutes"],
                "Mine": rules["Mine"]["lab_drying_minutes"],
                "Sublot": rules["Sublot"]["lab_drying_minutes"],
                "Lot Quality": rules["Lot Quality"]["lab_drying_minutes"],
                "Processing Basis": "Per Batch",
                "Resource Used": "Oven",
                "Notes": "Fixed by sample type.",
            },
            {
                "Process Step": "Cooling in Desiccator",
                "Face": 45,
                "Mine": 45,
                "Sublot": 45,
                "Lot Quality": 45,
                "Processing Basis": "Per Batch",
                "Resource Used": "Desiccator",
                "Notes": "Fixed per batch.",
            },
            {
                "Process Step": "Weighing",
                "Face": 3,
                "Mine": 3,
                "Sublot": 3,
                "Lot Quality": 3,
                "Processing Basis": "Per Sample",
                "Resource Used": "Balance",
                "Notes": "Two balances in parallel; Sublot prioritized when ready.",
            },
            {
                "Process Step": "Pelletizing",
                "Face": 3,
                "Mine": 3,
                "Sublot": 3,
                "Lot Quality": 3,
                "Processing Basis": "Per Sample",
                "Resource Used": "Pelletizer",
                "Notes": "Single pelletizer, serialized.",
            },
            {
                "Process Step": "XRF Analysis",
                "Face": 30,
                "Mine": 30,
                "Sublot": 30,
                "Lot Quality": 30,
                "Processing Basis": "Per 10 Samples",
                "Resource Used": "XRF Machine",
                "Notes": f"30 min per 10-sample run; parallel across {xrf_machine_count} XRF machine(s).",
            },
        ]
        st.dataframe(pd.DataFrame(spec_rows), use_container_width=True)

        st.subheader("Summary per Processing Step (per Batch)")
        step_order = [
            "Sorting",
            "Pre-Drying",
            "Reduction",
            "Drying",
            "Crushing",
            "Pulverizing & Sieving",
            "Laboratory Sorting",
            "Laboratory Drying",
            "Cooling in Desiccator",
            "Weighing",
            "Pelletizing",
            "XRF Analysis",
        ]
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
        active_overall_df = overall_df[overall_df["Finish"] > ph_now].copy()
        if active_overall_df.empty:
            st.info("No active sample batch to display.")
        else:
            active_overall_df["Label"] = active_overall_df["Batch"] + " - " + active_overall_df["Type"]
            fig_overall = px.timeline(active_overall_df, x_start="Start", x_end="Finish", y="Label", color="Step", text="Step")
            fig_overall.update_yaxes(autorange="reversed")
            fig_overall.update_yaxes(title_text="Batch No.")
            st.plotly_chart(fig_overall, use_container_width=True)

        st.subheader("Plate Allocation")
        active_red_df = red_df[red_df["Reduction Finish"] > ph_now].copy()
        if active_red_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_plate = px.timeline(
                active_red_df, x_start="Reduction Start", x_end="Reduction Finish", y="Plate", color="Type", text="Batch"
            )
            fig_plate.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_plate, use_container_width=True)

        st.subheader("Drying Oven Allocation")
        dry_plot = []
        active_dry_df = dry_df[dry_df["Finish"] > ph_now].copy()
        for _, r in active_dry_df.iterrows():
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
        if dry_plot_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_dry = px.timeline(dry_plot_df, x_start="Start", x_end="Finish", y="Slot", color="Type", text="Batch")
            fig_dry.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_dry, use_container_width=True)

        st.subheader("Crushing Personnel Allocation")
        crush_df["Lane"] = crush_df.apply(lambda x: f"{x['Batch']} ({x['Personnel']}P)", axis=1)
        active_crush_df = crush_df[crush_df["Finish"] > ph_now].copy()
        if active_crush_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_cr = px.timeline(active_crush_df, x_start="Start", x_end="Finish", y="Lane", color="Type", text="Qty")
            fig_cr.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_cr, use_container_width=True)

        st.subheader("Pulverizer Allocation")
        active_pulv_df = pulv_df[pulv_df["Finish"] > ph_now].copy()
        if active_pulv_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_p = px.timeline(active_pulv_df, x_start="Start", x_end="Finish", y="Machine", color="Type", text="Batch")
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)

        st.subheader("Weighing Chart")
        active_weighing_df = weighing_df[weighing_df["Finish"] > ph_now].copy()
        if active_weighing_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_w = px.timeline(active_weighing_df, x_start="Start", x_end="Finish", y="Balance", color="Type", text="Batch")
            fig_w.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_w, use_container_width=True)

        st.subheader("Pelletizing Chart")
        active_pellet_df = pellet_df[pellet_df["Finish"] > ph_now].copy()
        if active_pellet_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_pel = px.timeline(active_pellet_df, x_start="Start", x_end="Finish", y="Machine", color="Type", text="Batch")
            fig_pel.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_pel, use_container_width=True)

        st.subheader("XRF Allocation Chart")
        active_xrf_df = xrf_df[xrf_df["Finish"] > ph_now].copy()
        if active_xrf_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_xrf = px.timeline(active_xrf_df, x_start="Start", x_end="Finish", y="Machine", color="Type", text="Batch")
            fig_xrf.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_xrf, use_container_width=True)

        st.success(f"Overall estimated completion time: {overall_df['Finish'].max()}")
