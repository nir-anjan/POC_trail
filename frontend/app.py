"""
app.py — Streamlit Supply Chain Dashboard
Run: streamlit run frontend/app.py

Store selector → Item selector → Weekly Sales (bars) + Inventory (green line)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
from utils import (
    get_outputs_dir,
    load_sales,
    load_inventory,
    get_stores,
    get_items,
    get_chart_data,
)

# ─── Color Palette ──────────────────────────────────────────────────────────
COLORS = {
    "alabaster": "#E2E1E2",
    "black": "#000000",
    "emerald": "#53BA79",
    "pale_sky": "#B9D3EE",
    "wisteria": "#74A2E7",
    "cotton_rose": "#F5C5C5",
    "light_coral": "#EA7C7C",
    "soft_apricot": "#F2D3AF",
    "sunlit_clay": "#E7AA64",
    "ochre": "#D97706"
}

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="METRAI | Supply Chain Dashboard",
    layout="wide",
    page_icon=None,
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    
    .main {{
        background-color: white;
        font-family: 'Inter', sans-serif;
    }}
    
    .stApp {{
        background-color: white;
    }}

    .block-container {{
        padding-top: 1rem;
        padding-bottom: 0rem;
    }}

    h1 {{
        color: {COLORS['ochre']};
        font-weight: 700;
        letter-spacing: -0.05rem;
    }}

    .stMetric {{
        background-color: {COLORS['alabaster']};
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid {COLORS['ochre']};
    }}

    /* Top navigation bar style simulation */
    .nav-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid {COLORS['alabaster']};
        margin-bottom: 20px;
    }}
    
    .nav-logo {{
        font-size: 24px;
        font-weight: 800;
        color: {COLORS['black']};
    }}
    
    .nav-logo span {{
        color: {COLORS['ochre']};
    }}
</style>
""", unsafe_allow_html=True)

# ── Load Data ────────────────────────────────────────────────────────────────
outputs_dir = get_outputs_dir()
sales_df = load_sales(outputs_dir)
inv_df   = load_inventory(outputs_dir)

if sales_df.empty:
    st.error("No simulation data found. Run `python3 generate.py --demand_file demand.csv` first.")
    st.stop()

# ── Header ───────────────────────────────────────────────────────────────────
st.title("Supply Chain Simulation Dashboard")
st.caption("DC → Store flow  |  Daily simulation, weekly aggregation")
st.markdown("---")

# ── Sidebar Selectors ────────────────────────────────────────────────────────
st.sidebar.header("Selection")

stores = get_stores(sales_df)
selected_store = st.sidebar.selectbox("Select Store", stores)

items = get_items(sales_df, selected_store)
selected_item  = st.sidebar.selectbox("Select Item", items)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Store:** `{selected_store}`")
st.sidebar.markdown(f"**Item:**  `{selected_item}`")

# ── Get Chart Data ───────────────────────────────────────────────────────────
df = get_chart_data(sales_df, inv_df, selected_store, selected_item)

if df.empty:
    st.warning("No data for this combination.")
    st.stop()

# ── KPI Metrics ──────────────────────────────────────────────────────────────
total_sales     = int(df["SalesQuantity"].sum())
avg_weekly_sales= int(df["SalesQuantity"].mean())
min_inv         = int(df["QuantityOnHand"].min())
weeks_stockout  = int((df["QuantityOnHand"] == 0).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales (10 wks)",   f"{total_sales:,} units")
col2.metric("Avg Weekly Sales",        f"{avg_weekly_sales:,} units")
col3.metric("Min Inventory (EOW)",     f"{min_inv:,} units",
            delta="Stockout risk" if min_inv == 0 else None,
            delta_color="inverse")
col4.metric("Weeks with Zero Stock",  f"{weeks_stockout} / {len(df)}")

st.markdown("---")

# ── Main Chart ───────────────────────────────────────────────────────────────
st.subheader(f"Weeks 1-10 | {selected_store} — {selected_item}s")

fig = go.Figure()

# ── Bar: Weekly Sales ────────────────────────────────────────────────────────
fig.add_trace(go.Bar(
    x=df["WeekId"],
    y=df["SalesQuantity"],
    name="Actual Sales",
    marker=dict(
        color=COLORS['sunlit_clay'],
        opacity=0.8,
    ),
    yaxis="y",
    hovertemplate="<b>%{x}</b><br>Sales: %{y} units<extra></extra>",
))

# ── Line: End-of-Week Inventory (EMERALD GREEN) ──────────────────────────────
fig.add_trace(go.Scatter(
    x=df["WeekId"],
    y=df["QuantityOnHand"],
    name="Retail Inventory",
    mode="lines",
    line=dict(color=COLORS['emerald'], width=2, shape='spline'),
    yaxis="y2",
    hovertemplate="<b>%{x}</b><br>Inventory: %{y} units<extra></extra>",
))

# ── Layout ───────────────────────────────────────────────────────────────────
fig.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        title="WEEKS",
        showgrid=True,
        gridcolor=COLORS['alabaster'],
        color=COLORS['black'],
        tickfont=dict(size=10),
    ),
    yaxis=dict(
        title="Cases / week",
        showgrid=True,
        gridcolor=COLORS['alabaster'],
        color=COLORS['black'],
        rangemode="tozero",
        tickfont=dict(size=10),
    ),
    yaxis2=dict(
        title="Retail Inventory",
        overlaying="y",
        side="right",
        showgrid=False,
        color=COLORS['emerald'],
        rangemode="tozero",
        tickfont=dict(size=10),
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=10, color=COLORS['black']),
        bgcolor="rgba(0,0,0,0)",
    ),
    hovermode="x unified",
    margin=dict(t=50, b=50, l=50, r=50),
    height=550,
)

st.plotly_chart(fig, use_container_width=True)

# ── Raw Data Expander ─────────────────────────────────────────────────────────
with st.expander("View Weekly Data Table"):
    st.dataframe(
        df.rename(columns={
            "WeekId":        "Week",
            "SalesQuantity": "Sales (units)",
            "QuantityOnHand":"Inventory EOW (units)",
        }),
        use_container_width=True,
        hide_index=True,
    )
