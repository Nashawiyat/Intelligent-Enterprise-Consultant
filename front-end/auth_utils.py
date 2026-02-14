"""
ICA – Authentication Utilities
================================
Real backend integration with mock fallback for demo resilience.
Backend endpoints: POST /auth/login, GET /admin/users, POST /admin/users,
DELETE /admin/users/{username}, PATCH /admin/users/batch,
POST /context/upload, POST /integrations/slack/connect.

See API_CONTRACT.md for the expected JSON payloads.
"""

import streamlit as st
import requests
import uuid
from datetime import datetime


# ──────────────────────────────────────────────
# Backend config
# ──────────────────────────────────────────────
try:
    BACKEND_BASE_URL = st.secrets["BACKEND_URL"]
except Exception:
    BACKEND_BASE_URL = "http://localhost:8000"


def _get_auth_headers() -> dict:
    """Return headers dict with session-token for authenticated backend calls."""
    token = st.session_state.get("auth_token")
    if token:
        return {"session-token": token}
    return {}


def _normalize_backend_user(user_dict: dict) -> dict:
    """
    Normalize a user dict from the backend to the frontend's internal naming.

    Backend DB columns: mode (admin/user), role (job title).
    Backend returns:    {username, display_name, mode, role, department}.
    Frontend uses:      {username, display_name, role (admin/user), title (job title), department}.
    """
    out = dict(user_dict)
    if "mode" in out:
        backend_mode = out.pop("mode")          # "admin" or "user"
        backend_role = out.pop("role", "")       # job title like "Admin", "CEO"
        out["role"] = backend_mode               # frontend 'role' = permission level
        out["title"] = backend_role              # frontend 'title' = job title
    out.setdefault("title", "")
    return out


