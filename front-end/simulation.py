import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import random

# ==============================================================================
# 1. CONFIG & STYLE
# ==============================================================================
st.set_page_config(layout="wide", page_title="The Sandbox")

st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #0e1117; }
    
    /* GLASS CARD STYLING 
       Targets containers with border=True to give them the translucent look.
    */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(30, 33, 48, 0.4) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        padding: 20px !important;
    }
    
    /* COMPACT METRIC CARDS 
       Reduces padding to make the top metrics row look sleek.
    */
    div[data-testid="stMetric"], .stMetric { 
        background: rgba(255, 255, 255, 0.05); 
        padding: 8px 15px !important; 
        border-radius: 10px; 
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. HELPER FUNCTIONS (LOGIC LAYER)
# ==============================================================================

def init_state():
    """Initializes the session state variables if they don't exist yet."""
    # Default values for the sliders
    defaults = {
        "budget": 10, "interest": 250, "market": 2.5,  # Finance Tab
        "price": 85, "retention": 92, "leads": 450     # Strategy Tab
    }
    
    # ui_state: Controls the position of the sliders
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = defaults.copy()
        
    # sim_params: Controls the data shown on the graph (only updates on 'Run')
    if "sim_params" not in st.session_state:
        st.session_state.sim_params = defaults.copy()
    
    if "ai_note" not in st.session_state:
        st.session_state.ai_note = None

def calculate_projections(params):
    """
    Core math engine. Takes simulation parameters and returns the data for the chart.
    Returns: (projected_data, baseline_data, months_list)
    """
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    x = np.arange(len(months))
    
    # The 'Business Logic' formula
    impact = (params["budget"] * 12) + (params["leads"] * 0.3) - (params["interest"] * 1.2)
    baseline = 4000 + 400 * np.sin(x * 0.8)
    projected = baseline + impact
    
    return projected, baseline, months

# ==============================================================================
# 3. CALLBACKS (INTERACTION LAYER)
# ==============================================================================

def run_simulation():
    """Triggered by the 'Run Simulation' button. Updates the graph."""
    # Copy values from sliders (keys) to the simulation parameters
    st.session_state.sim_params = {
        "budget": st.session_state.slider_budget,
        "interest": st.session_state.slider_interest,
        "market": st.session_state.slider_market,
        "price": st.session_state.slider_price,
        "retention": st.session_state.slider_retention,
        "leads": st.session_state.slider_leads
    }
    st.toast("Projections updated.", icon="✅")

def apply_ai_scenario():
    """Triggered by the 'Adjust Sliders' button. Updates UI state based on text input."""
    query = st.session_state.get("user_query", "").lower()
    
    if not query:
        st.toast("Type a scenario first.", icon="✍️")
        return

    # Simple keyword matching logic
    if "growth" in query or "expand" in query:
        st.session_state.ui_state.update({"budget": 30, "leads": 750})
        st.session_state.ai_note = "Prepared growth settings. Review the sliders and hit 'Run'."
    elif "risk" in query or "crash" in query:
        st.session_state.ui_state.update({"budget": -15, "interest": 400, "retention": 70})
        st.session_state.ai_note = "Defensive posture ready. Review sliders and hit 'Run'."
    else:
        st.session_state.ui_state.update({"budget": random.randint(-20, 20), "leads": random.randint(200, 800)})
        st.session_state.ai_note = "Sliders tweaked for your scenario. Ready for simulation."

# Initialize the app state immediately
init_state()

# ==============================================================================
# 4. MAIN LAYOUT
# ==============================================================================
col_main, col_sidebar = st.columns([3, 1], gap="large")

# --- LEFT COLUMN: MAIN VISUALIZATION ---
with col_main:
    
    # CONTAINER A: Header & Graph
    with st.container(border=True):
        st.title("Simulation Sandbox")
        st.markdown("---") 

        # 1. Calculate Data
        p = st.session_state.sim_params
        projected, baseline, months = calculate_projections(p)
        
        # 2. Display Top Metrics
        m1, m2, m3 = st.columns(3)
        diff = ((projected.mean() - baseline.mean()) / (baseline.mean() + 1)) * 100
        
        m1.metric("Revenue Forecast", f"${projected.mean()/1000:,.1f}K", f"{diff:.1f}%")
        m2.metric("Market Fit", f"{p['retention']}%", "Stable")
        m3.metric("Projected Leads", f"{int(p['leads'])}", f"{int(p['leads']-450)}", delta_color="normal")

        # 3. Render Chart
        st.subheader("Performance Trajectory")
        
        df = pd.DataFrame({
            'Month': months, 'Baseline': baseline, 'Projected': projected,
            'Upper': projected + 400, 'Lower': projected - 400
        })

        base = alt.Chart(df).encode(x=alt.X('Month', sort=months))
        
        # Chart Layers
        line_base = base.mark_line(strokeDash=[5, 5], color='rgba(255,255,255,0.3)').encode(y='Baseline')
        line_proj = base.mark_line(color='#6c5ce7', strokeWidth=4).encode(y='Projected')
        band = base.mark_area(opacity=0.1, color='#6c5ce7').encode(y='Lower', y2='Upper')
        
        # Interactive Tooltip
        hover = alt.selection_single(fields=['Month'], nearest=True, on='mouseover', empty='none', clear='mouseout')
        points = base.mark_circle(color='#6c5ce7', size=80).encode(
            y='Projected',
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=['Month', 'Projected', 'Baseline']
        ).add_selection(hover)
        
        chart = (band + line_base + line_proj + points).properties(height=320).configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)

    # CONTAINER B: Insights
    with st.container(border=True):
        st.subheader("Analysis Insight")
        if projected.mean() > baseline.mean():
            st.success(f"**Recommended Insight:** This configuration suggests a healthy surplus. A budget of {p['budget']}% is well-supported.")
        else:
            st.error(f"**Strict Observation:** These parameters lead to a deficit. Check your lead volume or unit price.")

# --- RIGHT COLUMN: SIDEBAR CONTROLS ---
with col_sidebar:
    with st.container(border=True):
        st.title("Parameters")
        
        # Tabs for organization
        tab_money, tab_growth = st.tabs(["Finance", "Strategy"])
        
        # Note: We use st.session_state.ui_state for 'value' so the AI can update them
        with tab_money:
            st.markdown("####")
            st.slider("Budget Delta", -50, 50, value=st.session_state.ui_state["budget"], key="slider_budget", format="%d%%")
            st.slider("Rate Sensitivity", 0, 500, value=st.session_state.ui_state["interest"], key="slider_interest", format="%d bps")
            st.slider("Market Rate", 0.0, 10.0, value=st.session_state.ui_state["market"], key="slider_market", format="%.1f%%")
            
        with tab_growth:
            st.markdown("####")
            st.slider("Unit Price", 10, 200, value=st.session_state.ui_state["price"], key="slider_price", format="$%d")
            st.slider("Retention Rate", 50, 100, value=st.session_state.ui_state["retention"], key="slider_retention", format="%d%%")
            st.slider("Lead Volume", 0, 1000, value=st.session_state.ui_state["leads"], key="slider_leads")

        st.divider()

        # AI Section
        st.markdown("**Simulation Builder**")
        st.text_area("Describe a situation...", key="user_query", height=80, label_visibility="collapsed")
        st.button("✨ Adjust Sliders", use_container_width=True, on_click=apply_ai_scenario)
        
        if st.session_state.ai_note:
            st.caption(st.session_state.ai_note)

        st.markdown("<br>", unsafe_allow_html=True)
        # Primary Action Button
        st.button("▶ Run Simulation", type="primary", use_container_width=True, on_click=run_simulation)