"""
ICA – Admin Pages
==================
User management dashboard for admin users.
This file is loaded by app.py via st.navigation() (admin-only).
"""

import streamlit as st
import pandas as pd
from theme import get_colors
from auth_utils import get_all_users, create_user, delete_user, is_admin

# ──────────────────────────────────────────────
# Guard: only admins can access this page
# ──────────────────────────────────────────────
if not is_admin():
    st.error("Access denied. Admin privileges required.")
    st.stop()

# ──────────────────────────────────────────────
# Theme colours
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
HOVER_BG     = _c["HOVER_BG"]
PANEL_SHADOW = _c["PANEL_SHADOW"]

ROLES_OPTIONS = ["admin", "user"]
DEPARTMENTS = ["Executive", "Finance", "Engineering", "HR", "Operations", "Sales", "Marketing", "IT", "Legal"]
TITLES = ["Admin", "CEO", "CFO", "COO", "CTO", "CMO", "CHRO", "VP Sales", "VP Engineering", "Analyst"]

# ──────────────────────────────────────────────
# Page CSS
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
/* Global background */
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

/* Panel borders */
[data-testid="stVerticalBlock"].st-key-admin_users_panel,
[data-testid="stVerticalBlock"].st-key-admin_create_panel,
[data-testid="stVerticalBlock"].st-key-admin_audit_panel {{
    border: 3px solid {BORDER_STRONG} !important;
    border-radius: 16px !important;
    background: {CARD} !important;
    box-shadow: {PANEL_SHADOW} !important;
    padding: 0.8rem !important;
}}

/* All text forced to theme */
[data-testid="stMain"] [data-testid="stMarkdown"],
[data-testid="stMain"] p,
[data-testid="stMain"] span,
[data-testid="stMain"] label,
[data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] h4,
[data-testid="stMain"] td, [data-testid="stMain"] th {{
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
}}
.stButton > button:hover {{
    background: {HOVER_BG} !important;
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {ACCENT} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}}

/* Form container */
[data-testid="stForm"] {{
    background: {CARD_INNER} !important;
    border: 1.5px solid {BORDER} !important;
    border-radius: 14px !important;
    padding: 1rem !important;
}}

/* Inputs */
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

/* Selectbox */
[data-testid="stSelectbox"] > div > div {{
    background: {BG2} !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 10px !important;
}}
[data-baseweb="select"] span {{ color: {TEXT} !important; }}

/* Dataframe table */
[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    overflow: hidden !important;
}}

/* Panel header */
.admin-panel-header {{
    font-weight: 700;
    font-size: 1rem;
    color: {ACCENT} !important;
    margin-bottom: 0.5rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {BORDER};
}}

/* Stat cards */
.admin-stat {{
    background: {CARD_INNER};
    border: 1.5px solid {BORDER};
    border-radius: 12px;
    padding: 0.8rem 1rem;
    text-align: center;
}}
.admin-stat .stat-value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: {ACCENT};
}}
.admin-stat .stat-label {{
    font-size: 0.78rem;
    color: {TEXT2};
    margin-top: 0.2rem;
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# TOP BAR
# ──────────────────────────────────────────────
top_brand, _, top_toggle = st.columns([4, 3, 2])
with top_brand:
    st.markdown(f'<div style="font-size:1.3rem;font-weight:700;color:{ACCENT};">⚙️ Admin Dashboard</div>', unsafe_allow_html=True)
with top_toggle:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ──────────────────────────────────────────────
# Summary stats
# ──────────────────────────────────────────────
users = get_all_users()
total = len(users)
admins = sum(1 for u in users if u["role"] == "admin")
regulars = total - admins
depts = len(set(u.get("department", "") for u in users))

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="admin-stat"><div class="stat-value">{total}</div><div class="stat-label">Total Users</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="admin-stat"><div class="stat-value">{admins}</div><div class="stat-label">Admins</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="admin-stat"><div class="stat-value">{regulars}</div><div class="stat-label">Regular Users</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="admin-stat"><div class="stat-value">{depts}</div><div class="stat-label">Departments</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# MAIN LAYOUT: User table (left) + Create form (right)
# ──────────────────────────────────────────────
col_table, col_form = st.columns([3, 2], gap="large")

# ── LEFT: User table ──
with col_table:
    with st.container(border=True, key="admin_users_panel"):
        st.markdown('<div class="admin-panel-header">👥 User Management</div>', unsafe_allow_html=True)

        if users:
            df = pd.DataFrame(users)
            # Reorder columns
            display_cols = ["username", "display_name", "role", "department", "title"]
            display_cols = [c for c in display_cols if c in df.columns]
            df = df[display_cols]
            df.columns = ["Username", "Name", "Role", "Department", "Title"][:len(display_cols)]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=min(400, 45 + len(df) * 35),
            )
        else:
            st.info("No users found.")

        # Delete user section
        st.markdown("---")
        st.markdown(f'<div style="font-size:0.85rem;font-weight:600;color:{TEXT};">Remove User</div>', unsafe_allow_html=True)
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            usernames = [u["username"] for u in users if u["username"] != "admin"]
            if usernames:
                del_target = st.selectbox("Select user to remove", usernames, key="del_user_select", label_visibility="collapsed")
            else:
                del_target = None
                st.caption("No removable users.")
        with del_col2:
            if del_target and st.button("🗑️ Delete", key="del_user_btn", type="primary"):
                ok, msg = delete_user(del_target)
                if ok:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)

# ── RIGHT: Create user form ──
with col_form:
    with st.container(border=True, key="admin_create_panel"):
        st.markdown('<div class="admin-panel-header">➕ Create New User</div>', unsafe_allow_html=True)

        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input("Username *", placeholder="e.g. jdoe")
            new_password = st.text_input("Password *", type="password", placeholder="Set a password")
            new_display = st.text_input("Display Name *", placeholder="e.g. Jane Doe")
            new_role = st.selectbox("Role *", ROLES_OPTIONS, index=1)
            new_dept = st.selectbox("Department *", DEPARTMENTS, index=0)
            new_title = st.selectbox("Title *", TITLES, index=1)

            create_submitted = st.form_submit_button("Create User", type="primary", use_container_width=True)

            if create_submitted:
                if not new_username.strip() or not new_password.strip() or not new_display.strip():
                    st.error("Username, password, and display name are required.")
                else:
                    ok, msg = create_user(
                        username=new_username.strip(),
                        password=new_password.strip(),
                        display_name=new_display.strip(),
                        role=new_role,
                        department=new_dept,
                        title=new_title,
                    )
                    if ok:
                        st.toast(msg, icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)

    # Audit log placeholder
    with st.container(border=True, key="admin_audit_panel"):
        st.markdown('<div class="admin-panel-header">📋 API Contract Status</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:0.8rem;color:{TEXT2};line-height:1.6;">
            <b>Backend endpoints needed:</b><br>
            ⬜ <code>POST /auth/login</code> — Authentication<br>
            ⬜ <code>GET /admin/users</code> — List users<br>
            ⬜ <code>POST /admin/users</code> — Create user<br>
            ⬜ <code>DELETE /admin/users/{{username}}</code> — Delete user<br>
            ⬜ <code>POST /context/upload</code> — File upload<br>
            ⬜ <code>POST /integrations/slack/connect</code> — Slack<br>
            <br>
            <em>See <code>API_CONTRACT.md</code> for full specifications.</em>
        </div>
        """, unsafe_allow_html=True)
