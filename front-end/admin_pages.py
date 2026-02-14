"""
ICA – User Management (Admin)
==============================
Batch-editing interface for admin users.
Features: paginated editable grid, inline password masking,
role/dept/title filters, batch save + batch delete.

Loaded by app.py via st.navigation() — admin-only.
"""

import streamlit as st
import pandas as pd
import math
from theme import get_colors
from auth_utils import (
    is_admin,
    get_all_users,
    get_all_users_with_passwords,
    create_user,
    delete_user,
    batch_update_users,
    search_user_by_username,
    PASSWORD_MASK,
)

# ──────────────────────────────────────────────
# Access guard (programmatic safeguard)
# ──────────────────────────────────────────────
if not is_admin():
    st.error("⛔ Access denied. Admin privileges required.")
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

ROWS_PER_PAGE = 10

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
[data-testid="stVerticalBlock"].st-key-admin_contract_panel {{
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
button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
button[data-testid="stBaseButton-primary"]:hover {{
    opacity: 0.85 !important;
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

/* Data editor / Dataframe table */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {{
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

/* Password-mismatch warning */
.pw-mismatch {{
    color: #e53935 !important;
    font-size: 0.8rem;
    font-weight: 600;
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session state for pagination & filters
# ──────────────────────────────────────────────
if "admin_page_idx" not in st.session_state:
    st.session_state.admin_page_idx = 0
if "admin_filter_role" not in st.session_state:
    st.session_state.admin_filter_role = "All"
if "admin_filter_dept" not in st.session_state:
    st.session_state.admin_filter_dept = "All"
if "admin_filter_title" not in st.session_state:
    st.session_state.admin_filter_title = "All"
if "admin_search_query" not in st.session_state:
    st.session_state.admin_search_query = ""
if "admin_search_active" not in st.session_state:
    st.session_state.admin_search_active = False
if "admin_search_result" not in st.session_state:
    st.session_state.admin_search_result = None  # None = no search, [] = not found, [user] = found

# ──────────────────────────────────────────────
# TOP BAR
# ──────────────────────────────────────────────
top_brand, _, top_toggle = st.columns([4, 3, 2])
with top_brand:
    st.markdown(
        f'<div style="font-size:1.3rem;font-weight:700;color:{ACCENT};">👥 User Management</div>',
        unsafe_allow_html=True,
    )
with top_toggle:
    toggled = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if toggled != st.session_state.dark_mode:
        st.session_state.dark_mode = toggled
        st.rerun()

# ──────────────────────────────────────────────
# Summary stats
# ──────────────────────────────────────────────
all_users = get_all_users()  # without passwords (for stat display)
total = len(all_users)
admins_count = sum(1 for u in all_users if u["role"] == "admin")
regulars_count = total - admins_count
depts_count = len({u.get("department", "") for u in all_users})

c1, c2, c3, c4 = st.columns(4)
for col, val, label in [
    (c1, total, "Total Users"),
    (c2, admins_count, "Admins"),
    (c3, regulars_count, "Regular Users"),
    (c4, depts_count, "Departments"),
]:
    with col:
        st.markdown(
            f'<div class="admin-stat"><div class="stat-value">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# MAIN LAYOUT: Editable table (left) + Create form (right)
# ══════════════════════════════════════════════
col_table, col_form = st.columns([3, 2], gap="large")

# ─────────────────────────────────────────────
# LEFT: Editable User Grid with Pagination
# ─────────────────────────────────────────────
with col_table:
    with st.container(border=True, key="admin_users_panel"):
        st.markdown(
            '<div class="admin-panel-header">📋 All Users — Batch Editing</div>',
            unsafe_allow_html=True,
        )

        # ══════════════════════════════════════════════
        # SEARCH BAR
        # ══════════════════════════════════════════════
        srch_c1, srch_c2, srch_c3 = st.columns([5, 1, 1])
        with srch_c1:
            search_input = st.text_input(
                "Search by Username",
                value=st.session_state.admin_search_query,
                placeholder="Enter exact username…",
                key="search_username_input",
                label_visibility="collapsed",
            )
        with srch_c2:
            search_clicked = st.button("🔍 Search", key="search_btn", use_container_width=True)
        with srch_c3:
            clear_clicked = st.button("✕ Clear", key="clear_search_btn", use_container_width=True)

        if clear_clicked:
            st.session_state.admin_search_query = ""
            st.session_state.admin_search_active = False
            st.session_state.admin_search_result = None
            st.rerun()

        if search_clicked:
            query = search_input.strip()
            st.session_state.admin_search_query = query
            if not query:
                st.session_state.admin_search_active = False
                st.session_state.admin_search_result = None
            else:
                st.session_state.admin_search_active = True
                st.session_state.admin_search_result = search_user_by_username(query)
            st.rerun()

        # ══════════════════════════════════════════════
        # SEARCH-MODE VIEW: single user editable table
        # ══════════════════════════════════════════════
        if st.session_state.admin_search_active:
            result = st.session_state.admin_search_result

            if not result:
                st.warning(
                    f"No user found with username: **{st.session_state.admin_search_query}**"
                )
            else:
                found_user = result[0]
                st.info(f"Showing result for username: **{found_user['username']}**")

                search_rows = [{
                    "Username": found_user["username"],
                    "Name": found_user.get("display_name", ""),
                    "Role": found_user.get("role", "user"),
                    "Department": found_user.get("department", ""),
                    "Title": found_user.get("title", ""),
                    "Password": PASSWORD_MASK,
                }]
                search_df = pd.DataFrame(search_rows)

                search_column_config = {
                    "Username": st.column_config.TextColumn("Username", disabled=True, width="small"),
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Role": st.column_config.SelectboxColumn("Role", options=ROLES_OPTIONS, width="small"),
                    "Department": st.column_config.SelectboxColumn("Department", options=DEPARTMENTS, width="medium"),
                    "Title": st.column_config.SelectboxColumn("Title", options=TITLES, width="medium"),
                    "Password": st.column_config.TextColumn(
                        "Password", help="Type a new value to change.", width="small",
                    ),
                }

                edited_search_df = st.data_editor(
                    search_df,
                    column_config=search_column_config,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    key="search_data_editor",
                )

                save_col, del_col, _ = st.columns([1, 1, 3])
                with save_col:
                    if st.button("💾 Save Changes", key="search_save_btn", type="primary", use_container_width=True):
                        row = edited_search_df.iloc[0]
                        diff: dict = {"username": found_user["username"]}
                        has_changes = False

                        if row["Name"] != found_user.get("display_name", ""):
                            diff["display_name"] = row["Name"]
                            has_changes = True
                        if row["Role"] != found_user.get("role", "user"):
                            diff["role"] = row["Role"]
                            has_changes = True
                        if row["Department"] != found_user.get("department", ""):
                            diff["department"] = row["Department"]
                            has_changes = True
                        if row["Title"] != found_user.get("title", ""):
                            diff["title"] = row["Title"]
                            has_changes = True

                        pw_val = row.get("Password", PASSWORD_MASK)
                        if pw_val != PASSWORD_MASK and pw_val.strip():
                            diff["password"] = pw_val
                            has_changes = True

                        if not has_changes:
                            st.info("No changes detected.")
                        else:
                            updated, _, errors = batch_update_users([diff], [])
                            if errors:
                                for err in errors:
                                    st.error(err)
                            else:
                                st.toast(f"User '{found_user['username']}' updated.", icon="✅")
                            # Refresh search result to reflect changes
                            st.session_state.admin_search_result = search_user_by_username(
                                st.session_state.admin_search_query
                            )
                            st.rerun()

                with del_col:
                    if st.button("🗑️ Delete User", key="search_delete_btn", use_container_width=True):
                        ok, msg = delete_user(found_user["username"])
                        if ok:
                            st.toast(f"User '{found_user['username']}' deleted.", icon="✅")
                            # Revert to full user list
                            st.session_state.admin_search_query = ""
                            st.session_state.admin_search_active = False
                            st.session_state.admin_search_result = None
                            st.rerun()
                        else:
                            st.error(msg)

        # ══════════════════════════════════════════════
        # DEFAULT MODE: Filters + paginated batch-edit table
        # ══════════════════════════════════════════════
        else:
            # ── Filters ──
            flt_c1, flt_c2, flt_c3 = st.columns(3)
            with flt_c1:
                filter_role = st.selectbox(
                    "Filter by Role",
                    ["All"] + ROLES_OPTIONS,
                    index=(["All"] + ROLES_OPTIONS).index(st.session_state.admin_filter_role)
                    if st.session_state.admin_filter_role in (["All"] + ROLES_OPTIONS)
                    else 0,
                    key="flt_role",
                )
                if filter_role != st.session_state.admin_filter_role:
                    st.session_state.admin_filter_role = filter_role
                    st.session_state.admin_page_idx = 0
                    st.rerun()
            with flt_c2:
                filter_dept = st.selectbox(
                    "Filter by Department",
                    ["All"] + DEPARTMENTS,
                    index=(["All"] + DEPARTMENTS).index(st.session_state.admin_filter_dept)
                    if st.session_state.admin_filter_dept in (["All"] + DEPARTMENTS)
                    else 0,
                    key="flt_dept",
                )
                if filter_dept != st.session_state.admin_filter_dept:
                    st.session_state.admin_filter_dept = filter_dept
                    st.session_state.admin_page_idx = 0
                    st.rerun()
            with flt_c3:
                filter_title = st.selectbox(
                    "Filter by Title",
                    ["All"] + TITLES,
                    index=(["All"] + TITLES).index(st.session_state.admin_filter_title)
                    if st.session_state.admin_filter_title in (["All"] + TITLES)
                    else 0,
                    key="flt_title",
                )
                if filter_title != st.session_state.admin_filter_title:
                    st.session_state.admin_filter_title = filter_title
                    st.session_state.admin_page_idx = 0
                    st.rerun()

            # ── Build filtered DataFrame (with masked passwords) ──
            raw_users = get_all_users_with_passwords()

            if st.session_state.admin_filter_role != "All":
                raw_users = [u for u in raw_users if u.get("role") == st.session_state.admin_filter_role]
            if st.session_state.admin_filter_dept != "All":
                raw_users = [u for u in raw_users if u.get("department") == st.session_state.admin_filter_dept]
            if st.session_state.admin_filter_title != "All":
                raw_users = [u for u in raw_users if u.get("title") == st.session_state.admin_filter_title]

            if not raw_users:
                st.info("No users match the current filters.")
            else:
                # Pagination math
                total_filtered = len(raw_users)
                total_pages = max(1, math.ceil(total_filtered / ROWS_PER_PAGE))
                page_idx = min(st.session_state.admin_page_idx, total_pages - 1)
                start = page_idx * ROWS_PER_PAGE
                end = start + ROWS_PER_PAGE
                page_users = raw_users[start:end]

                # Build DF with masked passwords + Delete checkbox
                rows = []
                for u in page_users:
                    rows.append({
                        "Username": u["username"],
                        "Name": u.get("display_name", ""),
                        "Role": u.get("role", "user"),
                        "Department": u.get("department", ""),
                        "Title": u.get("title", ""),
                        "Password": PASSWORD_MASK,
                        "Delete?": False,
                    })
                df = pd.DataFrame(rows)

                # Column config for data_editor
                column_config = {
                    "Username": st.column_config.TextColumn(
                        "Username",
                        disabled=True,
                        width="small",
                    ),
                    "Name": st.column_config.TextColumn(
                        "Name",
                        width="medium",
                    ),
                    "Role": st.column_config.SelectboxColumn(
                        "Role",
                        options=ROLES_OPTIONS,
                        width="small",
                    ),
                    "Department": st.column_config.SelectboxColumn(
                        "Department",
                        options=DEPARTMENTS,
                        width="medium",
                    ),
                    "Title": st.column_config.SelectboxColumn(
                        "Title",
                        options=TITLES,
                        width="medium",
                    ),
                    "Password": st.column_config.TextColumn(
                        "Password",
                        help="Shows ****** by default. Type a new value to change password.",
                        width="small",
                    ),
                    "Delete?": st.column_config.CheckboxColumn(
                        "Delete?",
                        help="Check to mark user for deletion on Save.",
                        width="small",
                        default=False,
                    ),
                }

                edited_df = st.data_editor(
                    df,
                    column_config=column_config,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    key="users_data_editor",
                )

                # ── Pagination controls ──
                pag_c1, pag_c2, pag_c3, pag_c4 = st.columns([1, 2, 2, 1])
                with pag_c1:
                    if st.button("◀ Previous", key="page_prev", disabled=(page_idx == 0)):
                        st.session_state.admin_page_idx = max(0, page_idx - 1)
                        st.rerun()
                with pag_c2:
                    st.markdown(
                        f'<div style="text-align:center;font-size:0.82rem;color:{TEXT2};padding-top:0.4rem;">'
                        f'Page {page_idx + 1} of {total_pages}  ·  {total_filtered} users</div>',
                        unsafe_allow_html=True,
                    )
                with pag_c3:
                    pass  # spacer
                with pag_c4:
                    if st.button("Next ▶", key="page_next", disabled=(page_idx >= total_pages - 1)):
                        st.session_state.admin_page_idx = min(total_pages - 1, page_idx + 1)
                        st.rerun()

                # ── Batch Save button ──
                st.markdown("---")
                if st.button("💾  Save Changes", key="batch_save_btn", type="primary", use_container_width=True):
                    updates: list[dict] = []
                    deletes: list[str] = []

                    for i, row in edited_df.iterrows():
                        original = page_users[i]
                        uname = original["username"]

                        if row.get("Delete?", False):
                            deletes.append(uname)
                            continue

                        diff: dict = {"username": uname}
                        has_changes = False

                        if row["Name"] != original.get("display_name", ""):
                            diff["display_name"] = row["Name"]
                            has_changes = True
                        if row["Role"] != original.get("role", "user"):
                            diff["role"] = row["Role"]
                            has_changes = True
                        if row["Department"] != original.get("department", ""):
                            diff["department"] = row["Department"]
                            has_changes = True
                        if row["Title"] != original.get("title", ""):
                            diff["title"] = row["Title"]
                            has_changes = True

                        pw_val = row.get("Password", PASSWORD_MASK)
                        if pw_val != PASSWORD_MASK and pw_val.strip():
                            diff["password"] = pw_val
                            has_changes = True

                        if has_changes:
                            updates.append(diff)

                    if not updates and not deletes:
                        st.info("No changes detected.")
                    else:
                        updated, deleted, errors = batch_update_users(updates, deletes)
                        if errors:
                            for err in errors:
                                st.error(err)
                        summary_parts = []
                        if updated:
                            summary_parts.append(f"{updated} updated")
                        if deleted:
                            summary_parts.append(f"{deleted} deleted")
                        if summary_parts:
                            st.toast(", ".join(summary_parts), icon="✅")
                        st.rerun()

# ─────────────────────────────────────────────
# RIGHT: Create User form + API Contract status
# ─────────────────────────────────────────────
with col_form:
    with st.container(border=True, key="admin_create_panel"):
        st.markdown(
            '<div class="admin-panel-header">➕ Create New User</div>',
            unsafe_allow_html=True,
        )

        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input("Username *", placeholder="e.g. jdoe")
            new_password = st.text_input("Password *", type="password", placeholder="Set a password")
            new_confirm_password = st.text_input(
                "Confirm Password *", type="password", placeholder="Re-enter password"
            )
            new_display = st.text_input("Display Name *", placeholder="e.g. Jane Doe")
            new_role = st.selectbox("Role *", ROLES_OPTIONS, index=1)
            new_dept = st.selectbox("Department *", DEPARTMENTS, index=0)
            new_title = st.selectbox("Title *", TITLES, index=1)

            create_submitted = st.form_submit_button(
                "Create Account", type="primary", use_container_width=True
            )

            if create_submitted:
                # Validation
                if not new_username.strip() or not new_password.strip() or not new_display.strip():
                    st.error("Username, password, and display name are required.")
                elif new_password != new_confirm_password:
                    st.markdown(
                        '<span class="pw-mismatch">⚠ Passwords do not match.</span>',
                        unsafe_allow_html=True,
                    )
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

    # ── API Contract Status panel ──
    with st.container(border=True, key="admin_contract_panel"):
        st.markdown(
            '<div class="admin-panel-header">📋 API Contract Status</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"""
        <div style="font-size:0.8rem;color:{TEXT2};line-height:1.6;">
            <b>Backend endpoints needed:</b><br>
            ⬜ <code>POST /auth/login</code> — Authentication<br>
            ⬜ <code>GET /admin/users</code> — List / Search users<br>
            ⬜ <code>POST /admin/users</code> — Create user<br>
            ⬜ <code>DELETE /admin/users/{'{'}username{'}'}</code> — Delete user<br>
            ⬜ <code>PATCH /admin/users/batch</code> — Batch update + delete<br>
            ⬜ <code>POST /chat</code> — Chat with attachment<br>
            ⬜ <code>POST /integrations/slack/connect</code> — Slack<br>
            <br>
            <em>See <code>API_CONTRACT.md</code> for full specifications.</em>
        </div>
        """, unsafe_allow_html=True)
