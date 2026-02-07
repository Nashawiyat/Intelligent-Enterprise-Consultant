import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import random
from theme import get_colors

# ==============================================================================
# 1. THEME COLOURS (from shared palette)
# ==============================================================================
_c = get_colors(st.session_state.dark_mode)
BG           = _c["BG"]
BG2          = _c["BG2"]
CARD         = _c["CARD"]
CARD_INNER   = _c["CARD_INNER"]
BORDER       = _c["BORDER"]
BORDER_STRONG = _c["BORDER_STRONG"]
TEXT         = _c["TEXT"]
TEXT2        = _c["TEXT2"]
ACCENT       = _c["ACCENT"]
ACCENT_BG    = _c["ACCENT_BG"]
HOVER_BG     = _c["HOVER_BG"]
TOGGLE_BG    = _c["TOGGLE_BG"]
TOGGLE_CHECKED = _c["TOGGLE_CHECKED"]
PANEL_SHADOW = _c["PANEL_SHADOW"]

# Derived colours for glass effect (adapts to theme)
if st.session_state.dark_mode:
    GLASS_BG     = "rgba(30, 33, 48, 0.4)"
    GLASS_BORDER = "rgba(255, 255, 255, 0.1)"
    METRIC_BG    = "rgba(255, 255, 255, 0.05)"
    METRIC_BORDER = "rgba(255, 255, 255, 0.05)"
    CHART_LINE   = "#6c5ce7"
    CHART_BASE   = "rgba(255,255,255,0.3)"
    CHART_BAND   = "#6c5ce7"
    TAB_ACTIVE_BG = CARD_INNER
    SLIDER_TRACK = "#4a4a60"
    DIVIDER_CLR  = "rgba(255,255,255,0.1)"
else:
    GLASS_BG     = "rgba(255, 255, 255, 0.7)"
    GLASS_BORDER = "rgba(0, 0, 0, 0.1)"
    METRIC_BG    = "rgba(0, 0, 0, 0.03)"
    METRIC_BORDER = "rgba(0, 0, 0, 0.06)"
    CHART_LINE   = "#5b4cc4"
    CHART_BASE   = "rgba(0,0,0,0.2)"
    CHART_BAND   = "#5b4cc4"
    TAB_ACTIVE_BG = "#ffffff"
    SLIDER_TRACK = "#c0c5cc"
    DIVIDER_CLR  = "rgba(0,0,0,0.1)"

