import base64
import html
import itertools
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / ".devcontainer" / "viber_image_2024-02-27_14-50-04-299-removebg-preview (1).png"
SIDEBAR_LOGO_PATH = APP_DIR / ".devcontainer" / "KMI Logo.jpg"

st.set_page_config(page_title="Sample Workflow Optimizer", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stSidebarHeader"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stMain"] {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    .stApp {
        background-color: #081C15;
        color: #E9F5EF;
    }
    section[data-testid="stSidebar"] {
        background-color: #0B2E26 !important;
        border-right: 1px solid #2D6A4F;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    section[data-testid="stSidebar"] * { color: #E9F5EF !important; }
    .block-container {
        background: #0B2E26;
        border: 1px solid #2D6A4F;
        border-radius: 14px;
        padding-top: 0rem !important;
        margin-top: 0rem !important;
        padding-bottom: 2rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption { color: #E9F5EF !important; }
    .kmi-header {
        align-items: center;
        background: #1f2c1f;
        border: 1px solid #6f8a65;
        border-radius: 12px;
        display: flex;
        gap: 1rem;
        padding: 0.9rem 1.2rem;
        margin-top: 0rem;
        margin-bottom: 1rem;
    }
    .kmi-logo {
        border-radius: 10px;
        flex: 0 0 auto;
        height: 120px;
        object-fit: contain;
        width: 120px;
    }
    .kmi-header-text {
        min-width: 0;
    }
    .sidebar-kmi-logo {
        display: block;
        height: 63px;
        margin: 2rem auto 1rem auto;
        object-fit: contain;
        width: 183px;
    }
    .kmi-title {
        font-size: calc(1.75rem + 3px);
        font-weight: 700;
        margin: 0;
        color: #d9e5cd;
        letter-spacing: 0.5px;
    }
    .kmi-subtitle {
        font-size: calc(1.05rem + 2px);
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
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stDateTimeInput"] input {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background-color: #FFFFFF !important;
    }
    div[data-baseweb="select"] * { color: #000000 !important; }
    .stButton>button {
        background-color: #2D6A4F;
        color: white;
        border-radius: 10px;
    }
    .stButton>button:hover { background-color: #40916C; }
    .stFormSubmitButton>button {
        background-color: #2D6A4F !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
    }
    .stFormSubmitButton>button:hover {
        background-color: #1B4332 !important;
        color: #FFFFFF !important;
    }
    .lab-table-card-title {
        color: #F5F7F2;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: 0.02rem;
        margin-bottom: 0.65rem;
        padding-bottom: 0.45rem;
        border-bottom: 1px solid #6B8E5A;
    }
    .lab-table-caption {
        color: #D8E6D0;
        font-size: 0.88rem;
        margin-top: -0.35rem;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #6B8E5A !important;
        background: linear-gradient(145deg, #102E24 0%, #0B241D 100%) !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    }
    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"] {
        background-color: #F7F9F3 !important;
        border: 1px solid #A6B99A !important;
        border-radius: 14px !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
        overflow: hidden !important;
    }
    [data-testid="stDataFrame"] div[role="grid"],
    [data-testid="stDataEditor"] div[role="grid"] {
        color: #17251D !important;
        background-color: #F7F9F3 !important;
        font-size: 0.92rem !important;
    }
    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataEditor"] [role="columnheader"] {
        background-color: #1F3B2D !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-color: #6B8E5A !important;
    }
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataEditor"] [role="gridcell"] {
        color: #17251D !important;
        border-color: #D7E0D1 !important;
        min-height: 38px !important;
    }
    [data-testid="stDataEditor"] [role="rowgroup"] [role="row"]:nth-child(odd) [role="gridcell"],
    [data-testid="stDataEditor"] tbody tr:nth-child(odd) td[role="gridcell"] {
        background-color: #F7F9F3 !important;
    }
    [data-testid="stDataEditor"] [role="rowgroup"] [role="row"]:nth-child(even) [role="gridcell"],
    [data-testid="stDataEditor"] tbody tr:nth-child(even) td[role="gridcell"] {
        background-color: #EEF3E8 !important;
    }
    [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"],
    [data-testid="stDataEditor"] [role="row"]:hover [role="gridcell"] {
        background-color: #E5EEDC !important;
    }
    [data-testid="stDataEditor"] input[type="checkbox"] {
        accent-color: #2D6A4F;
        margin: auto;
    }

    .lab-html-table-card {
        background-color: #F7F9F3;
        border: 1px solid #A6B99A;
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
        overflow: hidden;
        width: 100%;
    }
    .lab-html-table-card table {
        border-collapse: collapse;
        table-layout: fixed;
        width: 100%;
    }
    .lab-html-table-card th {
        background-color: #1F3B2D;
        border-bottom: 2px solid #6B8E5A;
        color: #FFFFFF;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1.18;
        padding: 8px 6px;
        text-align: left;
        white-space: normal;
        word-break: normal;
        overflow-wrap: anywhere;
    }
    .lab-html-table-card td {
        border-bottom: 1px solid #D7E0D1;
        color: #17251D;
        font-size: 0.78rem;
        line-height: 1.25;
        padding: 8px 6px;
        vertical-align: top;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .lab-html-table-card tbody tr:nth-child(odd) td { background-color: #F7F9F3; }
    .lab-html-table-card tbody tr:nth-child(even) td { background-color: #EEF3E8; }
    .lab-html-table-card tbody tr:hover td { background-color: #E5EEDC; }
    .stAlert { background: #1B4332 !important; border: 1px solid #95D5B2 !important; color: #E9F5EF !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
logo_html = ""
if LOGO_PATH.exists():
    encoded_logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
    logo_html = (
        '<img class="kmi-logo" '
        'src="data:image/png;base64,' + encoded_logo + '" '
        'alt="Kafugan Mining Incorporated logo">'
    )

st.markdown(
    f"""
    <div class="kmi-header">
        {logo_html}
        <div class="kmi-header-text">
            <p class="kmi-title">KAFUGAN MINING INCORPORATED</p>
            <p class="kmi-subtitle">Assay Department</p>
            <p class="kmi-author">Created by: Engr. Dame Augustine Martije<br>Version 0: 05/08/2026</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("SAMPLE WORKFLOW OPTIMIZER")
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


def style_lab_table(df):
    """Apply reusable QA/QC laboratory dashboard styling to table data."""
    styled = df.style
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    center_cols = [col for col in df.columns if str(col).lower() in {"remove", "select"}]
    text_cols = [col for col in df.columns if col not in numeric_cols + datetime_cols + center_cols]

    def zebra_rows(row):
        row_position = df.index.get_loc(row.name)
        color = "#F7F9F3" if row_position % 2 == 0 else "#EEF3E8"
        return [f"background-color: {color}; color: #17251D;" for _ in row]

    def format_numeric(value):
        if pd.isna(value):
            return ""
        rounded = round(float(value), 2)
        if math.isclose(rounded, round(rounded)):
            return f"{rounded:,.0f}"
        return f"{rounded:,.2f}".rstrip("0").rstrip(".")

    formatters = {
        col: (lambda value: "" if pd.isna(value) else pd.Timestamp(value).strftime("%Y-%m-%d %I:%M %p"))
        for col in datetime_cols
    }
    formatters.update({col: format_numeric for col in numeric_cols})
    
    styled = styled.apply(zebra_rows, axis=1)
    styled = styled.format(formatters)
    if text_cols:
        styled = styled.set_properties(
            subset=text_cols,
            **{
                "text-align": "left",
                "font-size": "14px",
                "line-height": "1.45",
                "padding": "10px 12px",
                "color": "#17251D",
            },
        )
    if numeric_cols:
        styled = styled.set_properties(
            subset=numeric_cols,
            **{
                "text-align": "right",
                "font-size": "14px",
                "line-height": "1.45",
                "padding": "10px 12px",
                "color": "#17251D",
            },
        )
    if datetime_cols:
        styled = styled.set_properties(
            subset=datetime_cols,
            **{
                "text-align": "left",
                "font-size": "14px",
                "line-height": "1.45",
                "padding": "10px 12px",
                "white-space": "nowrap",
                "color": "#17251D",
            },
        )
    if center_cols:
        styled = styled.set_properties(
            subset=center_cols,
            **{
                "text-align": "center",
                "font-size": "14px",
                "line-height": "1.45",
                "padding": "10px 12px",
                "color": "#17251D",
            },
        )

    return styled.set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#1F3B2D"),
                    ("color", "#FFFFFF"),
                    ("font-weight", "700"),
                    ("font-size", "14px"),
                    ("text-transform", "none"),
                    ("border-bottom", "2px solid #6B8E5A"),
                    ("padding", "11px 12px"),
                ],
            },
            {
                "selector": "tbody tr:hover td",
                "props": [("background-color", "#E5EEDC"), ("color", "#17251D")],
            },
            {
                "selector": "tbody td",
                "props": [("border-bottom", "1px solid #D7E0D1")],
            },
        ]
    )


def lab_section_title(title):
    """Render section headings with the reusable laboratory title style."""
    st.markdown(f'<div class="lab-table-card-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def lab_table_card(title, dataframe, caption=None, height="content", column_config=None):
    """Render every dataframe in a consistent army-green laboratory card."""
    with st.container(border=True):
        lab_section_title(title)
        if caption:
            st.markdown(f'<div class="lab-table-caption">{html.escape(caption)}</div>', unsafe_allow_html=True)
        st.dataframe(
            style_lab_table(dataframe),
            use_container_width=True,
            height=height,
            column_config=column_config,
        )


def render_lab_html_table(dataframe):
    """Render fixed-width table markup with wrapped headers and consistent cell formatting."""
    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    datetime_cols = dataframe.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()

    def format_cell(column, value):
        if pd.isna(value):
            return ""
        if column in datetime_cols:
            return pd.Timestamp(value).strftime("%Y-%m-%d %I:%M %p")
        if column in numeric_cols:
            rounded = round(float(value), 2)
            if math.isclose(rounded, round(rounded)):
                return f"{rounded:,.0f}"
            return f"{rounded:,.2f}".rstrip("0").rstrip(".")
        return str(value)

    header_html = "".join(f"<th>{html.escape(str(col))}</th>" for col in dataframe.columns)
    row_html = []
    for _, row in dataframe.iterrows():
        cells = "".join(
            f"<td>{html.escape(format_cell(col, row[col]))}</td>" for col in dataframe.columns
        )
        row_html.append(f"<tr>{cells}</tr>")

    st.markdown(
        '<div class="lab-html-table-card"><table>'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )


def lab_html_table_card(title, dataframe, caption=None):
    """Render a fixed-width HTML table with wrapping headers to avoid horizontal scrolling."""
    with st.container(border=True):
        lab_section_title(title)
        if caption:
            st.markdown(f'<div class="lab-table-caption">{html.escape(caption)}</div>', unsafe_allow_html=True)
        render_lab_html_table(dataframe)


def lab_editor_card(title, dataframe, **editor_kwargs):
    """Render editable tables with the same laboratory card treatment."""
    with st.container(border=True):
        lab_section_title(title)
        return st.data_editor(style_lab_table(dataframe), use_container_width=True, **editor_kwargs)

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



# Modular QC expansion rules. User-entered quantities remain original received samples;
# these helpers derive the adjusted processing counts used from drying onward.
QC_RULES = {
    "Face": {
        "description": "1 QC sample for every 15 original samples from drying onward.",
        "qc_added": lambda original: math.ceil(original / 15),
        "analytical_additional": lambda original: 0,
    },
    "Mine": {
        "description": "1 QC sample per original mine sample from drying onward.",
        "qc_added": lambda original: original,
        "analytical_additional": lambda original: 0,
    },
    "Sublot": {
        "description": "1 QC sample per original sublot from drying onward, plus 2 additional analyses per original from weighing onward.",
        "qc_added": lambda original: original,
        "analytical_additional": lambda original: original * 2,
    },
    "Lot Quality": {
        "description": "1 QC sample per original lot quality sample from drying onward, plus 8 additional analyses per original from weighing onward.",
        "qc_added": lambda original: original,
        "analytical_additional": lambda original: original * 8,
    },
}

ORIGINAL_ONLY_STEPS = {"Sorting", "Pre-Drying", "Reduction"}
ANALYTICAL_STEPS = {"Weighing", "Pelletizing", "XRF Analysis"}


def qc_count_breakdown(sample_type, original_qty):
    """Return original, QC, and final analytical counts for a batch."""
    original_qty = max(0, int(original_qty))
    rule = QC_RULES[sample_type]
    qc_added = int(rule["qc_added"](original_qty))
    analytical_additional = int(rule["analytical_additional"](original_qty))
    adjusted_after_reduction = original_qty + qc_added
    final_xrf_count = adjusted_after_reduction + analytical_additional
    return {
        "Original Samples": original_qty,
        "QC Added Samples": qc_added,
        "Analytical Additional Counts": analytical_additional,
        "Adjusted After Reduction": adjusted_after_reduction,
        "Final XRF Count": final_xrf_count,
    }


def adjusted_count_for_step(sample_type, original_qty, step):
    """Return the processing count that should drive duration/resource use for a step."""
    counts = qc_count_breakdown(sample_type, original_qty)
    if step in ORIGINAL_ONLY_STEPS:
        return counts["Original Samples"]
    if step in ANALYTICAL_STEPS:
        return counts["Final XRF Count"]
    return counts["Adjusted After Reduction"]


def step_count_metadata(sample_type, original_qty, step):
    """Build reusable count-display metadata for schedule rows and tooltips."""
    counts = qc_count_breakdown(sample_type, original_qty)
    adjusted_processing_count = adjusted_count_for_step(sample_type, original_qty, step)
    return {
        **counts,
        "Adjusted Processing Count": adjusted_processing_count,
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


sidebar_logo_html = ""
if SIDEBAR_LOGO_PATH.exists():
    encoded_sidebar_logo = base64.b64encode(SIDEBAR_LOGO_PATH.read_bytes()).decode("utf-8")
    sidebar_logo_html = (
        '<img class="sidebar-kmi-logo" '
        'src="data:image/jpeg;base64,' + encoded_sidebar_logo + '" '
        'alt="KMI logo">'
    )

if sidebar_logo_html:
    st.sidebar.markdown(sidebar_logo_html, unsafe_allow_html=True)
    
solver_time_limit = st.sidebar.slider("Solver Time Limit (seconds)", min_value=3, max_value=60, value=15)

# Persist batches and selected schedule mode across Streamlit reruns.
if "batches" not in st.session_state:
    st.session_state.batches = load_batches()
if "schedule_mode" not in st.session_state:
    st.session_state.schedule_mode = "fifo"

st.sidebar.markdown("### Append Batch")
with st.sidebar.form("add_batch_form", clear_on_submit=True):
    new_batch_id = st.text_input("Batch Number / Sample ID", value="")
    new_type = st.selectbox("Sample Type", list(rules.keys()))
    new_material = st.selectbox("Material", ["Limonite", "Saprolite"], index=0)
    new_qty = st.number_input(
        "Original Samples Received",
        min_value=1,
        max_value=10000,
        value=1,
        help="Enter only the actual received samples. QC and analytical additions are calculated automatically.",
    )
    new_received = st.datetime_input("Date and Time Received", value=ph_now.to_pydatetime())
    add_clicked = st.form_submit_button("Add Batch")

st.sidebar.markdown("### Shared Capacity Inputs")
personnel_total = st.sidebar.number_input("Personnel Present", min_value=1, max_value=100, value=20)
window_start = st.sidebar.time_input("Higher-capacity window start", value=datetime(2026, 5, 4, 14, 0).time())
window_end = st.sidebar.time_input("Higher-capacity window end", value=datetime(2026, 5, 5, 6, 0).time())

st.sidebar.markdown("### Equipment Settings")
ovens_high = st.sidebar.selectbox("Ovens operating during higher-capacity window", [1, 2], index=1)
ovens_low = st.sidebar.selectbox("Ovens operating outside that window", [1, 2], index=0)
pulverizer_count = st.sidebar.selectbox("Pulverizers operating", [1, 2], index=1)
xrf_machine_count = st.sidebar.selectbox("XRF machines operating", [1, 2], index=1)

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

if st.session_state.batches:
    edit_df = pd.DataFrame(st.session_state.batches)
    batch_list_display_df = edit_df.rename(
        columns={
            "batch_id": "Batch",
            "sample_type": "Type",
            "qty": "Original Samples Received",
            "material": "Material",
            "received_at": "Date and Time Received",
        }
    )
    lab_html_table_card("Batch List Table", batch_list_display_df)

    edit_df["Remove"] = False
    with st.expander("Edit Batch List Table", expanded=False):
        edited = st.data_editor(
            style_lab_table(edit_df),
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "batch_id": st.column_config.TextColumn("Batch"),
                "sample_type": st.column_config.TextColumn("Type"),
                "qty": st.column_config.NumberColumn("Original Samples Received"),
                "material": st.column_config.TextColumn("Material"),
                "received_at": st.column_config.DatetimeColumn("Date and Time Received"),
                "Remove": st.column_config.CheckboxColumn(
                    "Remove",
                    help="Select rows to remove when applying edits.",
                    default=False,
                ),
            },
        )
    apply_col, fifo_col, soft_col = st.columns(3)
    with apply_col:
        apply_clicked = st.button("Apply Batch Edits/Deletes", use_container_width=True)
    with fifo_col:
        fifo_clicked = st.button("FIFO Sublot Priority Solver", use_container_width=True)
    with soft_col:
        soft_clicked = st.button("Soft Priority Solver", use_container_width=True)

    if apply_clicked:
        remove_mask = edited["Remove"].fillna(False).astype(bool)
        kept = edited[~remove_mask].drop(columns=["Remove"]).copy()
        kept["qty"] = kept["qty"].astype(int)
        kept["received_at"] = pd.to_datetime(kept["received_at"])
        st.session_state.batches = kept.to_dict("records")
        save_batches(st.session_state.batches)
        st.rerun()
    if fifo_clicked:
        st.session_state.schedule_mode = "fifo"
        st.success("Showing FIFO Sublot Priority")
    if soft_clicked:
        st.session_state.schedule_mode = "soft"
        st.success("Showing Soft Priority")
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
        counts = qc_count_breakdown(b["sample_type"], qty)
        dry_qty = counts["Adjusted After Reduction"]
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
                {
                    "Batch": bid,
                    "Type": b["sample_type"],
                    "Qty": qty,
                    "Step": "Pre-Drying",
                    "Start": pre_start,
                    "Finish": pre_finish,
                    "Slots": pre_slots,
                    **step_count_metadata(b["sample_type"], qty, "Pre-Drying"),
                }
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
        # Reduction cycle time is per-sample process time; each plate handles one sample-process in parallel.
        effective_parallel_samples = max(1, len(used_plates))
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
                **step_count_metadata(b["sample_type"], qty, "Reduction"),
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
        shelves_need = math.ceil(dry_qty / r["drying_per_shelf"])
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
                "Qty": dry_qty,
                **step_count_metadata(b["sample_type"], qty, "Drying"),
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
        crush_cycles = math.ceil(dry_qty / crush_personnel)
        crush_per_sample = per_sample_minutes("crushing", b["sample_type"], material)
        crush_minutes = crush_cycles * crush_per_sample
        crush_finish = crush_start + timedelta(minutes=crush_minutes)

        crushing_jobs.append({"start": crush_start, "finish": crush_finish, "personnel": crush_personnel})
        crushing_rows.append(
            {
                "Batch": bid,
                "Type": b["sample_type"],
                "Qty": dry_qty,
                **step_count_metadata(b["sample_type"], qty, "Crushing"),
                "Start": crush_start,
                "Finish": crush_finish,
                "Personnel": crush_personnel,
            }
        )

        # Split quantity across pulverizers, preferring the earliest-available machine.
        machines = sorted(list(pulv_free.keys()), key=lambda m: pulv_free[m])
        q_base = dry_qty // len(machines)
        q_rem = dry_qty % len(machines)

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
                    **step_count_metadata(b["sample_type"], qty, "Pulverizing & Sieving"),
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
    batch_lookup = {b["batch_id"]: b for b in batches}

    def overall_row(bid, sample_type, step, start, finish):
        original_qty = int(batch_lookup[bid]["qty"])
        return {
            "Batch": bid,
            "Type": sample_type,
            "Step": step,
            "Start": start,
            "Finish": finish,
            **step_count_metadata(sample_type, original_qty, step),
        }

    overall_rows = []
    for bid in red_df["Batch"].unique():
        rt = red_df[red_df["Batch"] == bid].iloc[0]
        overall_rows.extend(
            [
                overall_row(bid, rt["Type"], "Sorting", rt["Sorting Start"], rt["Sorting End"]),
                overall_row(bid, rt["Type"], "Reduction", rt["Reduction Start"], rt["Reduction Finish"]),
            ]
        )

        d = dry_df[dry_df["Batch"] == bid]
        c = crush_df[crush_df["Batch"] == bid]
        p = pulv_df[pulv_df["Batch"] == bid]

        if not d.empty:
            pre = d[d["Step"] == "Pre-Drying"]
            if not pre.empty:
                overall_rows.append(
                    overall_row(bid, rt["Type"], "Pre-Drying", pre["Start"].min(), pre["Finish"].max())
                )
            d_final = d[d["Step"] == "Drying"]
            if not d_final.empty:
                overall_rows.append(
                    overall_row(bid, rt["Type"], "Drying", d_final["Start"].min(), d_final["Finish"].max())
                )
        if not c.empty:
            overall_rows.append(
                overall_row(bid, rt["Type"], "Crushing", c["Start"].min(), c["Finish"].max())
            )
        if not p.empty:
            pulv_finish = p["Finish"].max()
            overall_rows.append(
                overall_row(bid, rt["Type"], "Pulverizing & Sieving", p["Start"].min(), pulv_finish)
            )

            lab_sort_start = pulv_finish
            lab_sort_finish = lab_sort_start + timedelta(minutes=10)
            lab_dry_finish = lab_sort_finish + timedelta(minutes=rules[rt["Type"]]["lab_drying_minutes"])
            cool_finish = lab_dry_finish + timedelta(minutes=45)

            overall_rows.extend(
                [
                    overall_row(bid, rt["Type"], "Laboratory Sorting", lab_sort_start, lab_sort_finish),
                    overall_row(bid, rt["Type"], "Laboratory Drying", lab_sort_finish, lab_dry_finish),
                    overall_row(bid, rt["Type"], "Cooling in Desiccator", lab_dry_finish, cool_finish),
                ]
            )

    overall_df = pd.DataFrame(overall_rows)

    # --- Weighing (2 balances, priority-aware), Pelletizing, XRF allocation ---
    cool_steps = overall_df[overall_df["Step"] == "Cooling in Desiccator"].copy()
    weighing_tasks = []
    for _, row in cool_steps.iterrows():
        original_qty = int(batch_lookup[row["Batch"]]["qty"])
        qty = adjusted_count_for_step(row["Type"], original_qty, "Weighing")
        for sample_idx in range(1, qty + 1):
            weighing_tasks.append(
                {
                    "Batch": row["Batch"],
                    "Type": row["Type"],
                    "Sample": sample_idx,
                    "ready": row["Finish"],
                    **step_count_metadata(row["Type"], original_qty, "Weighing"),
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
                **step_count_metadata(chosen["Type"], int(batch_lookup[chosen["Batch"]]["qty"]), "Weighing"),
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
                **step_count_metadata(w["Type"], int(batch_lookup[w["Batch"]]["qty"]), "Pelletizing"),
                "Start": p_start,
                "Finish": p_finish,
                "Machine": "Pelletizer 1",
            }
        )
    pellet_df = pd.DataFrame(pellet_rows)

    xrf_tasks = []
    for batch_id, grp in pellet_df.groupby("Batch", sort=False):
        grp = grp.sort_values("Finish")
        sample_finishes = list(grp["Finish"])
        batch_type = grp["Type"].iloc[0]
        for chunk_idx in range(0, len(sample_finishes), 10):
            chunk_samples = min(10, len(sample_finishes) - chunk_idx)
            xrf_tasks.append(
                {
                    "Batch": batch_id,
                    "Type": batch_type,
                    "Chunk": f"{chunk_idx + 1}-{chunk_idx + chunk_samples}",
                    "Samples": chunk_samples,
                    **step_count_metadata(batch_type, int(batch_lookup[batch_id]["qty"]), "XRF Analysis"),
                    "ready": sample_finishes[chunk_idx + chunk_samples - 1],
                }
            )
    
    xrf_rows = []
    xrf_free = {f"XRF {i}": pd.Timestamp.min for i in range(1, int(xrf_machine_count) + 1)}

    def xrf_task_priority(t):
        return (0 if t["Type"] == "Sublot" else 1, t["ready"], t["Batch"], t["Chunk"])

    pending_xrf = xrf_tasks[:]
    while pending_xrf:
        machine = min(xrf_free, key=lambda m: xrf_free[m])
        current_t = xrf_free[machine]
        ready = [t for t in pending_xrf if t["ready"] <= current_t]
        if not ready:
            next_ready = min(t["ready"] for t in pending_xrf)
            current_t = max(current_t, next_ready)
            ready = [t for t in pending_xrf if t["ready"] <= current_t]
        chosen = sorted(ready, key=xrf_task_priority)[0]
        x_start = current_t
        x_finish = x_start + timedelta(minutes=30)
        xrf_free[machine] = x_finish
        pending_xrf.remove(chosen)
        xrf_rows.append(
            {
                "Batch": chosen["Batch"],
                "Type": chosen["Type"],
                "Chunk": chosen["Chunk"],
                "Samples": chosen["Samples"],
                "Machine": machine,
                "Start": x_start,
                "Finish": x_finish,
                **{
                    key: value
                    for key, value in chosen.items()
                    if key not in {"Batch", "Type", "Chunk", "Samples", "ready"}
                },
            }
        )
    xrf_df = pd.DataFrame(xrf_rows)

    for bid in overall_df["Batch"].unique():
        w = weighing_df[weighing_df["Batch"] == bid]
        pel = pellet_df[pellet_df["Batch"] == bid]
        x = xrf_df[xrf_df["Batch"] == bid]
        batch_type = overall_df[overall_df["Batch"] == bid]["Type"].iloc[0]
        if not w.empty:
            overall_df.loc[len(overall_df)] = overall_row(bid, batch_type, "Weighing", w["Start"].min(), w["Finish"].max())
        if not pel.empty:
            overall_df.loc[len(overall_df)] = overall_row(bid, batch_type, "Pelletizing", pel["Start"].min(), pel["Finish"].max())
        if not x.empty:
            overall_df.loc[len(overall_df)] = overall_row(bid, batch_type, "XRF Analysis", x["Start"].min(), x["Finish"].max())

    return red_df, dry_df, crush_df, pulv_df, overall_df, weighing_df, pellet_df, xrf_df


def optimize_batch_order(batches, time_limit_seconds=None):
    """Return the deterministic FIFO order with Sublot tie-break priority."""
    if not batches:
        return batches, "FEASIBLE", "No batches."

    # FIFO baseline by received time.
    # Tie-break behavior:
    # - Sublot gets priority when same-ready contention occurs
    # - Face and Mine preserve first-input order for same timestamp (single-batch progression)
    indexed = list(enumerate(batches))
    ordered_pairs = sorted(
        indexed,
        key=lambda pair: (
            pair[1]["received_at"],
            0 if pair[1]["sample_type"] == "Sublot" else 1,
            pair[0],  # preserve first-input order on ties (especially Face/Mine)
        ),
    )
    ordered = [b for _, b in ordered_pairs]
    return ordered, "FEASIBLE", "FIFO Sublot Priority ordering applied."


def evaluate_order(order):
    """Score a candidate order by completion time, with Sublot priority as a soft tie-breaker."""
    _, _, _, _, candidate_overall_df, _, _, _ = schedule_batches(order)
    if candidate_overall_df.empty:
        return (pd.Timestamp.max, pd.Timestamp.max, pd.Timestamp.max)

    finish_by_batch = candidate_overall_df.groupby("Batch")["Finish"].max()
    makespan = finish_by_batch.max()
    sublot_ids = [b["batch_id"] for b in order if b["sample_type"] == "Sublot"]
    sublot_total = sum((finish_by_batch[bid].value if bid in finish_by_batch else pd.Timestamp.max.value) for bid in sublot_ids)
    total_completion = sum(ts.value for ts in finish_by_batch)
    return (makespan.value, sublot_total, total_completion)


def improve_order_with_adjacent_swaps(initial_order, deadline):
    """Improve a large-batch heuristic order while respecting the solver time limit."""
    best_order = list(initial_order)
    best_score = evaluate_order(best_order)
    improved = True

    while improved and time.monotonic() < deadline:
        improved = False
        for idx in range(len(best_order) - 1):
            if time.monotonic() >= deadline:
                break
            candidate = best_order[:]
            candidate[idx], candidate[idx + 1] = candidate[idx + 1], candidate[idx]
            candidate_score = evaluate_order(candidate)
            if candidate_score < best_score:
                best_order = candidate
                best_score = candidate_score
                improved = True

    return best_order, best_score


def optimize_soft_priority_order(batches, time_limit_seconds):
    """
    Search for the order with the least overall completion time.

    Sublot priority is treated as a soft tie-breaker after the overall completion
    time, so the solver can choose a faster total schedule when one exists.
    """
    if not batches:
        return batches, "FEASIBLE", "No batches."

    deadline = time.monotonic() + max(1, int(time_limit_seconds))
    fifo_order, _, _ = optimize_batch_order(batches)
    best_order = fifo_order
    best_score = evaluate_order(best_order)
    evaluated = 1

    if len(batches) <= 8:
        for candidate in itertools.permutations(batches):
            if time.monotonic() >= deadline:
                return (
                    best_order,
                    "TIME_LIMIT",
                    f"Soft Priority solver evaluated {evaluated} order(s) within {time_limit_seconds} seconds and returned the best schedule found.",
                )
            candidate_order = list(candidate)
            candidate_score = evaluate_order(candidate_order)
            evaluated += 1
            if candidate_score < best_score:
                best_order = candidate_order
                best_score = candidate_score
        return (
            best_order,
            "OPTIMAL",
            f"Soft Priority solver evaluated all {evaluated} order(s) and minimized overall completion time.",
        )

    heuristic_order = sorted(
        batches,
        key=lambda b: (
            b["received_at"],
            0 if b["sample_type"] == "Sublot" else 1,
            int(b["qty"]),
            b["batch_id"],
        ),
    )
    best_order, best_score = improve_order_with_adjacent_swaps(heuristic_order, deadline)
    return (
        best_order,
        "FEASIBLE",
        f"Soft Priority solver used a time-limited heuristic for {len(batches)} batches and returned the best schedule found within {time_limit_seconds} seconds.",
    )


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


CHART_PAPER_COLOR = "#081C15"
CHART_PLOT_COLOR = "#0B2A21"
CHART_GRID_COLOR = "#355E3B"

CHART_TEXT_COLOR = "#F4F7F5"
CHART_MUTED_TEXT_COLOR = "#C7D6CC"
CHART_ACCENT_COLOR = "#95D5B2"
CHART_BAR_OUTLINE_COLOR = "#08120E"
CHART_BAR_OPACITY = 0.92
PROCESS_STEP_COLORS = {
    "Sorting": "#95D5B2",
    "Pre-Drying": "#5BC0BE",
    "Reduction": "#F9C74F",
    "Drying": "#F95738",
    "Crushing": "#4D7EA8",
    "Pulverizing & Sieving": "#78C850",
    "Laboratory Sorting": "#B8A1E3",
    "Laboratory Drying": "#D9E650",
    "Cooling in Desiccator": "#F15BB5",
    "Weighing": "#EAEAEA",
    "Pelletizing": "#FFB703",
    "XRF Analysis": "#00B4D8",
}
BATCH_COLOR_SEQUENCE = [
    "#5BC0BE",
    "#F9C74F",
    "#F95738",
    "#4D7EA8",
    "#B8A1E3",
    "#D9E650",
    "#F15BB5",
    "#FFB703",
    "#00B4D8",
    "#EAEAEA",
    "#95D5B2",
    "#78C850",
]


def timeline_chart_height(row_count, minimum=430, row_height=34, maximum=900):
    """Scale timeline height so long process schedules stay readable without overwhelming the page."""
    return min(maximum, max(minimum, 170 + int(row_count) * row_height))


def apply_kmi_chart_theme(fig, legend_title_text, row_count=None):
    """Apply the military-green laboratory palette to Plotly timeline charts."""
    if row_count is not None:
        fig.update_layout(height=timeline_chart_height(row_count))

    fig.update_layout(
        paper_bgcolor=CHART_PAPER_COLOR,
        plot_bgcolor=CHART_PLOT_COLOR,
        font=dict(color=CHART_TEXT_COLOR, family="Inter, sans-serif", size=13),
        hovermode="closest",
        bargap=0.24,
        legend_title_text=legend_title_text,
        legend=dict(
            bgcolor="rgba(8, 28, 21, 0.90)",
            bordercolor="rgba(149, 213, 178, 0.35)",
            borderwidth=1,
            font=dict(color=CHART_TEXT_COLOR, size=12),
            itemwidth=42,
            itemsizing="constant",
            orientation="v",
            title_font=dict(color=CHART_TEXT_COLOR, size=13),
            tracegroupgap=8,
            x=1.02,
            xanchor="left",
            y=1,
            yanchor="top",
        ),
        margin=dict(l=28, r=215, t=34, b=72),
        hoverlabel=dict(
            bgcolor="#10261F",
            bordercolor="#95D5B2",
            font_color="#F4F7F5",
            font_family="Inter, sans-serif",
            font_size=13,
        ),
    )
    fig.update_xaxes(
        automargin=True,
        color=CHART_MUTED_TEXT_COLOR,
        gridcolor="rgba(53, 94, 59, 0.42)",
        griddash="dot",
        linecolor="rgba(149, 213, 178, 0.75)",
        mirror=True,
        showgrid=True,
        showline=True,
        tickfont=dict(color=CHART_MUTED_TEXT_COLOR, size=12),
        ticklabelposition="outside",
        ticks="outside",
        title_font=dict(color=CHART_TEXT_COLOR, size=13),
        title_standoff=14,
        zeroline=False,
    )
    fig.update_yaxes(
        automargin=True,
        color=CHART_MUTED_TEXT_COLOR,
        gridcolor="rgba(53, 94, 59, 0.22)",
        griddash="dot",
        linecolor="rgba(149, 213, 178, 0.75)",
        mirror=True,
        showgrid=True,
        showline=True,
        tickfont=dict(color=CHART_MUTED_TEXT_COLOR, size=12),
        ticks="outside",
        title_font=dict(color=CHART_TEXT_COLOR, size=13),
        title_standoff=12,
        zeroline=False,
    )
    fig.update_traces(
        marker=dict(
            line=dict(color="#08120E", width=1)
        ),
        opacity=CHART_BAR_OPACITY,
    )
    return fig


def show_legend_on_right(fig, title_text, row_count=None):
    """Keep color legends visible on the right side of themed timeline charts."""
    return apply_kmi_chart_theme(fig, title_text, row_count=row_count)

if st.session_state.batches:
    if st.session_state.schedule_mode == "soft":
        best_order, solver_status, solver_message = optimize_soft_priority_order(st.session_state.batches, solver_time_limit)
        schedule_mode_label = "Soft Priority"
    else:
        best_order, solver_status, solver_message = optimize_batch_order(st.session_state.batches)
        schedule_mode_label = "FIFO Sublot Priority"

    red_df, dry_df, crush_df, pulv_df, overall_df, weighing_df, pellet_df, xrf_df = schedule_batches(best_order)

    if overall_df.empty:
        st.warning("No batches to schedule.")
    else:
        st.info(f"Schedule Mode: {schedule_mode_label} | Solver Status: {solver_status}")
        st.caption(solver_message)


        qc_display_rows = []
        for batch in best_order:
            original_qty = int(batch["qty"])
            counts = qc_count_breakdown(batch["sample_type"], original_qty)
            qc_display_rows.append(
                {
                    "Batch": batch["batch_id"],
                    "Type": batch["sample_type"],
                    **counts,
                    "QC Rule": QC_RULES[batch["sample_type"]]["description"],
                }
            )
        qc_counts_df = pd.DataFrame(qc_display_rows)
        qc_counts_display_df = qc_counts_df.rename(
            columns={
                "QC Added Samples": "QC Twin Sample",
                "Analytical Additional Counts": "QC Pellet Sample",
            }
        )
        lab_html_table_card(
            "QC Adjusted Sample Counts",
            qc_counts_display_df,
            caption=(
                "Original Samples are the user-entered received samples only. "
                "QC Twin Sample begins at Drying. QC Pellet Sample begins at Weighing. "
                "Final XRF Count drives weighing, pelletizing, and XRF batching."
            ),
        )
        
        table_section_title = "Batch Completion Summary"
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
        lab_html_table_card(table_section_title, finals)

        process_specs_title = "Process Time Specifications"
        spec_rows = [
            {
                "Process Step": "Sorting",
                "Face": rules["Face"]["sorting_minutes"],
                "Mine": rules["Mine"]["sorting_minutes"],
                "Sublot": rules["Sublot"]["sorting_minutes"],
                "Lot Quality": rules["Lot Quality"]["sorting_minutes"],
                "Processing Basis": "Per Batch",
                "Resource Used": "Personnel",
                "Notes": "Fixed per batch by sample type; uses Original Samples only.",
            },
            {
                "Process Step": "Reduction",
                "Face": per_sample_minutes("reduction", "Face", "N/A"),
                "Mine": "Limonite 30 / Saprolite 45",
                "Sublot": "Limonite 45 / Saprolite 60",
                "Lot Quality": rules["Lot Quality"]["reduction_minutes"],
                "Processing Basis": "Per Batch",
                "Resource Used": "Personnel / Plate",
                "Notes": f"Uses Original Samples only; personnel headcount constrained by user input ({personnel_total}).",
            },
            {
                "Process Step": "Drying",
                "Face": rules["Face"]["drying_minutes"],
                "Mine": rules["Mine"]["drying_minutes"],
                "Sublot": rules["Sublot"]["drying_minutes"],
                "Lot Quality": rules["Lot Quality"]["drying_minutes"],
                "Processing Basis": "Per Cycle",
                "Resource Used": "Oven",
                "Notes": f"Uses adjusted count after QC additions; capacity varies by oven window ({ovens_high}/{ovens_low} ovens).",
            },
            {
                "Process Step": "Crushing",
                "Face": per_sample_minutes("crushing", "Face", "N/A"),
                "Mine": "Limonite 10 / Saprolite 15",
                "Sublot": "Limonite 15 / Saprolite 15",
                "Lot Quality": rules["Lot Quality"]["crushing_per_sample"],
                "Processing Basis": "Per Sample",
                "Resource Used": "Personnel",
                "Notes": f"Uses adjusted count after QC additions; parallelized by available personnel ({personnel_total} max).",
            },
            {
                "Process Step": "Pulverizing & Sieving",
                "Face": per_sample_minutes("pulverizing", "Face", "N/A"),
                "Mine": "Limonite 15 / Saprolite 15",
                "Sublot": "Limonite 30 / Saprolite 30",
                "Lot Quality": rules["Lot Quality"]["pulv_per_sample"],
                "Processing Basis": "Per Sample",
                "Resource Used": "Pulverizer",
                "Notes": f"Uses adjusted count after QC additions; distributed in parallel across {pulverizer_count} pulverizer(s).",
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
                "Notes": "Uses Final XRF Count after QC and analytical additions; two balances in parallel; Sublot prioritized when ready.",
            },
            {
                "Process Step": "Pelletizing",
                "Face": 3,
                "Mine": 3,
                "Sublot": 3,
                "Lot Quality": 3,
                "Processing Basis": "Per Sample",
                "Resource Used": "Pelletizer",
                "Notes": "Uses Final XRF Count after QC and analytical additions; single pelletizer, serialized.",
            },
            {
                "Process Step": "XRF Analysis",
                "Face": 30,
                "Mine": 30,
                "Sublot": 30,
                "Lot Quality": 30,
                "Processing Basis": "Per 10 Samples",
                "Resource Used": "XRF Machine",
                "Notes": f"Uses Final XRF Count; 30 min per 10-sample run or partial run; parallel across {xrf_machine_count} XRF machine(s).",
            },
        ]
        lab_html_table_card(process_specs_title, pd.DataFrame(spec_rows))

        step_summary_title = "Summary per Processing Step (per Batch)"
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

        with st.container(border=True):
            lab_section_title(step_summary_title)
            filter_col_batch, filter_col_step = st.columns(2)
            batch_filter_options = ["All batches"] + step_batch_summary["Batch Label"].drop_duplicates().tolist()
            available_steps = [
                step
                for step in step_order
                if step in set(step_batch_summary["Step"].astype(str))
            ]
            step_filter_options = ["All processing steps"] + available_steps
            with filter_col_batch:
                selected_batch_label = st.selectbox(
                    "Select batch",
                    batch_filter_options,
                    help="Choose a batch to show only that batch's processing-step summary.",
                )
            with filter_col_step:
                selected_step = st.selectbox(
                    "Select processing step",
                    step_filter_options,
                    help="Choose a processing step to show that step across all batches.",
                )

            filtered_step_summary = step_batch_summary.copy()
            if selected_batch_label != "All batches":
                filtered_step_summary = filtered_step_summary[
                    filtered_step_summary["Batch Label"] == selected_batch_label
                ]
            if selected_step != "All processing steps":
                filtered_step_summary = filtered_step_summary[
                    filtered_step_summary["Step"].astype(str) == selected_step
                ]

            render_lab_html_table(
                filtered_step_summary[[
                    "Batch Label",
                    "Step",
                    "Start",
                    "Finish",
                    "Duration (Min/Hr)",
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Adjusted Processing Count",
                ]]
            )

        lab_section_title("Overall Sample Prep and Laboratory Process Chart")
        active_overall_df = overall_df[overall_df["Finish"] > ph_now].copy()
        if active_overall_df.empty:
            st.info("No active sample batch to display.")
        else:
            active_overall_df["Step"] = pd.Categorical(
                active_overall_df["Step"], categories=step_order, ordered=True
            )
            active_overall_df["Label"] = active_overall_df["Batch"] + " - " + active_overall_df["Type"]
            fig_overall = px.timeline(
                active_overall_df,
                x_start="Start",
                x_end="Finish",
                y="Label",
                color="Step",
                category_orders={"Step": step_order},
                color_discrete_map=PROCESS_STEP_COLORS,
                hover_data=[
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Adjusted Processing Count",
                    "Final XRF Count",
                ],
            )
            show_legend_on_right(fig_overall, "Process Step", row_count=active_overall_df["Label"].nunique())
            fig_overall.update_yaxes(autorange="reversed")
            fig_overall.update_yaxes(title_text="Batch No.")
            st.plotly_chart(fig_overall, use_container_width=True)

        lab_section_title("Plate Assignment Chart")
        active_red_df = red_df[red_df["Reduction Finish"] > ph_now].copy()
        if active_red_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_plate = px.timeline(
                active_red_df,
                x_start="Reduction Start",
                x_end="Reduction Finish",
                y="Plate",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,
                hover_data=["Original Samples", "QC Added Samples", "Adjusted Processing Count"],
            )
            show_legend_on_right(fig_plate, "Batch", row_count=active_red_df["Plate"].nunique())
            fig_plate.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_plate, use_container_width=True)

        lab_section_title("Drying Oven Assignment Chart")
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
                        "Original Samples": r.get("Original Samples"),
                        "QC Added Samples": r.get("QC Added Samples"),
                        "Analytical Additional Counts": r.get("Analytical Additional Counts"),
                        "Adjusted Processing Count": r.get("Adjusted Processing Count"),
                    }
                )
        dry_plot_df = pd.DataFrame(dry_plot)
        if dry_plot_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_dry = px.timeline(
                dry_plot_df,
                x_start="Start",
                x_end="Finish",
                y="Slot",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=[
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Adjusted Processing Count",
                ],
            )
            show_legend_on_right(fig_dry, "Batch", row_count=dry_plot_df["Slot"].nunique())
            fig_dry.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_dry, use_container_width=True)

        lab_section_title("Crushing Personnel Assignment Chart")
        crush_df["Lane"] = crush_df.apply(lambda x: f"{x['Batch']} ({x['Personnel']}P)", axis=1)
        active_crush_df = crush_df[crush_df["Finish"] > ph_now].copy()
        if active_crush_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_cr = px.timeline(
                active_crush_df,
                x_start="Start",
                x_end="Finish",
                y="Lane",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=["Original Samples", "QC Added Samples", "Adjusted Processing Count"],
            )
            show_legend_on_right(fig_cr, "Batch", row_count=active_crush_df["Lane"].nunique())
            fig_cr.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_cr, use_container_width=True)

        lab_section_title("Pulverizer Assignment Chart")
        active_pulv_df = pulv_df[pulv_df["Finish"] > ph_now].copy()
        if active_pulv_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_p = px.timeline(
                active_pulv_df,
                x_start="Start",
                x_end="Finish",
                y="Machine",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=["Original Samples", "QC Added Samples", "Adjusted Processing Count"],
            )
            show_legend_on_right(fig_p, "Batch", row_count=active_pulv_df["Machine"].nunique())
            fig_p.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p, use_container_width=True)

        lab_section_title("Weighing Chart")
        active_weighing_df = weighing_df[weighing_df["Finish"] > ph_now].copy()
        if active_weighing_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_w = px.timeline(
                active_weighing_df,
                x_start="Start",
                x_end="Finish",
                y="Balance",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=[
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Final XRF Count",
                ],
            )
            show_legend_on_right(fig_w, "Batch", row_count=active_weighing_df["Balance"].nunique())
            fig_w.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_w, use_container_width=True)

        lab_section_title("Pelletizing Chart")
        active_pellet_df = pellet_df[pellet_df["Finish"] > ph_now].copy()
        if active_pellet_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_pel = px.timeline(
                active_pellet_df,
                x_start="Start",
                x_end="Finish",
                y="Machine",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=[
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Final XRF Count",
                ],
            )
            show_legend_on_right(fig_pel, "Batch", row_count=active_pellet_df["Machine"].nunique())
            fig_pel.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_pel, use_container_width=True)

        lab_section_title("XRF Assignment Chart")
        active_xrf_df = xrf_df[xrf_df["Finish"] > ph_now].copy()
        if active_xrf_df.empty:
            st.info("No active sample batch to display.")
        else:
            fig_xrf = px.timeline(
                active_xrf_df,
                x_start="Start",
                x_end="Finish",
                y="Machine",
                color="Batch",
                color_discrete_sequence=BATCH_COLOR_SEQUENCE,                
                hover_data=[
                    "Samples",
                    "Original Samples",
                    "QC Added Samples",
                    "Analytical Additional Counts",
                    "Final XRF Count",
                ],
            )
            show_legend_on_right(fig_xrf, "Batch", row_count=active_xrf_df["Machine"].nunique())
            fig_xrf.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_xrf, use_container_width=True)

        st.success(f"Overall estimated completion time: {overall_df['Finish'].max()}")
