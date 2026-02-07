"""
ICA – Intelligent Enterprise Consultant
=========================================
Entry point for the multi-page Streamlit app.

Run with:
    streamlit run app.py

Pages:
  • home.py       – Dashboard with insight cards + chatbot
  • simulation.py – Simulation sandbox
"""

import streamlit as st
from theme import get_colors

# ──────────────────────────────────────────────
# Page config (must be the very first Streamlit command)
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="ICA Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Navigation pages (hidden default nav — we use custom sidebar buttons)
# ──────────────────────────────────────────────
home_page = st.Page("home.py", title="Home", icon="🏠", default=True)
sim_page = st.Page("simulation.py", title="Simulation", icon="📊")

pg = st.navigation([home_page, sim_page], position="hidden")

# ──────────────────────────────────────────────
# Theme state
# ──────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default to dark mode

# ──────────────────────────────────────────────
# Theme colours
# ──────────────────────────────────────────────
_c = get_colors(st.session_state.dark_mode)
BG       = _c["BG"];       BG2          = _c["BG2"]
CARD     = _c["CARD"];     CARD_INNER   = _c["CARD_INNER"]
BORDER   = _c["BORDER"];   BORDER_STRONG = _c["BORDER_STRONG"]
TEXT     = _c["TEXT"];      TEXT2        = _c["TEXT2"]
ACCENT   = _c["ACCENT"];   ACCENT_BG    = _c["ACCENT_BG"]
SIDEBAR_BG = _c["SIDEBAR_BG"]
HOVER_BG = _c["HOVER_BG"]
TOGGLE_BG = _c["TOGGLE_BG"]; TOGGLE_CHECKED = _c["TOGGLE_CHECKED"]

# ──────────────────────────────────────────────
# CSS – shared across all pages (sidebar, toggle, global controls)
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

.block-container {{
    padding-top: 0.8rem !important;
    padding-bottom: 0 !important;
}}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* === SIDEBAR – always visible, icon-only, expands on hover === */
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
    min-width: 43px !important;
    max-width: 43px !important;
    width: 43px !important;
    transition: min-width 0.25s ease, max-width 0.25s ease, width 0.25s ease !important;
    overflow: hidden !important;
    z-index: 999 !important;
}}
section[data-testid="stSidebar"]:hover {{
    min-width: 210px !important;
    max-width: 210px !important;
    width: 210px !important;
}}
/* Sidebar inner wrapper – full height, no scroll */
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
/* Hide sidebar close button & collapsed hamburger */
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
[data-testid="stSidebar"] .stButton {{
    margin: 0.15rem 0 !important;
    padding: 0 !important;
}}
/* Sidebar containers – no visible border */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"][style*="overflow"],
.st-key-account_section [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] .st-key-account_section {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* === Toggle switch styling === */
[data-testid="stCheckbox"] label span {{
    color: {TEXT2} !important;
    font-size: 0.82rem !important;
}}
label[data-testid="stWidgetLabel"] p {{
    color: {TEXT} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}
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
/* ToggleTrack */
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
/* Toggle thumb */
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
/* When checked: track turns red, thumb slides right */
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input:checked) > div:first-child,
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child {{
    background-color: {TOGGLE_CHECKED} !important;
    border-color: {TOGGLE_CHECKED} !important;
}}
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input:checked) > div:first-child > div,
.st-key-theme_toggle [data-testid="stCheckbox"] label:has(input[aria-checked="true"]) > div:first-child > div {{
    transform: translateX(22px) !important;
}}
/* Label text */
.st-key-theme_toggle [data-testid="stCheckbox"] label > span,
.st-key-theme_toggle [data-testid="stCheckbox"] label > div:last-child {{
    border: none !important;
    background: transparent !important;
    color: {TEXT} !important;
}}

/* === Hide tooltips === */
[data-testid="stTooltipIcon"],
[role="tooltip"],
.stTooltipContent {{
    display: none !important;
    visibility: hidden !important;
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SIDEBAR – shared navigation across all pages
# ──────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="text-align:center;padding:0.6rem 0 0.3rem 0;">
        <span style="font-size:1.5rem;">🔬</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Nav buttons
    if st.button("🏠   Home", key="nav_Home"):
        st.switch_page(home_page)
    if st.button("📊   Simulation", key="nav_Simulation"):
        st.switch_page(sim_page)
    if st.button("🔄   Refresh", key="nav_Refresh"):
        if "active_insights" in st.session_state:
            st.session_state.active_insights = []
        st.switch_page(home_page)

    # Account button – pushed to bottom via CSS
    with st.container(key="account_section"):
        st.markdown("---")
        if st.button("👤   Account", key="account"):
            st.toast("Account – coming soon!", icon="👤")

# ──────────────────────────────────────────────
# Run the selected page
# ──────────────────────────────────────────────
pg.run()
