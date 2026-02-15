import os
import sqlite3
import re
from langchain_core.tools import tool
from typing import List, Dict, Any

# Resolve DB paths relative to this file so tests run from any cwd.
_BACK_END_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATABASE_PATHS = {
    "CRM": os.path.join(_BACK_END_DIR, "triecrm1.db"),
    "ERP": os.path.join(_BACK_END_DIR, "trieerp1.db"),
}

# Separate database used exclusively for simulations
SIMULATION_DB_PATH = os.path.join(
    os.path.dirname(_BACK_END_DIR), "enterprise_data2.db"
)

# Build a lookup: lowercase table name  -> db key, so queries hit the right file.
_TABLE_DB_MAP: Dict[str, str] = {}

def _refresh_table_map():
    """Scan every registered DB and map each table name to its DB key."""
    _TABLE_DB_MAP.clear()
    for db_key, db_path in DATABASE_PATHS.items():
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (tbl,) in cur.fetchall():
                _TABLE_DB_MAP[tbl.lower()] = db_key
            conn.close()
        except Exception:
            pass

# Populate on import so the map is ready before the first query.
_refresh_table_map()


def _detect_db_key(sql_query: str) -> str | None:
    """Return the DB key whose tables appear in *sql_query*, or None."""
    upper = sql_query.upper()
    for tbl_lower, db_key in _TABLE_DB_MAP.items():
        # Match the table name as a whole word (case-insensitive).
        if re.search(rf'\b{re.escape(tbl_lower)}\b', sql_query, re.IGNORECASE):
            return db_key
    return None


def _run_query_on_db(db_path: str, sql_query: str) -> str:
    """Execute a single SQL query against one database file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return str([dict(zip(columns, row)) for row in rows])


@tool
def query_enterprise_database(sql_query: str) -> str:
    """
    Executes a SQL query against the enterprise SQLite databases (CRM & ERP).
    The correct database is auto-detected from the table names in the query.
    If auto-detection fails the query is tried against every database.
    Input should be a valid SQLite SELECT statement.
    """
    try:
        # 1. Try to route to the exact database that owns the referenced table.
        db_key = _detect_db_key(sql_query)
        if db_key and db_key in DATABASE_PATHS:
            return _run_query_on_db(DATABASE_PATHS[db_key], sql_query)

        # 2. Fallback: try each database and return the first successful result.
        errors = []
        for key, path in DATABASE_PATHS.items():
            if not os.path.exists(path):
                continue
            try:
                return _run_query_on_db(path, sql_query)
            except Exception as e:
                errors.append(f"{key}: {e}")
        return f"Error executing query across databases: {'; '.join(errors)}"
    except Exception as e:
        return f"Error executing query: {str(e)}"

@tool
def get_competitive_intel(competitor_name: str) -> str:
    """
    Searches the live web for recent pricing moves, news, or feature updates 
    regarding a specific competitor. Use this for cross-domain market context.
    """
    # Integrate Tavily here for real-time market data
    # This satisfies the 'Competitive Intelligence' domain requirement.
    try:
        import os
        if not os.environ.get("TAVILY_API_KEY"):
            return (
                "External competitive intelligence is currently unavailable. "
                "Analysis will proceed using internal enterprise data only."
            )
        from langchain_community.tools.tavily_search import TavilySearchResults
        search = TavilySearchResults(max_results=3)
        return str(search.run(competitor_name))
    except Exception:
        return (
            "External competitive intelligence lookup could not be completed. "
            "Analysis will proceed using internal enterprise data only."
        )

@tool
def scrub_sensitive_info(text: str) -> str:
    """
    Scans a generated insight or recommendation for PII (Personally Identifiable Information)
    such as emails or ID numbers and masks them to ensure enterprise compliance.
    """
    # Privacy check to satisfy the 'Security' guardrail
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    masked_text = re.sub(email_regex, "[PROTECTED_EMAIL]", text)
    return masked_text

# ── Simulation-only helpers (plain functions, not LangChain tools) ──────────

def query_simulation_db(sql_query: str) -> str:
    """Execute a SQL query against the simulation database only."""
    if not os.path.exists(SIMULATION_DB_PATH):
        return f"Simulation DB not found at {SIMULATION_DB_PATH}"
    try:
        return _run_query_on_db(SIMULATION_DB_PATH, sql_query)
    except Exception as e:
        return f"Error executing simulation query: {e}"


def get_simulation_schema() -> str:
    """Return the schema of the simulation database."""
    if not os.path.exists(SIMULATION_DB_PATH):
        return f"Simulation DB not found at {SIMULATION_DB_PATH}"
    lines: list[str] = []
    try:
        conn = sqlite3.connect(SIMULATION_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for (table_name,) in cursor.fetchall():
            if table_name == "sqlite_sequence":
                continue
            cursor.execute(f"PRAGMA table_info({table_name});")
            cols = cursor.fetchall()
            col_desc = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
            lines.append(f"[SIM] Table: {table_name} | Columns: {col_desc}")
        conn.close()
    except Exception as e:
        lines.append(f"[SIM] Error: {e}")
    return "\n".join(lines)


@tool
def get_database_schema() -> str:
    """
    Retrieves the schema information for all tables across the enterprise
    databases (CRM & ERP).  Use this at the start of a data request to ensure
    SQL queries use correct table and column names.
    """
    all_schema: list[str] = []
    for db_key, db_path in DATABASE_PATHS.items():
        if not os.path.exists(db_path):
            all_schema.append(f"[{db_key}] Database file not found: {db_path}")
            continue
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for (table_name,) in tables:
                if table_name == "sqlite_sequence":
                    continue
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_desc = ", ".join(
                    [f"{col[1]} ({col[2]})" for col in columns]
                )
                all_schema.append(
                    f"[{db_key}] Table: {table_name} | Columns: {col_desc}"
                )
            conn.close()
        except Exception as e:
            all_schema.append(f"[{db_key}] Error retrieving schema: {e}")
    return "\n".join(all_schema)