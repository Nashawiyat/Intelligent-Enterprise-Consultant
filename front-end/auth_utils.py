"""
ICA – Authentication Utilities
================================
Mocked auth logic for demo. Will be replaced with real API calls
once the backend implements POST /auth/login, GET/POST /admin/users.

See API_CONTRACT.md for the expected JSON payloads.
"""

import streamlit as st
import uuid
from datetime import datetime


# ──────────────────────────────────────────────
# Hardcoded demo credentials (mock DB)
# ──────────────────────────────────────────────
DEFAULT_USERS = [
    {
        "username": "admin",
        "password": "admin",
        "display_name": "System Admin",
        "role": "admin",
        "department": "IT",
        "title": "Admin",
    },
    {
        "username": "user",
        "password": "user",
        "display_name": "Alex Morgan",
        "role": "user",
        "department": "Executive",
        "title": "CEO",
    },
    {
        "username": "cfo",
        "password": "cfo",
        "display_name": "Jordan Lee",
        "role": "user",
        "department": "Finance",
        "title": "CFO",
    },
    {
        "username": "cto",
        "password": "cto",
        "display_name": "Sam Rivera",
        "role": "user",
        "department": "Engineering",
        "title": "CTO",
    },
]


# ──────────────────────────────────────────────
# Session helpers
# ──────────────────────────────────────────────
def init_auth_state():
    """Ensure all auth-related session keys exist."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "users_db" not in st.session_state:
        # Deep-copy default users so mutations don't affect the module constant
        st.session_state.users_db = [dict(u) for u in DEFAULT_USERS]
    if "login_error" not in st.session_state:
        st.session_state.login_error = None


def is_authenticated() -> bool:
    init_auth_state()
    return st.session_state.authenticated


def is_admin() -> bool:
    if not is_authenticated():
        return False
    user = st.session_state.current_user
    return user is not None and user.get("role") == "admin"


def get_current_user() -> dict | None:
    init_auth_state()
    return st.session_state.current_user


# ──────────────────────────────────────────────
# Login / Logout (mocked)
# ──────────────────────────────────────────────
def mock_login(username: str, password: str) -> bool:
    """
    Mock login: checks credentials against session_state.users_db.
    In production, this will call POST /auth/login.
    Returns True on success.
    """
    init_auth_state()
    for user in st.session_state.users_db:
        if user["username"] == username and user["password"] == password:
            st.session_state.authenticated = True
            st.session_state.auth_token = f"mock-token-{uuid.uuid4().hex[:12]}"
            st.session_state.current_user = {
                "username": user["username"],
                "display_name": user["display_name"],
                "role": user["role"],
                "department": user["department"],
                "title": user["title"],
            }
            st.session_state.login_error = None
            return True
    st.session_state.login_error = "Invalid username or password."
    return False


def logout():
    """Clear auth state."""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.auth_token = None
    st.session_state.login_error = None


# ──────────────────────────────────────────────
# User management (mocked, admin-only)
# ──────────────────────────────────────────────
def get_all_users() -> list[dict]:
    """Return user list (without passwords)."""
    init_auth_state()
    return [
        {k: v for k, v in u.items() if k != "password"}
        for u in st.session_state.users_db
    ]


def create_user(
    username: str,
    password: str,
    display_name: str,
    role: str,
    department: str,
    title: str,
) -> tuple[bool, str]:
    """
    Create a new user in the mock DB.
    Returns (success: bool, message: str).
    """
    init_auth_state()
    # Check duplicates
    for u in st.session_state.users_db:
        if u["username"] == username:
            return False, f"Username '{username}' already exists."

    new_user = {
        "username": username,
        "password": password,
        "display_name": display_name,
        "role": role,
        "department": department,
        "title": title,
    }
    st.session_state.users_db.append(new_user)
    return True, f"User '{username}' created successfully."


def delete_user(username: str) -> tuple[bool, str]:
    """Delete a user from the mock DB."""
    init_auth_state()
    if username == "admin":
        return False, "Cannot delete the default admin account."
    before = len(st.session_state.users_db)
    st.session_state.users_db = [
        u for u in st.session_state.users_db if u["username"] != username
    ]
    if len(st.session_state.users_db) < before:
        return True, f"User '{username}' deleted."
    return False, f"User '{username}' not found."


def get_all_users_with_passwords() -> list[dict]:
    """Return full user list *including* passwords (admin-only, for data_editor)."""
    init_auth_state()
    return [dict(u) for u in st.session_state.users_db]


PASSWORD_MASK = "******"


def batch_update_users(
    updates: list[dict],
    deletes: list[str],
) -> tuple[int, int, list[str]]:
    """
    Apply batch edits + deletes to st.session_state.users_db.
    `updates` – list of dicts with at least "username" and any changed fields.
                Password field: value == PASSWORD_MASK means *unchanged*.
    `deletes` – list of usernames to remove.
    Returns (updated_count, deleted_count, errors).
    In production this calls PATCH /admin/users/batch.
    """
    init_auth_state()
    errors: list[str] = []
    updated = 0
    deleted = 0

    # --- Deletes ---
    protected = {"admin"}
    for uname in deletes:
        if uname in protected:
            errors.append(f"Cannot delete protected account '{uname}'.")
            continue
        before = len(st.session_state.users_db)
        st.session_state.users_db = [
            u for u in st.session_state.users_db if u["username"] != uname
        ]
        if len(st.session_state.users_db) < before:
            deleted += 1
        else:
            errors.append(f"User '{uname}' not found for deletion.")

    # --- Updates ---
    user_map = {u["username"]: u for u in st.session_state.users_db}
    for upd in updates:
        uname = upd.get("username")
        if not uname or uname not in user_map:
            errors.append(f"User '{uname}' not found for update.")
            continue
        target = user_map[uname]
        changed = False
        for field in ("display_name", "role", "department", "title"):
            if field in upd and upd[field] != target.get(field):
                target[field] = upd[field]
                changed = True
        # Password: only update if not masked
        pw = upd.get("password", PASSWORD_MASK)
        if pw != PASSWORD_MASK and pw.strip():
            target["password"] = pw
            changed = True
        if changed:
            updated += 1

    return updated, deleted, errors


# ──────────────────────────────────────────────
# Context upload (mocked)
# ──────────────────────────────────────────────
def init_context_state():
    """Ensure context-upload session keys exist."""
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []


def mock_upload_context(file_name: str, file_bytes: bytes, domain: str, description: str = "") -> dict:
    """
    Mock file upload; stores metadata in session_state.
    In production, this calls POST /context/upload (multipart).
    """
    init_context_state()
    entry = {
        "file_id": uuid.uuid4().hex[:8],
        "filename": file_name,
        "domain": domain,
        "description": description,
        "size_kb": round(len(file_bytes) / 1024, 1),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "processed",
    }
    st.session_state.uploaded_files.append(entry)
    return entry


# ──────────────────────────────────────────────
# Slack integration (mocked)
# ──────────────────────────────────────────────
def init_slack_state():
    if "slack_connected" not in st.session_state:
        st.session_state.slack_connected = False
    if "slack_config" not in st.session_state:
        st.session_state.slack_config = None


def mock_connect_slack(webhook_url: str, channel: str, notify_on: str = "high_urgency") -> dict:
    """
    Mock Slack connection.
    In production, calls POST /integrations/slack/connect.
    """
    init_slack_state()
    st.session_state.slack_connected = True
    st.session_state.slack_config = {
        "webhook_url": webhook_url,
        "channel": channel,
        "notify_on": notify_on,
        "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return {"status": "connected", "channel": channel}
