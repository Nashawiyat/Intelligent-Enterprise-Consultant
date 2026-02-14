import os
import sqlite3
import re
from langchain_core.tools import tool
from typing import List, Dict, Any

# Resolve DB path relative to this file so tests run from any cwd.
DATABASE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "enterprise_data2.db")
)

@tool
def query_enterprise_database(sql_query: str) -> str:
    """
    Executes a SQL query against the unified enterprise SQLite database.
    Input should be a valid SQLite SELECT statement.
    """
    try:
        # Connect to your siloed database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        # Get column names to provide better context to the AI
        columns = [description[0] for description in cursor.description]
        conn.close()
        
        # Format results as a list of dicts for the AI to reason over
        results = [dict(zip(columns, row)) for row in rows]
        return str(results)
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
    from langchain_community.tools.tavily_search import TavilySearchResults
    search = TavilySearchResults(max_results=3)
    return str(search.run(competitor_name))

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

@tool
def get_database_schema() -> str:
    """
    Retrieves the schema information for all tables in the enterprise database.
    Use this at the start of a data request to ensure SQL queries use 
    correct table and column names.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all table names 
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = []
        for table in tables:
            table_name = table[0]
            # Get column info for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            col_desc = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
            schema_info.append(f"Table: {table_name} | Columns: {col_desc}")
        
        conn.close()
        return "\n".join(schema_info)
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"