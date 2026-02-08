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
import json
import time
from datetime import datetime
from theme import get_colors
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────
# Backend config
# ──────────────────────────────────────────────
try:
    BACKEND_BASE_URL = st.secrets["BACKEND_URL"]
except Exception:
    BACKEND_BASE_URL = "http://localhost:8000"
INSIGHTS_ENDPOINT = f"{BACKEND_BASE_URL}/insights"
PROMPT_ENDPOINT = f"{BACKEND_BASE_URL}/prompt"

# Domains and roles available (aligned with backend ALLOWED_SILOS)
DOMAINS = ["Sales", "Operations", "HR", "Accounting", "CRM"]
ROLES = ["CEO", "CFO", "COO", "CTO", "CMO", "CHRO", "VP Sales", "VP Engineering", "Analyst"]

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
if "selected_role" not in st.session_state:
    st.session_state.selected_role = "CEO"
if "selected_domain" not in st.session_state:
    st.session_state.selected_domain = "Sales"
if "last_insight_fetch" not in st.session_state:
    st.session_state.last_insight_fetch = 0.0
if "insight_error" not in st.session_state:
    st.session_state.insight_error = None

INSIGHT_REFRESH_INTERVAL = 10  # seconds

# Auto-refresh the page to poll for new insights
st_autorefresh(interval=INSIGHT_REFRESH_INTERVAL * 1000, limit=None, key="insight_autorefresh")


# ──────────────────────────────────────────────
# Helpers (backend integration)
# ──────────────────────────────────────────────
def fetch_insights(domain: str, role: str) -> list[dict]:
    """Fetch insights from backend POST /insights."""
    try:
        resp = requests.post(
            INSIGHTS_ENDPOINT,
            json={"domain": domain.lower(), "role_context": role},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Backend may return a single insight dict or a list
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        return []
    except requests.exceptions.ConnectionError:
        st.session_state.insight_error = "Backend not reachable. Start the backend server."
        return []
    except Exception as e:
        st.session_state.insight_error = f"Error fetching insights: {e}"
        return []


def send_chat_message(message: str, domain: str, role: str) -> str:
    """Send a prompt to backend POST /prompt and return the response text."""
    try:
        resp = requests.post(
            PROMPT_ENDPOINT,
            json={"domain": domain.lower(), "role_context": role, "prompt": message},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Backend returns insight JSON; extract chat_response or summary
        if isinstance(data, dict):
            # Chat mode returns {"chat_response": "..."}
            if "chat_response" in data:
                return data["chat_response"]
            # Report mode returns full insight JSON — extract summary
            content = data.get("content", {})
            if isinstance(content, dict) and content.get("summary"):
                return content["summary"]
            return json.dumps(data, indent=2)
        return str(data)
    except requests.exceptions.ConnectionError:
        return "Backend not reachable. Please start the backend server."
    except Exception as e:
        return f"Error: {e}"


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
# TOP BAR – ICA + Role/Domain selectors + Light/Dark toggle
# ──────────────────────────────────────────────
top_brand, top_domain, top_role, top_toggle = st.columns([3, 2, 2, 2])
with top_brand:
    st.markdown(f'<div class="topbar-brand">🔬 Intelligent Consultant Agent</div>', unsafe_allow_html=True)
with top_domain:
    domain_idx = DOMAINS.index(st.session_state.selected_domain) if st.session_state.selected_domain in DOMAINS else 0
    new_domain = st.selectbox("Domain", DOMAINS, index=domain_idx, key="domain_select", label_visibility="collapsed")
    if new_domain != st.session_state.selected_domain:
        st.session_state.selected_domain = new_domain
        st.session_state.active_insights = []
        st.session_state.last_insight_fetch = 0.0
        st.rerun()
with top_role:
    role_idx = ROLES.index(st.session_state.selected_role) if st.session_state.selected_role in ROLES else 0
    new_role = st.selectbox("Role", ROLES, index=role_idx, key="role_select", label_visibility="collapsed")
    if new_role != st.session_state.selected_role:
        st.session_state.selected_role = new_role
        st.session_state.active_insights = []
        st.session_state.last_insight_fetch = 0.0
        st.rerun()
with top_toggle:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ──────────────────────────────────────────────
# Auto-refresh insights every INSIGHT_REFRESH_INTERVAL seconds
# ──────────────────────────────────────────────
now = time.time()
if now - st.session_state.last_insight_fetch >= INSIGHT_REFRESH_INTERVAL:
    st.session_state.insight_error = None
    fresh = fetch_insights(st.session_state.selected_domain, st.session_state.selected_role)
    if fresh:
        st.session_state.active_insights = fresh
    st.session_state.last_insight_fetch = now

# ──────────────────────────────────────────────
# MAIN LAYOUT: Insights (centre) + Chat (right)
# ──────────────────────────────────────────────
main_col, chat_col = st.columns([3, 1], gap="medium")

# ── CENTRE: Big insights box ──
with main_col:
    panel = st.container(border=True, key="insights_panel")
    with panel:
        insights = st.session_state.active_insights

        # Show error banner if backend unreachable
        if st.session_state.insight_error:
            st.warning(st.session_state.insight_error)

        if not insights:
            if not st.session_state.insight_error:
                st.info(f"Fetching insights for **{st.session_state.selected_domain}** as **{st.session_state.selected_role}**…")
        else:
            scroll = st.container(height=560)
            with scroll:
                # Backend may return a single insight — always iterate as list
                for row_start in range(0, len(insights), 2):
                    row = insights[row_start: row_start + 2]
                    cols = st.columns(2, gap="medium")
                    for col, insight in zip(cols, row):
                        with col:
                            card_id = insight.get("insight_id", f"card_{row_start}")
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
                                if visuals and visuals.get("plotly_data"):
                                    render_plotly(visuals, card_id)

                                # Summary
                                st.markdown(f'<div class="insight-summary">{content.get("summary", "")}</div>', unsafe_allow_html=True)

                                # Recommendations
                                recs = content.get("recommendations", [])
                                if recs:
                                    with st.expander("📋 Recommendations", expanded=False):
                                        for rec in recs:
                                            st.markdown(f"**{rec.get('action', '')}** – {rec.get('detail', '')}  \n*Impact: {rec.get('expected_impact', 'N/A')}*")

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
            now_str = datetime.now().strftime("%I:%M %p")
            st.session_state.chat_history.append({"role": "user", "content": user_input, "time": now_str})
            response = send_chat_message(
                user_input,
                st.session_state.selected_domain,
                st.session_state.selected_role,
            )
            st.session_state.chat_history.append({"role": "assistant", "content": response, "time": now_str})
            st.rerun()
