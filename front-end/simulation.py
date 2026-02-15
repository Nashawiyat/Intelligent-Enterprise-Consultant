import streamlit as st
import plotly.graph_objects as go
import requests
import json
from theme import get_colors
from auth_utils import get_current_user, get_user_domain, get_user_role_context

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
    /* Hide 'Press Enter to submit form' helper text */
    div[data-testid="InputInstructions"] {{
        display: none !important;
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. BACKEND CONFIG + CONSTANTS
# ==============================================================================
try:
    BACKEND_BASE_URL = st.secrets["BACKEND_URL"]
except Exception:
    BACKEND_BASE_URL = "http://localhost:8000"
SIMULATION_ENDPOINT = f"{BACKEND_BASE_URL}/simulation"

# Parameters per domain (aligned with backend helper_classes.py)
DOMAIN_PARAMS = {
    "Sales": {
        "price":                {"label": "Unit Price ($)",          "min": 10,   "max": 500,  "default": 85,   "format": "$%d"},
        "discount_quantity":    {"label": "Discount Qty Threshold",  "min": 0,    "max": 1000, "default": 100,  "format": "%d units"},
        "client_retention_rate":{"label": "Client Retention Rate",   "min": 0.0,  "max": 100.0,"default": 92.0, "format": "%.1f%%"},
        "lead_inflow_volume":   {"label": "Lead Inflow Volume",      "min": 0,    "max": 2000, "default": 450,  "format": "%d"},
    },
    "Operations": {
        "api_latency":  {"label": "API Latency (ms)",   "min": 0,    "max": 2000, "default": 120, "format": "%d ms"},
        "failure_rate": {"label": "Failure Rate (%)",   "min": 0.0,  "max": 100.0,"default": 2.5, "format": "%.1f%%"},
        "throughput":   {"label": "Throughput (req/s)",  "min": 0,    "max": 10000,"default": 500, "format": "%d req/s"},
    },
    "HR": {
        "salary_budget":   {"label": "Salary Budget ($K)", "min": 0,   "max": 10000, "default": 2000, "format": "$%dK"},
        "headcount_change": {"label": "Headcount Change",  "min": -50, "max": 100,   "default": 0,    "format": "%d"},
        "attrition_rate":  {"label": "Attrition Rate (%)", "min": 0.0, "max": 50.0,  "default": 12.0, "format": "%.1f%%"},
    },
    "Accounting": {
        "revenue_target":  {"label": "Revenue Target ($K)",  "min": 0,    "max": 50000, "default": 5000,  "format": "$%dK"},
        "cost_reduction":  {"label": "Cost Reduction (%)",   "min": 0.0,  "max": 50.0,  "default": 5.0,   "format": "%.1f%%"},
        "tax_rate":        {"label": "Effective Tax Rate (%)", "min": 0.0, "max": 50.0,  "default": 21.0,  "format": "%.1f%%"},
    },
    "CRM": {
        "nps_target":      {"label": "NPS Target",           "min": -100, "max": 100,  "default": 45,   "format": "%d"},
        "ticket_volume":   {"label": "Support Tickets/day",  "min": 0,    "max": 1000, "default": 150,  "format": "%d"},
        "response_time":   {"label": "Avg Response Time (h)","min": 0.0,  "max": 72.0, "default": 4.0,  "format": "%.1fh"},
    },
}

# ==============================================================================
# 4. HELPER FUNCTIONS
# ==============================================================================
def init_state():
    """Initializes session state for simulation."""
    if "sim_domain" not in st.session_state:
        st.session_state.sim_domain = get_user_domain()
    if "sim_role" not in st.session_state:
        st.session_state.sim_role = get_user_role_context()
    if "sim_result" not in st.session_state:
        st.session_state.sim_result = None
    if "sim_error" not in st.session_state:
        st.session_state.sim_error = None
    if "sim_loading" not in st.session_state:
        st.session_state.sim_loading = False
    if "sim_prompt" not in st.session_state:
        st.session_state.sim_prompt = ""

def run_simulation_backend():
    """Send simulation request to backend POST /simulation."""
    domain = st.session_state.sim_domain
    role = st.session_state.sim_role
    params = DOMAIN_PARAMS.get(domain, {})

    # Build payload: required fields + domain-specific slider values
    payload = {
        "domain": domain.lower(),
        "role_context": role,
    }

    # Add prompt if user provided one
    prompt_text = st.session_state.get("sim_prompt_input", "").strip()
    if prompt_text:
        payload["prompt"] = prompt_text

    # Add domain-specific parameters from sliders
    for param_key, config in params.items():
        slider_key = f"sim_slider_{param_key}"
        if slider_key in st.session_state:
            payload[param_key] = st.session_state[slider_key]

    st.session_state.sim_loading = True
    st.session_state.sim_error = None

    # Auth header for protected endpoint
    token = st.session_state.get("auth_token")
    headers = {"session-token": token} if token else {}

    try:
        resp = requests.post(SIMULATION_ENDPOINT, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        st.session_state.sim_result = data
        st.toast("Simulation complete!", icon="✅")
    except requests.exceptions.ConnectionError:
        st.session_state.sim_error = "Backend not reachable. Start the backend server."
        st.session_state.sim_result = None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        if status == 429:
            st.session_state.sim_error = "⏳ AI rate limit reached. Please wait a minute and try again."
        else:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            st.session_state.sim_error = f"Simulation error ({status}): {detail}"
        st.session_state.sim_result = None
    except Exception as e:
        st.session_state.sim_error = f"Simulation error: {e}"
        st.session_state.sim_result = None
    finally:
        st.session_state.sim_loading = False


def render_sim_plotly(visuals: dict):
    """Render Plotly chart from backend visuals data."""
    plotly_data = visuals.get("plotly_data", {})
    fig = go.Figure()
    for trace in plotly_data.get("data", []):
        t = trace.get("type", "scatter")
        tc = {k: v for k, v in trace.items() if k != "type"}
        if t in ("scatter", "line"):
            fig.add_trace(go.Scatter(**tc))
        elif t == "bar":
            fig.add_trace(go.Bar(**tc))
        elif t == "pie":
            fig.add_trace(go.Pie(**tc))
        else:
            fig.add_trace(go.Scatter(**tc))

    layout = plotly_data.get("layout", {})
    PLOTLY_BG = _c.get("PLOTLY_BG", CARD_INNER)
    CHART_TEXT_CLR = _c.get("CHART_TEXT", TEXT)
    CHART_GRID_CLR = _c.get("CHART_GRID", BORDER)
    layout.update({
        "margin": dict(l=40, r=40, t=40, b=40),
        "height": 350,
        "paper_bgcolor": PLOTLY_BG,
        "plot_bgcolor": PLOTLY_BG,
        "font": {"family": "Inter", "size": 12, "color": CHART_TEXT_CLR},
        "title_font": {"size": 14, "color": CHART_TEXT_CLR},
        "legend": {"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center", "font": {"size": 11, "color": CHART_TEXT_CLR}},
    })
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID_CLR, color=CHART_TEXT_CLR)
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID_CLR, color=CHART_TEXT_CLR)
    st.plotly_chart(fig, use_container_width=True, key="sim_chart")


# Initialize state
init_state()

# ==============================================================================
# 5. TOP BAR – Title + user info + Dark Mode toggle
# ==============================================================================
# Fix domain/role from user profile on every render
st.session_state.sim_domain = get_user_domain()
st.session_state.sim_role = get_user_role_context()

top_brand, _, top_toggle = st.columns([6, 3, 2])
with top_brand:
    current_user = get_current_user()
    dept_label = current_user.get("department", "") if current_user else ""
    role_label = st.session_state.sim_role
    st.markdown(
        f'<div class="sim-topbar-brand">🔬 Simulation Sandbox'
        f'<span style="font-size:0.95rem;color:{TEXT2};font-weight:400;opacity:0.85;margin-left:0.4rem;">'
        f' · {dept_label} · {role_label}</span></div>',
        unsafe_allow_html=True,
    )
with top_toggle:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ==============================================================================
# 6. MAIN LAYOUT
# ==============================================================================
col_main, col_sidebar = st.columns([3, 1], gap="large")

current_domain = st.session_state.sim_domain
domain_params = DOMAIN_PARAMS.get(current_domain, {})

# --- LEFT COLUMN: MAIN VISUALIZATION ---
with col_main:
    # CONTAINER A: Results area
    with st.container(border=True, key="sim_graph_panel"):
        result = st.session_state.sim_result

        if st.session_state.sim_loading:
            st.info("Running simulation… This may take a moment.")
        elif st.session_state.sim_error:
            st.error(st.session_state.sim_error)
        elif result is None:
            st.info(f"Configure **{current_domain}** parameters and click **▶ Run Simulation** to see results.")
        else:
            # Extract content from backend response
            content = result.get("content", {})
            meta = result.get("meta", {})
            visuals = result.get("visuals", {})

            # Metrics row
            headline = content.get("headline", "Simulation Result")
            st.subheader(headline)

            m1, m2, m3 = st.columns(3)
            conf = meta.get("confidence_score", 0)
            urgency = meta.get("urgency_score", 0)
            m1.metric("Confidence", f"{int(conf * 100 if conf <= 1 else conf)}%")
            m2.metric("Urgency", f"{int(urgency * 100 if urgency <= 1 else urgency)}%")
            m3.metric("Domain", current_domain)

            # Chart
            if visuals and visuals.get("plotly_data"):
                render_sim_plotly(visuals)

            # Summary
            summary = content.get("summary", "")
            if summary:
                st.markdown(f"**Summary:** {summary}")

            # Detailed reasoning
            detailed = content.get("reasoning_detailed", "")
            if detailed:
                with st.expander("📖 Detailed Analysis", expanded=False):
                    st.markdown(detailed)

    # CONTAINER B: Recommendations
    with st.container(border=True, key="sim_analysis_panel"):
        st.subheader("Recommendations")
        if result and result.get("content", {}).get("recommendations"):
            recs = result["content"]["recommendations"]
            for i, rec in enumerate(recs):
                st.markdown(f"**{i+1}. {rec.get('action', 'Action')}**")
                st.markdown(f"> {rec.get('detail', '')}")
                impact = rec.get("expected_impact", "")
                if impact:
                    st.caption(f"Expected impact: {impact}")
        else:
            st.caption("Run a simulation to see recommendations.")

        # Reasoning chain
        if result and result.get("reasoning_chain"):
            with st.expander("💡 Reasoning Chain", expanded=False):
                for step in result["reasoning_chain"]:
                    st.markdown(f"**{step['step']}.** *{step['agent']}* – {step['thought']}")

# --- RIGHT COLUMN: PARAMETER CONTROLS ---
with col_sidebar:
    with st.container(border=True, key="sim_params_panel"):
        st.markdown(f"### {current_domain} Parameters")

        # Dynamic sliders based on selected domain
        for param_key, config in domain_params.items():
            slider_key = f"sim_slider_{param_key}"
            val = config["default"]
            # Use float slider if default or min/max are floats
            if isinstance(val, float) or isinstance(config["min"], float):
                st.slider(
                    config["label"],
                    min_value=float(config["min"]),
                    max_value=float(config["max"]),
                    value=float(val),
                    key=slider_key,
                    format=config["format"],
                )
            else:
                st.slider(
                    config["label"],
                    min_value=int(config["min"]),
                    max_value=int(config["max"]),
                    value=int(val),
                    key=slider_key,
                    format=config["format"],
                )

        st.divider()

        # Scenario prompt
        st.markdown("**Scenario Prompt** *(optional)*")
        st.text_area(
            "Describe a what-if scenario…",
            key="sim_prompt_input",
            height=80,
            label_visibility="collapsed",
            placeholder="e.g. What if we increase price by 20% and latency spikes to 500ms?",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        # Primary Action Button
        st.button("▶ Run Simulation", type="primary", use_container_width=True, on_click=run_simulation_backend)