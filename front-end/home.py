"""
ICA – Home Page
===============
Dashboard with insight cards + chatbot panel.
This file is loaded by app.py via st.navigation().
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
import random
from datetime import datetime
from theme import get_colors

# ──────────────────────────────────────────────
# Backend config
# ──────────────────────────────────────────────
try:
    BACKEND_BASE_URL = st.secrets["BACKEND_URL"]
except Exception:
    BACKEND_BASE_URL = "http://localhost:8000"
INSIGHTS_ENDPOINT = f"{BACKEND_BASE_URL}/api/insights"
CHAT_ENDPOINT = f"{BACKEND_BASE_URL}/api/chat"
USE_BACKEND = False  # flip to True when FastAPI is live

# ──────────────────────────────────────────────
# Theme colours (for Python-level usage: Plotly charts, inline HTML)
# ──────────────────────────────────────────────
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
CHAT_ASSIST_BG = _c["CHAT_ASSIST_BG"]
CHAT_USER_BG = _c["CHAT_USER_BG"]
INPUT_BG     = _c["INPUT_BG"]
HOVER_BG     = _c["HOVER_BG"]
PLOTLY_BG    = _c["PLOTLY_BG"]
CHART_TEXT   = _c["CHART_TEXT"]
CHART_GRID   = _c["CHART_GRID"]
PANEL_SHADOW = _c["PANEL_SHADOW"]

# ──────────────────────────────────────────────
# Page-specific CSS (content styling for home page)
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
/* === Global background === */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container,
[data-testid="stAppViewBlockContainer"],
section[data-testid="stMain"],
div[data-testid="stAppViewContainer"] > section,
div[data-testid="stAppViewContainer"] > section > div {{
    background-color: {BG} !important;
    color: {TEXT} !important;
}}

/* === Top bar === */
.topbar-inline {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 0;
    margin-bottom: 0.5rem;
}}
.topbar-brand {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {ACCENT};
}}

/* === PANEL BORDERS === */
[data-testid="stVerticalBlock"].st-key-insights_panel,
[data-testid="stVerticalBlock"].st-key-chat_panel {{
    border: 3px solid {BORDER_STRONG} !important;
    border-radius: 16px !important;
    background: {CARD} !important;
    box-shadow: {PANEL_SHADOW} !important;
    padding: 0.5rem !important;
}}
/* Scroll container – no visible border */
.st-key-insights_panel [data-testid="stVerticalBlock"][style*="overflow"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* === Insight card borders === */
[data-testid="stVerticalBlock"][class*="st-key-card_"] {{
    border: 2px solid {BORDER_STRONG} !important;
    border-radius: 14px !important;
    background: {CARD_INNER} !important;
    padding: 0.6rem !important;
}}
/* Remove borders from elements INSIDE cards */
[data-testid="stVerticalBlock"][class*="st-key-card_"] [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlock"][class*="st-key-card_"] [data-testid="stHorizontalBlock"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* === Insight card classes === */
.insight-card {{
    background: {CARD_INNER};
    border: 1.5px solid {BORDER};
    border-radius: 14px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.3rem;
    transition: border-color 0.15s ease;
}}
.insight-card:hover {{
    border-color: {ACCENT};
}}
.insight-card h4 {{
    margin: 0 0 0.25rem 0;
    color: {TEXT} !important;
    font-size: 0.88rem;
    font-weight: 600;
}}
.meta-row {{
    display: flex;
    gap: 0.3rem;
    margin-bottom: 0.3rem;
    flex-wrap: wrap;
}}
.meta-tag {{
    background: {ACCENT_BG};
    color: {ACCENT} !important;
    border-radius: 10px;
    padding: 0.1rem 0.45rem;
    font-size: 0.68rem;
    font-weight: 600;
}}
.meta-tag.urgent {{
    background: #fff3e0;
    color: #e65100 !important;
}}
.insight-summary {{
    font-size: 0.78rem;
    color: {TEXT2} !important;
    line-height: 1.4;
    margin-bottom: 0.2rem;
}}

/* === Chat bubbles === */
.chat-bubble {{
    max-width: 88%;
    padding: 0.6rem 0.9rem;
    margin-bottom: 0.5rem;
    border-radius: 14px;
    font-size: 0.82rem;
    line-height: 1.45;
    word-wrap: break-word;
}}
.chat-bubble.user {{
    background: {CHAT_USER_BG};
    color: {TEXT} !important;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}}
.chat-bubble.assistant {{
    background: {CHAT_ASSIST_BG};
    color: {TEXT} !important;
    margin-right: auto;
    border-bottom-left-radius: 4px;
}}
.chat-time {{
    font-size: 0.6rem;
    color: {TEXT2} !important;
    margin-top: 0.1rem;
}}

/* === Panel header === */
.panel-header {{
    font-weight: 700;
    font-size: 1rem;
    color: {ACCENT} !important;
    margin-bottom: 0.3rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {BORDER};
}}

/* === ALL text forced to theme (scoped to main content) === */
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

/* === Expander === */
[data-testid="stExpander"] {{
    background: {CARD_INNER} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] details {{
    background: {CARD_INNER} !important;
}}
[data-testid="stExpander"] summary {{
    color: {ACCENT} !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    background: {CARD_INNER} !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: {CARD_INNER} !important;
}}
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary svg {{
    color: {ACCENT} !important;
    fill: {ACCENT} !important;
}}
[data-testid="stExpander"][open] summary,
[data-testid="stExpander"] details[open] summary {{
    background: {CARD_INNER} !important;
    color: {ACCENT} !important;
}}
[data-testid="stExpander"] [data-testid="stMarkdown"] p {{
    color: {TEXT2} !important;
    font-size: 0.8rem !important;
}}

/* === Buttons === */
.stButton > button {{
    background: {CARD} !important;
    color: {TEXT2} !important;
    border: 1.5px solid {BORDER} !important;
    border-radius: 10px !important;
    font-size: 0.8rem !important;
    padding: 0.3rem 0.8rem !important;
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

/* === Chat input === */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div {{
    background: {INPUT_BG} !important;
    border-radius: 12px !important;
    border-color: {BORDER} !important;
}}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {{
    color: {TEXT} !important;
    background: {INPUT_BG} !important;
    caret-color: {TEXT} !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
    color: {TEXT2} !important;
}}
[data-testid="stChatInput"] button {{
    background: {ACCENT} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 50% !important;
}}

/* === Plotly === */
[data-testid="stPlotlyChart"], .stPlotlyChart {{
    background: {PLOTLY_BG} !important;
    border-radius: 10px !important;
}}

/* === Expander compact === */
[data-testid="stExpander"] {{
    margin-top: 0.1rem !important;
    margin-bottom: 0 !important;
}}
[data-testid="stExpander"] details {{
    padding: 0.2rem 0.5rem !important;
}}
[data-testid="stExpander"] summary span {{
    font-size: 0.78rem !important;
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "active_insights" not in st.session_state:
    st.session_state.active_insights = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ──────────────────────────────────────────────
# Dummy data (replaced by backend)
# ──────────────────────────────────────────────
DUMMY_INSIGHTS = [
    {
        "insight_id": "INC-2026-0042",
        "timestamp": "2026-02-07T12:00:00Z",
        "meta": {"confidence_score": 0.88, "urgency_score": 0.92, "domain": "Finance/Ops", "role_context": "CEO"},
        "content": {
            "headline": "5% Margin Compression – APAC",
            "summary": "Revenue in APAC trending down. Checkout API latency spike is the primary driver.",
            "recommendations": [
                {"action": "Ops Patch", "detail": "Scale checkout in ap-southeast-1.", "expected_impact": "Recover ~$12K/day."},
                {"action": "Loyalty Campaign", "detail": "5% discount for affected users.", "expected_impact": "Reduce churn ~15%."}
            ]
        },
        "reasoning_chain": [
            {"step": 1, "agent": "SQL Specialist", "thought": "Detected 5% revenue dip in APAC."},
            {"step": 2, "agent": "Ops Monitor", "thought": "Found latency spike in checkout API."},
            {"step": 3, "agent": "Market Researcher", "thought": "Competitor X launched fast-checkout."},
            {"step": 4, "agent": "Orchestrator", "thought": "Latency + competitor = compounded churn."}
        ],
        "visuals": {
            "chart_type": "line",
            "plotly_data": {
                "data": [
                    {"x": ["08:00", "10:00", "12:00", "14:00"], "y": [100, 95, 90, 85], "name": "Revenue ($K)", "type": "scatter"},
                    {"x": ["08:00", "10:00", "12:00", "14:00"], "y": [50, 80, 250, 310], "name": "Latency (ms)", "type": "scatter", "yaxis": "y2"}
                ],
                "layout": {"title": "Revenue vs Latency", "yaxis2": {"overlaying": "y", "side": "right"}}
            }
        }
    },
    {
        "insight_id": "INC-2026-0043",
        "timestamp": "2026-02-07T11:30:00Z",
        "meta": {"confidence_score": 0.91, "urgency_score": 0.65, "domain": "Marketing", "role_context": "CMO"},
        "content": {
            "headline": "Email Campaign ROI +22% – EU",
            "summary": "EU email campaign outperformed projections by 22%. Open rates and CTR at all-time highs.",
            "recommendations": [
                {"action": "Scale Campaign", "detail": "Extend to APAC with localised content.", "expected_impact": "+$8K weekly."},
                {"action": "A/B Test", "detail": "Test emoji vs plain subject lines.", "expected_impact": "+5% open rate."}
            ]
        },
        "reasoning_chain": [
            {"step": 1, "agent": "CRM Analyst", "thought": "EU open rate at 38%."},
            {"step": 2, "agent": "Revenue Tracker", "thought": "Correlated opens with conversions."}
        ],
        "visuals": {
            "chart_type": "bar",
            "plotly_data": {
                "data": [
                    {"x": ["Wk1", "Wk2", "Wk3", "Wk4"], "y": [12, 18, 25, 31], "name": "Conversions", "type": "bar", "marker": {"color": "#4caf50"}},
                    {"x": ["Wk1", "Wk2", "Wk3", "Wk4"], "y": [8, 10, 14, 16], "name": "Unsubs", "type": "bar", "marker": {"color": "#ef5350"}}
                ],
                "layout": {"title": "Email Performance", "barmode": "group"}
            }
        }
    },
    {
        "insight_id": "INC-2026-0044",
        "timestamp": "2026-02-07T10:45:00Z",
        "meta": {"confidence_score": 0.79, "urgency_score": 0.85, "domain": "Supply Chain", "role_context": "COO"},
        "content": {
            "headline": "Inventory Risk – SKU #4421",
            "summary": "Stock depletes in 6 days. Supplier lead time is 10 days. Demand expected to surge 40%.",
            "recommendations": [
                {"action": "Emergency Reorder", "detail": "Supplier B can expedite in 3 days.", "expected_impact": "Avoid $45K lost sales."},
                {"action": "Substitute SKU", "detail": "Offer #4422 at 5% discount.", "expected_impact": "Retain ~60% demand."}
            ]
        },
        "reasoning_chain": [
            {"step": 1, "agent": "Inventory", "thought": "6 days stock remaining."},
            {"step": 2, "agent": "Demand Forecast", "thought": "40% demand spike predicted."},
            {"step": 3, "agent": "Procurement", "thought": "Supplier B: 3-day expedite."}
        ],
        "visuals": {
            "chart_type": "line",
            "plotly_data": {
                "data": [
                    {"x": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"], "y": [500, 420, 340, 260, 180, 100, 20], "name": "Stock", "type": "scatter", "fill": "tozeroy", "fillcolor": "rgba(76,175,80,0.15)", "line": {"color": "#4caf50"}},
                    {"x": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"], "y": [80, 85, 90, 100, 110, 120, 130], "name": "Demand", "type": "scatter", "line": {"color": "#ff9800", "dash": "dash"}}
                ],
                "layout": {"title": "Stock Depletion – SKU #4421"}
            }
        }
    },
    {
        "insight_id": "INC-2026-0045",
        "timestamp": "2026-02-07T09:15:00Z",
        "meta": {"confidence_score": 0.94, "urgency_score": 0.45, "domain": "HR/People", "role_context": "CHRO"},
        "content": {
            "headline": "Employee Satisfaction +8%",
            "summary": "Flexible work policy improved eNPS by 8 points. Attrition intent dropped from 18% to 11%.",
            "recommendations": [
                {"action": "Expand Policy", "detail": "Extend to sales and support teams.", "expected_impact": "+5% eNPS company-wide."},
                {"action": "Case Study", "detail": "Share results internally.", "expected_impact": "Boost employer brand."}
            ]
        },
        "reasoning_chain": [
            {"step": 1, "agent": "HR Analyst", "thought": "eNPS improved 8 points."},
            {"step": 2, "agent": "Stats Engine", "thought": "Confirmed at p<0.01."}
        ],
        "visuals": {
            "chart_type": "bar",
            "plotly_data": {
                "data": [{"x": ["Before", "After"], "y": [62, 70], "name": "eNPS", "type": "bar", "marker": {"color": ["#90caf9", "#4caf50"]}}],
                "layout": {"title": "Employee Net Promoter Score"}
            }
        }
    }
]

DUMMY_CHAT_RESPONSES = [
    "The APAC region shows a 5% margin compression caused by a checkout API latency spike.",
    "I recommend scaling checkout microservices and launching a targeted loyalty campaign.",
    "The EU email campaign is outperforming by 22%. Consider extending to other regions.",
    "I can pull up detailed analytics for any insight card. Which one interests you?",
]


# ──────────────────────────────────────────────
# Helpers (backend-ready)
# ──────────────────────────────────────────────
def fetch_insights() -> list[dict]:
    if USE_BACKEND:
        try:
            resp = requests.get(INSIGHTS_ENDPOINT, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return DUMMY_INSIGHTS
    return DUMMY_INSIGHTS


def send_chat_message(message: str) -> str:
    if USE_BACKEND:
        try:
            resp = requests.post(
                CHAT_ENDPOINT,
                json={"message": message, "session_id": st.session_state.get("session_id", "default")},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", data.get("reply", str(data)))
        except Exception as e:
            return f"Backend unavailable: {e}"
    return random.choice(DUMMY_CHAT_RESPONSES)


def dismiss_insight(insight_id: str):
    st.session_state.active_insights = [
        i for i in st.session_state.active_insights if i["insight_id"] != insight_id
    ]


def render_plotly(visuals: dict, key: str):
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
        elif t == "heatmap":
            fig.add_trace(go.Heatmap(**tc))
        elif t == "histogram":
            fig.add_trace(go.Histogram(**tc))
        else:
            fig.add_trace(go.Scatter(**tc))
    layout = plotly_data.get("layout", {})
    layout.update({
        "margin": dict(l=30, r=30, t=35, b=30),
        "height": 200,
        "paper_bgcolor": PLOTLY_BG,
        "plot_bgcolor": PLOTLY_BG,
        "font": {"family": "Inter", "size": 11, "color": CHART_TEXT},
        "title_font": {"size": 12, "color": CHART_TEXT},
        "legend": {"orientation": "h", "y": -0.3, "x": 0.5, "xanchor": "center", "font": {"size": 10, "color": CHART_TEXT}},
    })
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID, gridwidth=1, color=CHART_TEXT,
                     tickfont=dict(size=11, color=CHART_TEXT))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID, gridwidth=1, color=CHART_TEXT,
                     tickfont=dict(size=11, color=CHART_TEXT))
    st.plotly_chart(fig, key=f"chart_{key}", width="stretch")


# ──────────────────────────────────────────────
# Load insights
# ──────────────────────────────────────────────
if not st.session_state.active_insights:
    st.session_state.active_insights = fetch_insights()

# ──────────────────────────────────────────────
# TOP BAR – ICA + Light/Dark toggle
# ──────────────────────────────────────────────
top_left, top_spacer, top_right = st.columns([3, 5, 2])
with top_left:
    st.markdown(f'<div class="topbar-brand">🔬 Intelligent Consultant Agent</div>', unsafe_allow_html=True)
with top_right:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ──────────────────────────────────────────────
# MAIN LAYOUT: Insights (centre) + Chat (right)
# ──────────────────────────────────────────────
main_col, chat_col = st.columns([3, 1], gap="medium")

# ── CENTRE: Big insights box ──
with main_col:
    panel = st.container(border=True, key="insights_panel")
    with panel:
        insights = st.session_state.active_insights
        if not insights:
            st.info("No active insights. Click Refresh in the sidebar.")
        else:
            scroll = st.container(height=560)
            with scroll:
                for row_start in range(0, len(insights), 2):
                    row = insights[row_start: row_start + 2]
                    cols = st.columns(2, gap="medium")
                    for col, insight in zip(cols, row):
                        with col:
                            card_id = insight["insight_id"]
                            card = st.container(border=False, key=f"card_{card_id}")
                            with card:
                                meta = insight.get("meta", {})
                                content = insight.get("content", {})
                                visuals = insight.get("visuals", {})

                                urgency = meta.get("urgency_score", 0)
                                urg_cls = "urgent" if urgency >= 0.8 else ""
                                urg_lbl = "High" if urgency >= 0.8 else ("Med" if urgency >= 0.5 else "Low")
                                conf = int(meta.get("confidence_score", 0) * 100)

                                # Top row: meta tags + dismiss button (top-right)
                                meta_col, dismiss_col = st.columns([5, 1])
                                with meta_col:
                                    st.markdown(f"""
                                    <div style="margin-bottom:0.3rem;">
                                        <span class="meta-tag {urg_cls}">{urg_lbl}</span>
                                        <span class="meta-tag">🎯 {conf}%</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                with dismiss_col:
                                    if st.button("✕", key=f"dismiss_{card_id}"):
                                        dismiss_insight(card_id)
                                        st.rerun()

                                st.markdown(f'<h4 style="margin:0 0 0.2rem 0;font-size:0.88rem;font-weight:600;color:{TEXT} !important;">{content.get("headline", "Insight")}</h4>', unsafe_allow_html=True)

                                # Chart
                                if visuals:
                                    render_plotly(visuals, card_id)

                                # Summary
                                st.markdown(f'<div class="insight-summary">{content.get("summary", "")}</div>', unsafe_allow_html=True)

                                # Reasoning expander (full width)
                                chain = insight.get("reasoning_chain", [])
                                if chain:
                                    with st.expander("💡 Reasoning", expanded=False):
                                        for step in chain:
                                            st.markdown(f"**{step['step']}.** *{step['agent']}* – {step['thought']}")


