"""
ICA – Intelligent Enterprise Consultant
=========================================
Entry point for the multi-page Streamlit app.

Run with:
    streamlit run app.py

Pages:
  • home.py          – Dashboard with insight cards + chatbot
  • simulation.py    – Simulation sandbox
  • admin_pages.py   – Admin user management (admin-only)

Authentication:
  Mocked via auth_utils.py — see API_CONTRACT.md for the real endpoints.
"""

import streamlit as st
from theme import get_colors
from auth_utils import (
    init_auth_state,
    is_authenticated,
    is_admin,
    get_current_user,
    mock_login,
    logout,
)

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
# Auth state
# ──────────────────────────────────────────────
init_auth_state()

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
# LOGIN SCREEN  (shown when not authenticated)
# ──────────────────────────────────────────────
if not is_authenticated():
    # Hide sidebar completely on login page
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    # Centred login card
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main, .block-container {{
        background-color: {BG} !important;
        color: {TEXT} !important;
    }}
    .login-logo {{
        text-align: center;
        font-size: 3rem;
        margin-bottom: 0.2rem;
        margin-top: 6vh;
    }}
    .login-title {{
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: {ACCENT};
        margin-bottom: 0.1rem;
    }}
    .login-subtitle {{
        text-align: center;
        font-size: 0.85rem;
        color: {TEXT2};
        margin-bottom: 1.5rem;
    }}
    /* Style inputs */
    [data-testid="stTextInput"] input {{
        background: {BG2} !important;
        color: {TEXT} !important;
        border: 1.5px solid {BORDER} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stTextInput"] label p {{
        color: {TEXT} !important;
        font-weight: 500 !important;
    }}
    /* Form container */
    [data-testid="stForm"] {{
        background: {CARD} !important;
        border: 2px solid {BORDER_STRONG} !important;
        border-radius: 20px !important;
        padding: 1.5rem !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.25) !important;
    }}
    /* Primary button inside form */
    [data-testid="stForm"] button[data-testid="stBaseButton-primaryFormSubmit"] {{
        background: {ACCENT} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        margin-top: 0.5rem !important;
    }}
    [data-testid="stForm"] button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{
        opacity: 0.85 !important;
    }}
    /* Caption */
    .stCaption, [data-testid="stCaption"] {{
        color: {TEXT2} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-logo">🔬</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Intelligent Enterprise Consultant</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Sign in to access your dashboard</div>', unsafe_allow_html=True)

    # Form
    col_l, col_form, col_r = st.columns([1, 2, 1])
    with col_form:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="admin / user / cfo / cto")
            password = st.text_input("Password", type="password", placeholder="same as username")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submitted:
                if mock_login(username.strip(), password.strip()):
                    st.rerun()
                else:
                    st.error(st.session_state.login_error)

        st.caption("Demo credentials: `admin`/`admin` · `user`/`user` · `cfo`/`cfo` · `cto`/`cto`")

    st.stop()  # ← nothing below runs until authenticated

# ══════════════════════════════════════════════
# AUTHENTICATED — build navigation & shared CSS
# ══════════════════════════════════════════════

# ──────────────────────────────────────────────
# Navigation pages
# ──────────────────────────────────────────────
home_page = st.Page("home.py", title="Home", icon="🏠", default=True)
sim_page = st.Page("simulation.py", title="Simulation", icon="📊")

nav_pages = [home_page, sim_page]

# Add admin page if current user is admin
if is_admin():
    admin_page = st.Page("admin_pages.py", title="Admin", icon="⚙️")
    nav_pages.append(admin_page)

pg = st.navigation(nav_pages, position="hidden")

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

/* === Selectbox (dropdowns) === */
[data-testid="stSelectbox"] > div > div {{
    background: {BG2} !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 10px !important;
}}
[data-testid="stSelectbox"] [data-testid="stMarkdown"] p {{
    color: {TEXT} !important;
}}
[data-baseweb="select"] span {{
    color: {TEXT} !important;
}}
[data-baseweb="popover"] li {{
    background: {BG2} !important;
    color: {TEXT} !important;
}}
[data-baseweb="popover"] li:hover {{
    background: {HOVER_BG} !important;
}}
[data-baseweb="popover"] ul {{
    background: {BG2} !important;
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
current_user = get_current_user()
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

    # Admin nav (only for admins)
    if is_admin():
        if st.button("⚙️   Admin", key="nav_Admin"):
            st.switch_page(admin_page)

    # Account section – pushed to bottom via CSS
    with st.container(key="account_section"):
        st.markdown("---")

        # Show current user info
        if current_user:
            display = current_user.get("display_name", current_user["username"])
            role_badge = current_user.get("title", current_user.get("role", ""))
            st.markdown(f"""
            <div style="font-size:0.72rem;color:{TEXT2};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                👤 {display}<br>
                <span style="font-size:0.65rem;color:{ACCENT};">{role_badge}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚪   Logout", key="logout_btn"):
            logout()
            st.rerun()

# ──────────────────────────────────────────────
# Run the selected page
# ──────────────────────────────────────────────
pg.run()
