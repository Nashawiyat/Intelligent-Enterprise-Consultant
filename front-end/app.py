"""
ICA – Intelligent Enterprise Consultant
=========================================
Simple Streamlit dashboard:
  • Left narrow sidebar  – ICA logo, nav (Home/Sim/Custom), account button at bottom
  • Top bar              – ICA title + Light/Dark toggle
  • Centre               – Big box with 2×2 insight cards (internally scrollable)
  • Right                – Chatbot panel
Backend-ready: all data flows through JSON from FastAPI.
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
import random
from datetime import datetime

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="ICA Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# Theme state
# ──────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default to dark mode

# ──────────────────────────────────────────────
# Theme colours
# ──────────────────────────────────────────────
if st.session_state.dark_mode:
    BG = "#1e1e2e"
    BG2 = "#2a2a3c"
    CARD = "#2a2a3c"
    CARD_INNER = "#33334a"
    BORDER = "#3e3e56"
    TEXT = "#e0e0e0"
    TEXT2 = "#b0b0c0"
    ACCENT = "#66bb6a"
    ACCENT_BG = "#2e3d2e"
    SIDEBAR_BG = f"linear-gradient(180deg, {BG2} 0%, {BG} 100%)"
    TOPBAR_BG = BG2
    CHAT_ASSIST_BG = "#33334a"
    CHAT_USER_BG = "#2e3d2e"
    INPUT_BG = BG2
    HOVER_BG = "#3e3e56"
    PLOTLY_BG = CARD_INNER
    BORDER_STRONG = BORDER
    CHART_TEXT = "#cccccc"
    CHART_GRID = "#4a4a60"
    PANEL_SHADOW = "0 4px 16px rgba(0,0,0,0.3)"
    TOGGLE_BG = "#4a4a60"
    TOGGLE_CHECKED = "#ef5350"  # red when dark mode is ON
else:
    BG = "#f8f9fa"           # Page bg – clean near-white
    BG2 = "#ffffff"
    CARD = "#ffffff"          # Panel bg – pure white
    CARD_INNER = "#f3f5f7"    # Card bg – subtle off-white
    BORDER = "#d0d5da"        # Light border for inner cards
    BORDER_STRONG = "#2c2c2c" # Near-black for outer panel edges
    TEXT = "#111111"
    TEXT2 = "#333333"
    CHART_TEXT = "#111111"
    CHART_GRID = "#c0c5cc"
    ACCENT = "#2e7d32"
    ACCENT_BG = "#e8f5e9"
    SIDEBAR_BG = "#ffffff"
    TOPBAR_BG = "#ffffff"
    CHAT_ASSIST_BG = "#f0f2f5"
    CHAT_USER_BG = "#e8f5e9"
    INPUT_BG = "#ffffff"
    HOVER_BG = "#e8f5e9"
    PLOTLY_BG = "#ffffff"
    PANEL_SHADOW = "0 2px 8px rgba(0,0,0,0.08)"
    TOGGLE_BG = "#b0b5bb"
    TOGGLE_CHECKED = "#ef5350"  # red when toggled ON

# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

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
.block-container {{
    padding-top: 0.8rem !important;
    padding-bottom: 0 !important;
}}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}  /* safe: sidebar forced via transform:none */

/* === SIDEBAR – always visible, icon-only, expands on hover === */
/* ┌──────────────────────────────────────────────────────────────┐ */
/* │  COLLAPSED WIDTH: change the three 58px values below.       │ */
/* │  EXPANDED WIDTH:  change the three 210px values below.      │ */
/* └──────────────────────────────────────────────────────────────┘ */
section[data-testid="stSidebar"] {{
    transform: none !important;
    visibility: visible !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    bottom: 0 !important;
    height: 100vh !important;
    background: {SIDEBAR_BG} !important;
    border-right: 3px solid {BORDER_STRONG} !important;
    border-radius: 0 16px 16px 0 !important;
    box-shadow: 3px 0 16px rgba(0,0,0,0.12) !important;
    min-width: 43px !important;   /* ← collapsed width */
    max-width: 43px !important;   /* ← collapsed width */
    width: 43px !important;       /* ← collapsed width */
    transition: min-width 0.25s ease, max-width 0.25s ease, width 0.25s ease !important;
    overflow: hidden !important;
    z-index: 999 !important;
}}
section[data-testid="stSidebar"]:hover {{
    min-width: 210px !important;  /* ← expanded width */
    max-width: 210px !important;  /* ← expanded width */
    width: 210px !important;      /* ← expanded width */
}}
/* Sidebar inner wrapper – full height, no scroll, no overflow clipping */
section[data-testid="stSidebar"] > div {{
    height: 100% !important;
    overflow: visible !important;
    display: flex !important;
    flex-direction: column !important;
}}
/* All nested sidebar containers stretch to fill available height */
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {{
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 0% !important;
    height: 100% !important;
    min-height: 0 !important;
    max-height: 100vh !important;
    overflow: visible !important;
}}
/* Sidebar content padding */
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding: 0.9rem 0.6rem !important;
    box-sizing: border-box !important;
}}
/* Gap between elements in sidebar vertical blocks */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 0.35rem !important;
}}
/* Element container spacing in sidebar */
section[data-testid="stSidebar"] [data-testid="stElementContainer"] {{
    margin-bottom: 0 !important;
    margin-top: 0 !important;
}}
/* The account section – pushed to bottom via margin-top:auto */
.st-key-account_section {{
    margin-top: auto !important;
    padding-top: 0.5rem !important;
    padding-bottom: 0.8rem !important;
}}
/* Sidebar buttons: only show icon when collapsed, full text on hover */
[data-testid="stSidebar"] .stButton > button {{
    min-width: 36px !important;
    max-width: 36px !important;
    padding: 0.35rem !important;
    text-align: center !important;
    overflow: hidden !important;
    text-overflow: clip !important;
    justify-content: center !important;
    transition: max-width 0.25s ease, padding 0.25s ease !important;
}}
section[data-testid="stSidebar"]:hover .stButton > button {{
    max-width: 200px !important;
    padding: 0.4rem 0.6rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
}}
/* Hide sidebar close button & collapsed hamburger – sidebar is always open */
[data-testid="collapsedControl"] {{
    display: none !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] button[kind="headerNoPadding"],
section[data-testid="stSidebar"] > div:first-child > button {{
    display: none !important;
}}
[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}
[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    background: transparent !important;
    color: {TEXT} !important;
    border: 1.5px solid transparent !important;
    border-radius: 12px;
    margin-bottom: 0rem;
    font-weight: 500;
    font-size: 0.85rem;
    white-space: nowrap;
    padding: 0.35rem !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: {ACCENT_BG} !important;
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {BORDER} !important;
    margin: 0.6rem 0 !important;
}}
/* stButton wrapper spacing in sidebar */
[data-testid="stSidebar"] .stButton {{
    margin: 0.15rem 0 !important;
    padding: 0 !important;
}}

/* === Top bar (flat, no box) === */
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

/* === PANEL BORDERS – targeted by container key (st.container key= adds .st-key-xxx class) === */
[data-testid="stVerticalBlock"].st-key-insights_panel,
[data-testid="stVerticalBlock"].st-key-chat_panel {{
    border: 3px solid {BORDER_STRONG} !important;
    border-radius: 16px !important;
    background: {CARD} !important;
    box-shadow: {PANEL_SHADOW} !important;
    padding: 0.5rem !important;
}}
/* Scroll container & sidebar containers – no visible border */
.st-key-insights_panel [data-testid="stVerticalBlock"][style*="overflow"],
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"][style*="overflow"],
.st-key-account_section [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] .st-key-account_section {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* === Insight card borders – only target containers with card keys === */
[data-testid="stVerticalBlock"][class*="st-key-card_"] {{
    border: 2px solid {BORDER_STRONG} !important;
    border-radius: 14px !important;
    background: {CARD_INNER} !important;
    padding: 0.6rem !important;
}}
/* Remove any borders from elements INSIDE cards (columns, nested blocks) */
[data-testid="stVerticalBlock"][class*="st-key-card_"] [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlock"][class*="st-key-card_"] [data-testid="stHorizontalBlock"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* === Insight card === */
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

/* === ALL text forced to theme === */
[data-testid="stMarkdown"], [data-testid="stText"],
p, span, label, h1, h2, h3, h4, h5, h6, li, td, th,
[data-testid="stMarkdown"] p, [data-testid="stMarkdown"] span {{
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
/* Hide tooltip elements */
[data-testid="stTooltipIcon"],
[role="tooltip"],
.stTooltipContent {{
    display: none !important;
    visibility: hidden !important;
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

/* === Toggle switch styling === */
[data-testid="stCheckbox"] label span {{
    color: {TEXT2} !important;
    font-size: 0.82rem !important;
}}

/* === st.toggle visibility fix === */
label[data-testid="stWidgetLabel"] p {{
    color: {TEXT} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}

/*
 * Toggle visibility fix for BaseUI.
 * DOM: <div data-baseweb="checkbox"> <label> <ToggleTrack div> <Toggle div (thumb)> </ToggleTrack> <input type=checkbox hidden> <Label span>
 * The ToggleTrack is a styled div with inline backgroundColor from BaseUI theme.
 * The Toggle (thumb) uses transform:translateX() to slide; has inline backgroundColor.
 */
/* Align the whole toggle widget vertically with the label text */
.st-key-theme_toggle [data-testid="stCheckbox"] {{
    display: flex !important;
    align-items: center !important;
}}
.st-key-theme_toggle [data-testid="stCheckbox"] [data-baseweb="checkbox"] {{
    display: flex !important;
    align-items: center !important;
}}
.st-key-theme_toggle [data-testid="stCheckbox"] label {{
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}}
/* ToggleTrack – the first div child of label (overrides inline bg) */
.st-key-theme_toggle [data-testid="stCheckbox"] label > div:first-child {{
    background-color: {TOGGLE_BG} !important;
    border: 2px solid {BORDER_STRONG} !important;
    border-radius: 999px !important;
    min-width: 48px !important;
    width: 48px !important;
    height: 26px !important;
    min-height: 26px !important;
    display: flex !important;
    align-items: center !important;
    padding: 2px 3px !important;
    cursor: pointer !important;
    position: relative !important;
    flex-shrink: 0 !important;
    margin-top: 0 !important;
    box-sizing: border-box !important;
}}
/* Toggle thumb (div inside the track) – position via transform */
.st-key-theme_toggle [data-testid="stCheckbox"] label > div:first-child > div {{
    background-color: #ffffff !important;
    border-radius: 50% !important;
    width: 18px !important;
    height: 18px !important;
    min-width: 18px !important;
    min-height: 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    transition: transform 0.2s ease !important;
    transform: translateX(0px) !important;
}}
/* When checked (dark mode ON): track turns red, thumb slides right.
 * NOTE: input is a CHILD of label (not a sibling), and comes AFTER the track div.
 * So input:checked ~ label can never match. Use :has() instead.
 */
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input:checked) > div:first-child,
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child {{
    background-color: {TOGGLE_CHECKED} !important;
    border-color: {TOGGLE_CHECKED} !important;
}}
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input:checked) > div:first-child > div,
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child > div {{
    transform: translateX(22px) !important;
}}
/* Label text – no rogue styling */
.st-key-theme_toggle [data-testid="stCheckbox"] label > span,
.st-key-theme_toggle [data-testid="stCheckbox"] label > div:last-child {{
    border: none !important;
    background: transparent !important;
    color: {TEXT} !important;
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
# SIDEBAR – narrow nav per wireframe
# ──────────────────────────────────────────────
with st.sidebar:
    # Logo – centered icon, text visible on hover
    st.markdown(f"""
    <div style="text-align:center;padding:0.6rem 0 0.3rem 0;">
        <span style="font-size:1.5rem;">🔬</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Nav buttons – icon always visible, label clips when collapsed
    nav = [("🏠", "Home"), ("📊", "Simulation"), ("🔄", "Refresh")]
    for icon, label in nav:
        if st.button(f"{icon}   {label}", key=f"nav_{label}"):
            if label == "Refresh":
                st.session_state.active_insights = fetch_insights()
                st.rerun()
            else:
                st.toast(f"{label} – coming soon!", icon="🚧")

    # Account button – pushed to bottom via CSS (key-targeted margin-top:auto)
    with st.container(key="account_section"):
        st.markdown("---")
        if st.button("👤   Account", key="account"):
            st.toast("Account – coming soon!", icon="👤")

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

        # Auto-scroll chat to bottom via components.html (st.markdown strips <script>)
        if st.session_state.chat_history:
            components.html("""
            <script>
            (function scrollChat() {
                const root = window.parent.document;
                // Find ANY scrollable element inside the chat panel by checking
                // computed style, not inline attributes — Streamlit may set
                // overflow via CSS classes rather than inline style.
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
                // Run immediately, then again after a short delay to catch
                // late-rendered content.
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
