import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import random

# ==============================================================================
# 1. CONFIG & THEME LOGIC
# ==============================================================================
st.set_page_config(layout="wide", page_title="The Sandbox")

# --- THEME MANAGEMENT ---
def init_theme():
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "Dark" # Default

# Initialize Theme State
init_theme()

# --- CSS GENERATOR ---
# We use Python variables to swap colors based on the toggle state
if st.session_state.theme_mode == "Dark":
    # DARK MODE PALETTE (Your original look)
    bg_color = "#0e1117"
    card_bg = "rgba(30, 33, 48, 0.4)"
    border_color = "rgba(255, 255, 255, 0.1)"
    text_color = "white"
    metric_bg = "rgba(255, 255, 255, 0.05)"
    chart_color = "#6c5ce7" # Purple
    grid_color = "#333"
else:
    # LIGHT MODE PALETTE (Clean & Professional)
    bg_color = "#f0f2f6"
    card_bg = "rgba(255, 255, 255, 0.7)" # White glass
    border_color = "rgba(0, 0, 0, 0.1)"
    text_color = "#31333F"
    metric_bg = "rgba(0, 0, 0, 0.03)"
    chart_color = "#2563eb" # Blue
    grid_color = "#e5e7eb"

# INJECT DYNAMIC CSS
st.markdown(f"""
<style>
    /* Main Background */
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    
    /* GLASS CARD STYLING */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {border_color} !important;
        background: {card_bg} !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); /* Soft shadow for light mode depth */
    }}
    
    /* METRIC CARDS */
    div[data-testid="stMetric"], .stMetric {{ 
        background: {metric_bg}; 
        padding: 8px 15px !important; 
        border-radius: 10px; 
        border: 1px solid {border_color};
        color: {text_color} !important;
    }}
    
    /* Text Color Overrides for Light Mode visibility */
    h1, h2, h3, p, span, div {{ color: {text_color}; }}
    
    /* Metric Label/Value Sizes */
    div[data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; opacity: 0.8; }}
    div[data-testid="stMetricValue"] {{ font-size: 1.5rem !important; }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. HELPER FUNCTIONS (LOGIC LAYER)
# ==============================================================================

def init_state():
    """Initializes the session state variables if they don't exist yet."""
    defaults = {
        "budget": 10, "interest": 250, "market": 2.5,  # Finance Tab
        "price": 85, "retention": 92, "leads": 450     # Strategy Tab
    }
    
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = defaults.copy()
        
    if "sim_params" not in st.session_state:
        st.session_state.sim_params = defaults.copy()
    
    if "ai_note" not in st.session_state:
        st.session_state.ai_note = None

def calculate_projections(params):
    """Core math engine for the chart."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    x = np.arange(len(months))
    
    impact = (params["budget"] * 12) + (params["leads"] * 0.3) - (params["interest"] * 1.2)
    baseline = 4000 + 400 * np.sin(x * 0.8)
    projected = baseline + impact
    
    return projected, baseline, months

def toggle_theme():
    """Callback to switch the theme state."""
    if st.session_state.theme_mode == "Dark":
        st.session_state.theme_mode = "Light"
    else:
        st.session_state.theme_mode = "Dark"

# ==============================================================================
# 3. CALLBACKS
# ==============================================================================

def run_simulation():
    """Updates the graph simulation parameters."""
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
    """Updates UI sliders based on text input."""
    query = st.session_state.get("user_query", "").lower()
    if not query:
        st.toast("Type a scenario first.", icon="✍️")
        return

    if "growth" in query or "expand" in query:
        st.session_state.ui_state.update({"budget": 30, "leads": 750})
        st.session_state.ai_note = "Prepared growth settings. Review the sliders and hit 'Run'."
    elif "risk" in query or "crash" in query:
        st.session_state.ui_state.update({"budget": -15, "interest": 400, "retention": 70})
        st.session_state.ai_note = "Defensive posture ready. Review sliders and hit 'Run'."
    else:
        st.session_state.ui_state.update({"budget": random.randint(-20, 20), "leads": random.randint(200, 800)})
        st.session_state.ai_note = "Sliders tweaked for your scenario. Ready for simulation."

init_state()

# ==============================================================================
# 4. MAIN LAYOUT
# ==============================================================================
col_main, col_sidebar = st.columns([3, 1], gap="large")

# --- RIGHT COLUMN: SIDEBAR CONTROLS ---
with col_sidebar:
    # 1. THEME TOGGLE (Placed outside the container for easy access)
    c1, c2 = st.columns([1,3])
    with c1:
        # We use a button-like toggle or just a simple toggle widget
        st.toggle("☀️ Mode", value=(st.session_state.theme_mode == "Light"), on_change=toggle_theme, key="theme_toggle")
    
    # 2. MAIN CONTROL CARD
    with st.container(border=True):
        st.title("Parameters")
        
        tab_money, tab_growth = st.tabs(["Finance", "Strategy"])
        
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

        st.markdown("**Simulation Builder**")
        st.text_area("Describe a situation...", key="user_query", height=80, label_visibility="collapsed")
        st.button("✨ Adjust Sliders", use_container_width=True, on_click=apply_ai_scenario)
        
        if st.session_state.ai_note:
            st.caption(st.session_state.ai_note)

        st.markdown("<br>", unsafe_allow_html=True)
        st.button("▶ Run Simulation", type="primary", use_container_width=True, on_click=run_simulation)

# --- LEFT COLUMN: VISUALIZATION ---
with col_main:
    
    # CONTAINER A: Header & Graph
    with st.container(border=True):
        st.title("Simulation Sandbox")
        st.markdown("---") 

        p = st.session_state.sim_params
        projected, baseline, months = calculate_projections(p)
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        diff = ((projected.mean() - baseline.mean()) / (baseline.mean() + 1)) * 100
        
        m1.metric("Revenue Forecast", f"${projected.mean()/1000:,.1f}K", f"{diff:.1f}%")
        m2.metric("Market Fit", f"{p['retention']}%", "Stable")
        m3.metric("Projected Leads", f"{int(p['leads'])}", f"{int(p['leads']-450)}", delta_color="normal")

        # Chart
        st.subheader("Performance Trajectory")
        
        df = pd.DataFrame({
            'Month': months, 'Baseline': baseline, 'Projected': projected,
            'Upper': projected + 400, 'Lower': projected - 400
        })

        base = alt.Chart(df).encode(x=alt.X('Month', sort=months))
        
        # Chart Layers with Dynamic Color
        line_base = base.mark_line(strokeDash=[5, 5], color='grey').encode(y='Baseline')
        line_proj = base.mark_line(color=chart_color, strokeWidth=4).encode(y='Projected')
        band = base.mark_area(opacity=0.1, color=chart_color).encode(y='Lower', y2='Upper')
        
        hover = alt.selection_single(fields=['Month'], nearest=True, on='mouseover', empty='none', clear='mouseout')
        points = base.mark_circle(color=chart_color, size=80).encode(
            y='Projected',
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=['Month', 'Projected', 'Baseline']
        ).add_selection(hover)
        
        # We add .configure_axis() to fix grid visibility in light mode
        chart = (band + line_base + line_proj + points).properties(height=320).configure_view(strokeWidth=0).configure_axis(
            gridColor=border_color,
            domainColor=border_color,
            labelColor=text_color,
            titleColor=text_color
        )
        st.altair_chart(chart, use_container_width=True)

    # CONTAINER B: Insights
    with st.container(border=True):
        st.subheader("Analysis Insight")
        if projected.mean() > baseline.mean():
            st.success(f"**Recommended Insight:** This configuration suggests a healthy surplus. A budget of {p['budget']}% is well-supported.")
        else:
            st.error(f"**Strict Observation:** These parameters lead to a deficit. Check your lead volume or unit price.")