# ──────────────────────────────────────────────
# Hardcoded demo credentials (mock DB fallback)
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
    Login: tries the real backend POST /auth/login first.
    Falls back to mock session_state.users_db if the backend is unreachable.
    Returns True on success.
    """
    init_auth_state()

    # ── Try real backend first ──
    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            if "token" in data and "user" in data:
                user = _normalize_backend_user(data["user"])
                st.session_state.authenticated = True
                st.session_state.auth_token = data["token"]
                st.session_state.current_user = {
                    "username": user.get("username", username),
                    "display_name": user.get("display_name", username),
                    "role": user.get("role", "user"),
                    "department": user.get("department", ""),
                    "title": user.get("title", ""),
                }
                st.session_state.login_error = None
                _sync_user_to_local_db(st.session_state.current_user)
                return True

        # Non-200 response (401, etc.)
        try:
            data = resp.json()
            st.session_state.login_error = data.get("detail", "Invalid username or password.")
        except Exception:
            st.session_state.login_error = f"Login failed (HTTP {resp.status_code})"
        return False

    except requests.exceptions.ConnectionError:
        # Backend unreachable — fall back to mock
        pass
    except Exception:
        # Any other error — fall back to mock
        pass

    # ── Fallback: mock login against session_state.users_db ──
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


def _sync_user_to_local_db(user: dict):
    """Add/update user in local session DB so admin page reflects backend users."""
    init_auth_state()
    for u in st.session_state.users_db:
        if u["username"] == user["username"]:
            u.update({k: v for k, v in user.items() if k != "password"})
            return
    # Not found locally — add without password
    st.session_state.users_db.append({**user, "password": ""})


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
    """Return user list (without passwords). Tries GET /admin/users first."""
    init_auth_state()

    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/admin/users",
            headers=_get_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("users", [])
            return [_normalize_backend_user(u) for u in users]
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback to local session DB
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
    Create a new user. Tries real backend POST /admin/users first,
    falls back to mock session_state DB if backend is unreachable.

    Frontend params: role = admin/user, title = job title.
    Backend expects:  mode = admin/user, role  = job title.
    """
    init_auth_state()

    # ── Try real backend first ──
    try:
        payload = {
            "username": username,
            "password": password,
            "display_name": display_name,
            "mode": role,          # frontend 'role' → backend 'mode'
            "department": department,
            "role": title,          # frontend 'title' → backend 'role'
        }
        resp = requests.post(
            f"{BACKEND_BASE_URL}/admin/users",
            json=payload,
            headers=_get_auth_headers(),
            timeout=10,
        )
        data = resp.json()

        if resp.status_code in (200, 201):
            # Also add to local DB so the admin page reflects it immediately
            new_user = {
                "username": username,
                "password": password,
                "display_name": display_name,
                "role": role,
                "department": department,
                "title": title,
            }
            # Avoid duplicates
            if not any(u["username"] == username for u in st.session_state.users_db):
                st.session_state.users_db.append(new_user)
            msg = data.get("detail", data.get("message", f"User '{username}' created successfully."))
            return True, msg
        else:
            detail = data.get("detail", f"Backend error ({resp.status_code})")
            return False, detail

    except requests.exceptions.ConnectionError:
        pass  # Fall back to mock
    except Exception:
        pass  # Fall back to mock

    # ── Fallback: mock create in session_state ──
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
    """Delete a user. Tries DELETE /admin/users/{username} first."""
    init_auth_state()

    try:
        resp = requests.delete(
            f"{BACKEND_BASE_URL}/admin/users/{username}",
            headers=_get_auth_headers(),
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200:
            # Also remove from local session DB
            st.session_state.users_db = [
                u for u in st.session_state.users_db if u["username"] != username
            ]
            return True, data.get("detail", f"User '{username}' deleted.")
        return False, data.get("detail", f"Backend error ({resp.status_code})")
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback to local mock DB
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
    """
    Return full user list for admin data_editor.
    Backend never returns real passwords — we use PASSWORD_MASK.
    """
    init_auth_state()

    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/admin/users",
            headers=_get_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            users = []
            for u in data.get("users", []):
                nu = _normalize_backend_user(u)
                nu["password"] = PASSWORD_MASK
                users.append(nu)
            return users
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback
    return [dict(u) for u in st.session_state.users_db]


def search_user_by_username(username: str) -> list[dict]:
    """
    Search for a user by username. Tries GET /admin/users?search_username=.
    Returns list of matching users (with PASSWORD_MASK for passwords).
    """
    init_auth_state()

    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/admin/users",
            params={"search_username": username},
            headers=_get_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            users = []
            for u in data.get("users", []):
                nu = _normalize_backend_user(u)
                nu["password"] = PASSWORD_MASK
                users.append(nu)
            return users
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback to local mock
    target = username.lower()
    for u in st.session_state.users_db:
        if u["username"].lower() == target:
            return [dict(u)]
    return []


PASSWORD_MASK = "******"


def batch_update_users(
    updates: list[dict],
    deletes: list[str],
) -> tuple[int, int, list[str]]:
    """
    Apply batch edits + deletes. Tries PATCH /admin/users/batch first.
    `updates` – list of dicts with at least "username" and any changed fields.
                Password field: value == PASSWORD_MASK means *unchanged*.
    `deletes` – list of usernames to remove.
    Returns (updated_count, deleted_count, errors).
    """
    init_auth_state()

    # Build backend-compatible payload
    backend_updates = []
    for upd in updates:
        item = {"username": upd["username"]}
        if "display_name" in upd:
            item["display_name"] = upd["display_name"]
        if "role" in upd:
            item["mode"] = upd["role"]        # frontend role → backend mode
        if "department" in upd:
            item["department"] = upd["department"]
        if "title" in upd:
            item["role"] = upd["title"]       # frontend title → backend role
        pw = upd.get("password", PASSWORD_MASK)
        if pw != PASSWORD_MASK and pw.strip():
            item["password"] = pw
        backend_updates.append(item)

    try:
        resp = requests.patch(
            f"{BACKEND_BASE_URL}/admin/users/batch",
            json={"updates": backend_updates, "deletes": deletes},
            headers=_get_auth_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            updated_count = len(data.get("updated", []))
            deleted_count = len(data.get("deleted", []))
            errors = data.get("errors", [])
            # Sync local session DB: remove deleted users
            for uname in data.get("deleted", []):
                st.session_state.users_db = [
                    u for u in st.session_state.users_db if u["username"] != uname
                ]
            return updated_count, deleted_count, errors
        else:
            detail = "Backend error"
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            return 0, 0, [f"{detail} ({resp.status_code})"]
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # ── Fallback: local mock ──
    errors: list[str] = []
    updated = 0
    deleted = 0

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
    Upload a context file. Tries POST /context/upload first.
    Falls back to local mock if backend is down.
    """
    init_context_state()

    try:
        files = {"file": (file_name, file_bytes)}
        resp = requests.post(
            f"{BACKEND_BASE_URL}/context/upload",
            files=files,
            headers=_get_auth_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            entry = {
                "file_id": uuid.uuid4().hex[:8],
                "filename": data.get("filename", file_name),
                "domain": domain,
                "description": description,
                "size_kb": round(data.get("size", len(file_bytes)) / 1024, 1),
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "processed",
            }
            st.session_state.uploaded_files.append(entry)
            return entry
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback: local mock
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
    Connect Slack integration. Tries POST /integrations/slack/connect first.
    """
    init_slack_state()

    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/integrations/slack/connect",
            json={"webhook_url": webhook_url},
            headers=_get_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            st.session_state.slack_connected = True
            st.session_state.slack_config = {
                "webhook_url": webhook_url,
                "channel": channel,
                "notify_on": notify_on,
                "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            return {"status": "connected", "channel": channel}
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    # Fallback: local mock
    st.session_state.slack_connected = True
    st.session_state.slack_config = {
        "webhook_url": webhook_url,
        "channel": channel,
        "notify_on": notify_on,
        "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return {"status": "connected", "channel": channel}
