import streamlit as st
import plotly.graph_objects as go
from utils import load_all_data, aggregate_dashboard_metrics
import os

# 1. UI Page Config
st.set_page_config(page_title="Supply Chain Dashboard", layout="wide", page_icon="📈")

# 2. Main Title and Layout
st.title("📈 Retail Supply Chain Dashboard")
st.markdown("### Weekly Sales vs. Inventory Tracking")
st.markdown("---")

# 3. Load Data Safely
outputs_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")

try:
    sales_df, inv_df = load_all_data(outputs_dir)
except Exception as e:
    st.error(f"Error loading CSV data: {e}")
    st.stop()

if sales_df.empty and inv_df.empty:
    st.warning("No data found. Make sure you have run the underlying simulation engine first.")
    st.stop()

# 4. Interactive Sidebar Filters
st.sidebar.header("Filter Configuration: ⚙️")

# Determine distinct values for filters from sales data
all_stores = sorted(sales_df["StoreCode"].dropna().unique().tolist())
all_items = sorted(sales_df["ItemCode"].dropna().unique().tolist())

selected_stores = st.sidebar.multiselect("Filter by StoreCode", all_stores, default=[])
selected_items = st.sidebar.multiselect("Filter by ItemCode", all_items, default=[])

st.sidebar.markdown("---")
st.sidebar.info("Leaving filters empty shows global aggregate supply chain data.")

# 5. Transform / Aggregate Metrics based on Filters
agg_df = aggregate_dashboard_metrics(sales_df, inv_df, stores=selected_stores, items=selected_items)

# 6. Build the Visualizations
if not agg_df.empty:
    # Use Plotly Graph Objects to support dual Y-Axis plotting
    fig = go.Figure()
    
    # Trace 1: Sales as Bar Chart (Primary Y-axis)
    fig.add_trace(go.Bar(
        x=agg_df["Week"],
        y=agg_df["Total Sales"],
        name="Weekly Sales",
        marker_color="#2ca02c",  # Nice distinct green line for sales 
        opacity=0.8
    ))
    
    # Trace 2: Inventory as Line Chart (Secondary Y-axis)
    fig.add_trace(go.Scatter(
        x=agg_df["Week"],
        y=agg_df["Total Inventory"],
        name="Quantity On Hand",
        mode='lines+markers',
        line=dict(color='#ff7f0e', width=3),
        marker=dict(size=6),
        yaxis="y2"  # Targets the secondary axis
    ))
    
    # Update layout for dual axis rendering
    fig.update_layout(
        title="Sales vs. Physical Inventory Availability",
        xaxis=dict(title="Simulation Calendar Week", showgrid=False),
        yaxis=dict(
            title="Sales Quantity", 
            showgrid=True, 
            gridcolor="lightgray"
        ),
        yaxis2=dict(
            title="Total Inventory On Hand", 
            overlaying="y", 
            side="right",
            showgrid=False
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.5)"),
        barmode='group'
    )
    
    # Apply standard dark/light theme awareness from Streamlit
    if st.get_option("theme.base") == "dark":
        fig.update_layout(template="plotly_dark", legend=dict(bgcolor="rgba(0,0,0,0.5)"))
        
    st.plotly_chart(fig, use_container_width=True)
    
    # Expose raw table details strictly as optional collapse block to keep UI minimal
    with st.expander("View Underlying Summary Data"):
        st.dataframe(agg_df, use_container_width=True)
else:
    st.info("No data matched your selected combinations.")