# ==============================================================================
# 2. CONFIG & STYLE
# ==============================================================================
st.markdown(f"""
<style>
    /* Main Background – override shared theme */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main, .block-container,
    [data-testid="stAppViewBlockContainer"],
    section[data-testid="stMain"],
    div[data-testid="stAppViewContainer"] > section,
    div[data-testid="stAppViewContainer"] > section > div,
    .stApp {{ background-color: {BG} !important; color: {TEXT} !important; }}

    /* === PANEL BORDERS — thick borders for visual separation === */
    [data-testid="stVerticalBlock"].st-key-sim_graph_panel,
    [data-testid="stVerticalBlock"].st-key-sim_analysis_panel,
    [data-testid="stVerticalBlock"].st-key-sim_params_panel {{
        border: 3px solid {BORDER_STRONG} !important;
        border-radius: 16px !important;
        background: {CARD} !important;
        box-shadow: {PANEL_SHADOW} !important;
        padding: 0.8rem !important;
    }}

    /* GLASS CARD STYLING (fallback for other bordered containers) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {GLASS_BORDER} !important;
        background: {GLASS_BG} !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        padding: 20px !important;
    }}

    /* COMPACT METRIC CARDS */
    div[data-testid="stMetric"], .stMetric {{
        background: {METRIC_BG};
        padding: 8px 15px !important;
        border-radius: 10px;
        border: 1px solid {METRIC_BORDER};
    }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; color: {TEXT2} !important; }}
    div[data-testid="stMetricValue"] {{ font-size: 1.5rem !important; color: {TEXT} !important; }}
    div[data-testid="stMetricDelta"] {{ color: {TEXT2} !important; }}

    /* ALL text forced to theme colour (scoped to main content, not sidebar) */
    [data-testid="stMain"] [data-testid="stMarkdown"],
    [data-testid="stMain"] [data-testid="stText"],
    [data-testid="stMain"] p,
    [data-testid="stMain"] span,
    [data-testid="stMain"] label,
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] h5,
    [data-testid="stMain"] h6,
    [data-testid="stMain"] li,
    [data-testid="stMain"] td,
    [data-testid="stMain"] th {{
        color: {TEXT} !important;
    }}

    /* Top bar */
    .sim-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.3rem 0;
        margin-bottom: 0.5rem;
    }}
    .sim-topbar-brand {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {ACCENT};
    }}

    /* Tabs */
    [data-testid="stTabs"] button {{
        color: {TEXT2} !important;
        background: transparent !important;
        border: none !important;
        font-weight: 500 !important;
    }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        color: {ACCENT} !important;
        border-bottom: 2px solid {ACCENT} !important;
        background: {TAB_ACTIVE_BG} !important;
        border-radius: 8px 8px 0 0 !important;
    }}

    /* Slider label and value text */
    [data-testid="stSlider"] label,
    [data-testid="stSlider"] [data-testid="stWidgetLabel"] p {{
        color: {TEXT} !important;
    }}
    [data-testid="stSlider"] [data-testid="stThumbValue"] {{
        color: {TEXT} !important;
    }}

    /* Text area, inputs */
    [data-testid="stTextArea"] textarea {{
        background: {CARD_INNER} !important;
        color: {TEXT} !important;
        border-color: {BORDER} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stTextArea"] textarea::placeholder {{
        color: {TEXT2} !important;
    }}
    [data-testid="stTextArea"] label p {{
        color: {TEXT} !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {CARD} !important;
        color: {TEXT2} !important;
        border: 1.5px solid {BORDER} !important;
        border-radius: 10px !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 0.8rem !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }}
    .stButton > button:hover {{
        background: {HOVER_BG} !important;
        border-color: {ACCENT} !important;
        color: {ACCENT} !important;
    }}

    /* Primary button */
    button[data-testid="stBaseButton-primary"] {{
        background: {ACCENT} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }}
    button[data-testid="stBaseButton-primary"]:hover {{
        opacity: 0.85 !important;
    }}

    /* Dividers */
    hr {{
        border-color: {DIVIDER_CLR} !important;
    }}

    /* Success / Error boxes */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
    }}

    /* Caption text */
    .stCaption, [data-testid="stCaption"] {{
        color: {TEXT2} !important;
    }}

    /* Title and subheader */
    .stTitle, [data-testid="stTitle"] {{
        color: {TEXT} !important;
    }}
    .stSubheader {{
        color: {TEXT} !important;
    }}
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
# 4. TOP BAR – Title + Dark Mode toggle (same as home page)
# ==============================================================================
top_left, top_spacer, top_right = st.columns([3, 5, 2])
with top_left:
    st.markdown(f'<div class="sim-topbar-brand">🔬 Simulation Sandbox</div>', unsafe_allow_html=True)
with top_right:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ==============================================================================
# 5. MAIN LAYOUT
# ==============================================================================
col_main, col_sidebar = st.columns([3, 1], gap="large")

# --- LEFT COLUMN: MAIN VISUALIZATION ---
with col_main:
    
    # CONTAINER A: Header & Graph
    with st.container(border=True, key="sim_graph_panel"):
        st.markdown("") 

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
        line_base = base.mark_line(strokeDash=[5, 5], color=CHART_BASE).encode(y='Baseline')
        line_proj = base.mark_line(color=CHART_LINE, strokeWidth=4).encode(y='Projected')
        band = base.mark_area(opacity=0.1, color=CHART_BAND).encode(y='Lower', y2='Upper')
        
        # Interactive Tooltip
        hover = alt.selection_single(fields=['Month'], nearest=True, on='mouseover', empty='none', clear='mouseout')
        points = base.mark_circle(color=CHART_LINE, size=80).encode(
            y='Projected',
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=['Month', 'Projected', 'Baseline']
        ).add_selection(hover)
        
        chart = (band + line_base + line_proj + points).properties(height=320).configure_view(
            strokeWidth=0
        ).configure(
            background='transparent'
        ).configure_axis(
            labelColor=TEXT,
            titleColor=TEXT,
            gridColor=BORDER
        )
        st.altair_chart(chart, use_container_width=True)

    # CONTAINER B: Insights
    with st.container(border=True, key="sim_analysis_panel"):
        st.subheader("Analysis Insight")
        if projected.mean() > baseline.mean():
            st.success(f"**Recommended Insight:** This configuration suggests a healthy surplus. A budget of {p['budget']}% is well-supported.")
        else:
            st.error(f"**Strict Observation:** These parameters lead to a deficit. Check your lead volume or unit price.")

# --- RIGHT COLUMN: SIDEBAR CONTROLS ---
with col_sidebar:
    with st.container(border=True, key="sim_params_panel"):
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