# ── RIGHT: Chatbot panel ──
with chat_col:
    chat_panel = st.container(border=True, key="chat_panel")
    with chat_panel:
        st.markdown(f'<div class="panel-header">💬 Chatbot</div>', unsafe_allow_html=True)

        chat_box = st.container(height=420)
        with chat_box:
            if not st.session_state.chat_history:
                st.markdown("""
                <div class="chat-bubble assistant">
                    Hi! I'm your AI assistant. Ask me anything about your business data.
                </div>
                """, unsafe_allow_html=True)

            for msg in st.session_state.chat_history:
                cls = "user" if msg["role"] == "user" else "assistant"
                ico = "👤" if msg["role"] == "user" else "🤖"
                st.markdown(f"""
                <div class="chat-bubble {cls}">
                    {ico} {msg["content"]}
                    <div class="chat-time">{msg.get("time", "")}</div>
                </div>
                """, unsafe_allow_html=True)

        # Auto-scroll chat to bottom via components.html
        if st.session_state.chat_history:
            components.html("""
            <script>
            (function scrollChat() {
                const root = window.parent.document;
                function doScroll() {
                    const panel = root.querySelector('.st-key-chat_panel');
                    if (!panel) return;
                    const candidates = panel.querySelectorAll('*');
                    candidates.forEach(el => {
                        const cs = window.parent.getComputedStyle(el);
                        if ((cs.overflowY === 'auto' || cs.overflowY === 'scroll')
                            && el.scrollHeight > el.clientHeight) {
                            el.scrollTop = el.scrollHeight;
                        }
                    });
                }
                doScroll();
                setTimeout(doScroll, 150);
                setTimeout(doScroll, 500);
            })();
            </script>
            """, height=0, scrolling=False)

        user_input = st.chat_input("Ask anything...", key="chat_input")
        if user_input:
            now = datetime.now().strftime("%I:%M %p")
            st.session_state.chat_history.append({"role": "user", "content": user_input, "time": now})
            response = send_chat_message(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": response, "time": now})
            st.rerun()
