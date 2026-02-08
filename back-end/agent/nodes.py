from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from .state import AgentState
from .tools import query_enterprise_database, get_competitive_intel, get_database_schema
import ast
import re
import json

# LLM initialization
llm_smart = ChatGroq(model="llama-3.3-70b-versatile")
llm_fast = ChatGroq(model="llama-3.1-8b-instant")
tools = [query_enterprise_database, get_competitive_intel, get_database_schema]
llm_with_tools = llm_fast.bind_tools(tools)

ALLOWED_SILOS = ["Sales", "Operations", "HR", "Accounting", "CRM"]
SILO_INSTRUCTIONS = {
    "Sales": "Focus on pipeline, conversion, CAC, and LTV.",
    "Operations": "Focus on latency, throughput, uptime, and bottleneck.",
    "HR": "Focus on churn, headcount, payroll, and productivity.",
    "Accounting": "Focus on EBITDA, margin, overhead, and liability.",
    "CRM": "Focus on sentiment, retention, support tickets, and NPS."
}
SILO_FOCUS_MAP = {
    "Sales": "pipeline, conversion, CAC, LTV",
    "Operations": "latency, throughput, uptime, bottleneck",
    "Accounting": "EBITDA, margin, overhead, liability",
    "HR": "churn, headcount, payroll, productivity",
    "CRM": "sentiment, retention, support tickets, NPS"
}

def orchestrator_node(state: AgentState):
    user_role = state.get("role", "Analyst")

    last_message = state["messages"][-1]
    
    if isinstance(last_message, tuple):
        user_message = last_message[1]
    else:
        user_message = last_message.content

    # Check if external competitive intelligence is needed
    if "competitor" in user_message.lower() or "market" in user_message.lower():
        intel = get_competitive_intel.invoke({"competitor_name": "Market Leaders"})
        external_context = intel
    else:
        external_context = ""

    return {
        "current_silo": "Determined by LLM", 
        "external_context": external_context,
        "reasoning_steps": [f"Orchestrator identified need for {user_role} domain data."]
    }

def get_message_content(msg):
    """Helper to safely extract content from a tuple or BaseMessage object."""
    if isinstance(msg, tuple):
        return msg[1]
    return msg.content

def normalize_silos(raw_silos):
    if not raw_silos:
        return ["Operations"]
    normalized = []
    for silo in raw_silos:
        if not silo:
            continue
        silo_clean = str(silo).strip().lower()
        if silo_clean in ["it", "tech", "technology"]:
            normalized.append("Operations")
        elif silo_clean in ["finance", "accounting"]:
            normalized.append("Accounting")
        elif silo_clean in ["hr", "people", "human resources"]:
            normalized.append("HR")
        elif silo_clean in ["sales", "revenue"]:
            normalized.append("Sales")
        elif silo_clean in ["crm", "customer", "customer success"]:
            normalized.append("CRM")
    if not normalized:
        normalized = ["Operations"]
    filtered = [s for s in normalized if s in ALLOWED_SILOS]
    return list(dict.fromkeys(filtered)) or ["Operations"]

def infer_target_silos(text: str) -> list:
    if not text:
        return []
    content = text.lower()
    inferred = []
    if "latency" in content or "success_rate" in content or "uptime" in content:
        inferred.append("Operations")
    if "revenue" in content or "margin" in content or "cash flow" in content:
        inferred.append("Accounting")
    if "churn" in content or "satisfaction" in content:
        inferred.extend(["CRM", "Sales"])
    return infer_only_allowed(inferred)

def infer_only_allowed(silos: list) -> list:
    filtered = [s for s in silos if s in ALLOWED_SILOS]
    return list(dict.fromkeys(filtered))

def should_query_trend(user_msg: str) -> bool:
    msg = (user_msg or "").lower()
    keywords = ["health check", "healthcheck", "anomaly", "trend", "correlation", "cross-domain", "cross domain"]
    return any(k in msg for k in keywords)

def merge_sql_results(previous: str, current: str) -> str:
    prev = (previous or "").strip()
    curr = (current or "").strip()
    if not prev or prev == "No data found.":
        return curr or "No data found."
    if not curr or curr == "No data found.":
        return prev
    return f"PREVIOUS SQL RESULTS:\n{prev}\n\nCURRENT SQL RESULTS:\n{curr}"

def extract_dates(text: str) -> list:
    if not text:
        return []
    return sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)))

def extract_table_names(schema: str) -> list:
    if not schema:
        return []
    matches = re.findall(r"Table:\s*([^|]+)\|", schema)
    return [m.strip() for m in matches if m.strip()]

def is_sql_error(result: str) -> bool:
    return bool(result) and result.startswith("Error executing query:")

def retry_simple_query(schema: str, keywords: list[str]) -> str:
    table_names = extract_table_names(schema)
    if not table_names:
        return "Data Unavailable"
    candidates = [t for t in table_names if any(k in t.lower() for k in keywords)]
    if not candidates:
        candidates = table_names[:1]
    for table in candidates:
        attempt = query_enterprise_database.invoke({"sql_query": f"SELECT * FROM {table} LIMIT 10;"})
        if not is_sql_error(attempt):
            return attempt
    return "Data Unavailable"

def normalize_price_change(value: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if abs(numeric) > 1:
        return numeric / 100.0
    return numeric

def extract_baseline_revenue(sql_text: str) -> float | None:
    if not sql_text:
        return None
    try:
        parsed = ast.literal_eval(sql_text)
        if isinstance(parsed, list):
            for row in parsed:
                if isinstance(row, dict):
                    for key in row.keys():
                        if "revenue" in str(key).lower():
                            try:
                                return float(row[key])
                            except (TypeError, ValueError):
                                continue
    except (ValueError, SyntaxError):
        pass
    revenue_match = re.search(r"revenue\s*[:=]\s*([\d,]+\.?\d*)", sql_text, re.IGNORECASE)
    if revenue_match:
        return float(revenue_match.group(1).replace(",", ""))
    return None

def extract_latest_revenue(sql_text: str) -> float | None:
    if not sql_text:
        return None
    try:
        parsed = ast.literal_eval(sql_text)
        if isinstance(parsed, list):
            dated_rows = []
            fallback_values = []
            for row in parsed:
                if not isinstance(row, dict):
                    continue
                date_key = None
                revenue_key = None
                for key in row.keys():
                    key_lower = str(key).lower()
                    if "date" in key_lower:
                        date_key = key
                    if "revenue" in key_lower:
                        revenue_key = key
                if revenue_key is not None:
                    try:
                        value = float(row[revenue_key])
                    except (TypeError, ValueError):
                        continue
                    if date_key is not None and row.get(date_key):
                        dated_rows.append((str(row[date_key]), value))
                    else:
                        fallback_values.append(value)
            if dated_rows:
                dated_rows.sort(key=lambda item: item[0])
                return dated_rows[-1][1]
            if fallback_values:
                return fallback_values[-1]
    except (ValueError, SyntaxError):
        pass
    return extract_baseline_revenue(sql_text)

def clean_llm_json(text: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    return cleaned.strip()

def has_extreme_percentage(text: str, threshold: float = 1000.0) -> bool:
    if not text:
        return False
    for match in re.findall(r"(\d+(?:\.\d+)?)%", text):
        try:
            if float(match) > threshold:
                return True
        except ValueError:
            continue
    return False

def sql_agent_node(state: AgentState):
    schema = get_database_schema.invoke({})
    user_msg = get_message_content(state["messages"][-1])
    trend_required = should_query_trend(user_msg)
    retry_mode = state.get("sql_retry_mode")
    trend_instruction = ""
    if trend_required:
        trend_instruction = (
            "TREND REQUIREMENT: For health checks or anomaly detection, query the last 10 records "
            "from ALL relevant finance and operations tables, ordered by date DESC, and include dates.\n"
        )
    if retry_mode == "history_7d":
        trend_instruction = (
            "RETRY MODE: Query the full 7-day history across Finance and Operations tables, "
            "ordered by date ASC, and include dates.\n"
        )
    query_prompt = SystemMessage(
        content=(
            "Output ONLY the raw tool call for 'query_enterprise_database'. "
            "No explanation, no tags, no markdown.\n"
            "QUERY GOAL: Retrieve time-series data with explicit date ordering.\n"
            "TRIANGULATION: Include metrics from at least two silos (Operations and Accounting) when possible.\n"
            f"{trend_instruction}"
            f"SCHEMA: {schema}\n"
            f"REQUEST: {user_msg}"
        )
    )

    results = "No data found."
    try:
        response = llm_with_tools.invoke([query_prompt])
        if getattr(response, "tool_calls", None):
            tool_args = response.tool_calls[0].get("args", {})
            results = query_enterprise_database.invoke(tool_args)
        else:
            # Regex fallback for 8B model reliability
            query = re.search(r"SELECT\s+.*?\s+FROM\s+.*?(;|$)", response.content, re.IGNORECASE | re.DOTALL)
            if query:
                results = query_enterprise_database.invoke({"sql_query": query.group(0).strip()})
    except Exception:
        # Ensure state integrity even if the LLM call fails
        results = "No data found."
    if is_sql_error(results):
        results = retry_simple_query(schema, ["finance", "account", "ops", "operation"])
    if is_sql_error(results):
        results = "Data Unavailable"
    previous_results = state.get("sql_results")
    if results == "Data Unavailable" and previous_results:
        merged_results = previous_results
    else:
        merged_results = merge_sql_results(previous_results, str(results))

    return {
        "sql_results": merged_results,
        "sql_retry_mode": None,
        "reasoning_steps": ["SQL node retrieved specific domain data."]
    }

def simulation_specialist_node(state: AgentState):
    schema = get_database_schema.invoke({})
    if state.get("messages"):
        user_msg = get_message_content(state["messages"][-1])
    else:
        user_msg = "Use simulation inputs to build a baseline query for the most relevant metrics."
    simulation_inputs = state.get("simulation_inputs", {})
    query_prompt = SystemMessage(
        content=(
            "Output ONLY the raw tool call for 'query_enterprise_database'. "
            "No explanation, no tags, no markdown.\n"
            "QUERY GOAL: Retrieve time-series baseline data for the most relevant tables and metrics.\n"
            f"SCHEMA: {schema}\n"
            f"REQUEST: {user_msg}"
        )
    )
    response = llm_with_tools.invoke([query_prompt])
    
    if response.tool_calls:
        results = query_enterprise_database.invoke(response.tool_calls[0]["args"])
    else:
        # Regex fallback for 8B model reliability
        query = re.search(r"SELECT.*FROM.*", response.content, re.IGNORECASE)
        results = query_enterprise_database.invoke({"sql_query": query.group()}) if query else "No data found."

    baseline_source = str(results) if str(results) and str(results) != "No data found." else state.get("sql_results")
    baseline_revenue = extract_latest_revenue(baseline_source or "")
    price_change = simulation_inputs.get("price_change", 0)
    price_change_ratio = normalize_price_change(price_change)
    ops_latency = simulation_inputs.get("ops_latency")
    projected_revenue = None
    if baseline_revenue is not None:
        projected_revenue = baseline_revenue * (1 + price_change_ratio)
    baseline_available = baseline_revenue is not None
    if baseline_revenue is None:
        baseline_revenue = 0.0
        projected_revenue = 0.0

    simulation_summary = {
        "baseline_revenue": baseline_revenue,
        "baseline_available": baseline_available,
        "price_change_pct": price_change,
        "projected_revenue": projected_revenue,
        "ops_latency_ms": ops_latency,
        "scenario_description": (
            "Price drop combined with high latency increases abandonment risk, "
            "which can depress CRM retention and revenue conversion."
        ),
        "crm_churn_note": "Higher ops latency can increase CRM churn risk and reduce retention.",
        "note": "Baseline vs Projected for simulation"
    }

    return {
        "sql_results": merge_sql_results(state.get("sql_results"), json.dumps(simulation_summary)),
        "reasoning_steps": ["Simulation node computed baseline vs projected revenue."]
    }

def validate_insight_json(data: dict) -> bool:
    """
    Validates that the generated JSON contains all mandatory fields.
    """
    required_keys = ["meta", "content", "reasoning_chain", "visuals"]
    content_keys = ["headline", "summary", "reasoning_detailed", "recommendations"]
    
    if not all(key in data for key in required_keys):
        return False
    
    if not all(key in data["content"] for key in content_keys):
        return False
        
    return True

def reasoner_node(state: AgentState):
    sql_context = state.get("sql_results", "No data")
    user_role = state.get("role", "Executive")
    is_sim = state.get("is_simulation", False)
    simulation_inputs = state.get("simulation_inputs", {})
    last_msg = get_message_content(state["messages"][-1]).lower()
    is_chat = len(state["messages"]) > 1 and not is_sim and "health check" not in last_msg

    target_silos = normalize_silos(state.get("target_silos"))
    detected_silo = target_silos[0] if target_silos else "Operations"
    silo_instruction_block = "\n".join(
        [f"- {silo}: {SILO_INSTRUCTIONS.get(silo, '')}" for silo in target_silos]
    )
    silo_focus = SILO_FOCUS_MAP.get(detected_silo, "latency, throughput, uptime, bottleneck")

    mission_switch = {
        "Sales": "Act as a CI (Chief Intelligence) surrogate. Focus on revenue leakage, customer churn, and pipeline velocity.",
        "Operations": "Act as a CI (Chief Intelligence) surrogate. Focus on bottlenecks, latency, and uptime.",
        "HR": "Act as a CI (Chief Intelligence) surrogate. Focus on churn, headcount, payroll, and productivity impacts.",
        "Accounting": "Act as a CI (Chief Intelligence) surrogate. Focus on expenditure, cash flow, and margins.",
        "CRM": "Act as a CI (Chief Intelligence) surrogate. Focus on sentiment, retention, support tickets, and NPS impacts."
    }
    persona_focus = mission_switch.get(detected_silo, "Focus on bottlenecks, latency impact, and SLA breaches.")

    # PERSONA FILTER: Prevent database leaks in chat
    if is_chat:
        mission = (
            f"CHAT MODE ({detected_silo}): You are the {user_role}. {persona_focus} "
            "Answer the user's specific question using the detected silo language. "
            "DO NOT list raw database rows. SYNTHESIZE the answer."
        )
        format_inst = (
            "Output: Conversational text only, role-appropriate. "
            "Do not invent metrics or values not present in the provided data. "
            "Do NOT show math formulas like ((N-O)/O)."
        )
    else:
        mission = (
            f"REPORT MODE ({detected_silo}): Act as a CIO for {user_role}. {persona_focus} "
            "Enforce strict silo boundaries and financial rigor."
        )
        format_inst = "Output: STRICT JSON SCHEMA ONLY."

    simulation_block = ""
    if is_sim:
        simulation_block = (
            "SIMULATION MODE:\n"
            "- Treat sql_results as BASELINE (actuals).\n"
            "- Treat simulation_inputs as PROJECTED (what-if).\n"
            "- If a percentage change is provided, compute PROJECTED = BASELINE * (1 + change/100).\n"
            "- Compare BASELINE vs PROJECTED using the delta formula.\n"
            "- Report findings using the SQL results; do not assume a specific metric like latency.\n"
            f"PROJECTED INPUTS: {simulation_inputs}\n"
        )

    dates_found = extract_dates(sql_context)
    trend_note = ""
    if len(dates_found) < 2 and not is_sim:
        trend_note = "ONLY ONE DATE FOUND: You must state \"Insufficient trend data\" and avoid any delta.\n"

    if is_sim:
        json_template = f"""
    STRICT JSON TEMPLATE:
    {{
        "insight_id": "SIM-2026-NXS",
        "meta": {{ "urgency_score": 0.9, "confidence_score": 0.9, "role_context": "{user_role}" }},
        "target_silos": ["Sales"],
        "content": {{
            "headline": "str",
            "summary": "str with numbers",
            "reasoning_detailed": "layman cross-silo explanation",
            "recommendations": [{{ "action": "Task", "detail": "Steps", "expected_impact": "Impact" }}]
        }},
        "reasoning_chain": [{{ "step": 1, "agent": "Auditor", "thought": "Calculated deltas from context." }}],
        "visuals": {{
            "chart_type": "bar",
            "plotly_data": {{
                "data": [
                    {{ "type": "bar", "name": "Baseline Revenue", "x": ["Baseline"], "y": [0] }},
                    {{ "type": "bar", "name": "Simulated Revenue", "x": ["Simulated"], "y": [0] }}
                ]
            }}
        }}
    }}
    """
    else:
        json_template = f"""
    STRICT JSON TEMPLATE:
    {{
        "insight_id": "INC-2026-NXS",
        "meta": {{ "urgency_score": 0.9, "confidence_score": 0.9, "role_context": "{user_role}" }},
        "target_silos": ["Operations"],
        "content": {{
            "headline": "str",
            "summary": "str with numbers",
            "reasoning_detailed": "layman cross-silo explanation",
            "recommendations": [{{ "action": "Task", "detail": "Steps", "expected_impact": "Impact" }}]
        }},
        "reasoning_chain": [{{ "step": 1, "agent": "Auditor", "thought": "Calculated deltas from context." }}],
        "visuals": {{
            "chart_type": "line",
            "plotly_data": {{
                "data": [
                    {{ "type": "scatter", "mode": "lines+markers", "name": "Root Cause", "x": ["2026-01-01"], "y": [0] }},
                    {{ "type": "scatter", "mode": "lines+markers", "name": "Business Outcome", "x": ["2026-01-01"], "y": [0] }}
                ]
            }}
        }}
    }}
    """

    prompt = f"""
    MISSION: {mission}
    CONTEXT DATA (BASELINE): {sql_context}
    USER ROLE: {user_role}
    TARGET SILOS (STRICT): {target_silos}
    {format_inst}

    SILO INSTRUCTIONS:
    {silo_instruction_block}

    DETECTED SILO FOCUS:
    - Use these keywords prominently: {silo_focus}
    - Ground all findings in the SQL results; do not assume a specific metric.

    FINANCIAL MANDATE:
    - Explicitly mention impact on Cash Flow and Expenditure.
    - Include the sentence: "Total Expenditure changed by $X due to Silo {detected_silo} bottleneck."
    - Quantify Cash Flow and Expenditure using numbers present in CONTEXT DATA.
    - Include: "Impact on Cash Flow: $X" and "Estimated Expenditure: $Y".

    NUMERICAL GUARDRAIL:
    - ONLY use numbers present in CONTEXT DATA.
    - Step 1: Extract RAW values from CONTEXT DATA.
    - Step 2: Identify Baseline (Earliest Date) vs Current (Latest Date).
    - Step 3: Calculate Delta = ((Current - Baseline) / Baseline) * 100 manually and show the math.
    - If only one date exists, state "Insufficient trend data" and do not calculate a delta.
    - Do not anchor to older data outside the baseline/current window.
    {trend_note}

    TRIANGULATION MANDATE:
    - You are forbidden from reporting a metric change in one silo without correlating another silo.
    - If Operations insight appears, correlate to Accounting; if Sales insight appears, correlate to CRM.
    - If only one silo is present in CONTEXT DATA, explicitly state "Data Unavailable for triangulation".
    - Use this pattern: "Silo A (Operations) Metric X changed by Y%, which directly correlates to Silo B (Accounting) Metric Z changing by W%."
    - Use only values from CONTEXT DATA.

    {simulation_block}

        TASK (If JSON):
    1. TARGETING: Choose ONLY from [Sales, Operations, HR, Accounting, CRM].
    2. If IT-related insight occurs, map it to Operations.
    3. MATH: Use the manual delta calculation exactly.
    4. Always include a Financial Thread on Cash Flow and Expenditure.
    5. Do not invent metrics or values not present in CONTEXT DATA.
    6. Visuals must include at least two silo traces with x (dates) and y (values).
    7. If two dates exist, a graph is mandatory and x must be dates, y numeric.
        {json_template}
    """

    response = llm_smart.invoke(prompt)
    if is_chat: return {"final_insight": {"chat_response": response.content}}

    try:
        # ROBUST JSON CLEANING: Remove any text before the first '{' and after the last '}'
        # 
        cleaned_content = clean_llm_json(response.content)
        json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
        if not json_match: raise ValueError("JSON block missing")
        
        raw_json = json_match.group(0)
        clean_json = re.sub(r',\s*([\]}])', r'\1', raw_json) # Remove trailing commas
        data = json.loads(clean_json)

        if "meta" in data and "urgency_score" in data["meta"]:
            try:
                data["meta"]["urgency_score"] = min(float(data["meta"]["urgency_score"]), 1.0)
            except (TypeError, ValueError):
                data["meta"]["urgency_score"] = 1.0
        if has_extreme_percentage(cleaned_content):
            if "meta" not in data:
                data["meta"] = {"urgency_score": 1.0}
            else:
                data["meta"]["urgency_score"] = 1.0

        visuals = data.get("visuals", {})
        plotly_data = visuals.get("plotly_data", {}) if isinstance(visuals, dict) else {}
        traces = plotly_data.get("data", []) if isinstance(plotly_data, dict) else []
        if not isinstance(traces, list):
            traces = []

        dates_found = extract_dates(sql_context)
        if dates_found:
            x_values = dates_found
        else:
            x_values = ["2026-01-01", "2026-01-02"]

        needs_default = not traces or any(
            "x" not in t or "y" not in t for t in traces if isinstance(t, dict)
        )
        if needs_default:
            traces = []

        if len(traces) < 2:
            if is_sim:
                traces = [
                    {"type": "bar", "name": "Baseline Revenue", "x": x_values[:1], "y": [0.0]},
                    {"type": "bar", "name": "Simulated Revenue", "x": x_values[:1], "y": [0.0]}
                ]
            else:
                traces = [
                    {"type": "scatter", "mode": "lines+markers", "name": "Latency", "x": x_values, "y": [0.0] * len(x_values)},
                    {"type": "scatter", "mode": "lines+markers", "name": "Revenue", "x": x_values, "y": [0.0] * len(x_values)}
                ]

        visuals = {
            "chart_type": "bar" if is_sim else "line",
            "plotly_data": {"data": traces}
        }
        data["visuals"] = visuals

        normalized_targets = normalize_silos(data.get("target_silos"))
        content_text = " ".join(
            [
                str(data.get("content", {}).get("headline", "")),
                str(data.get("content", {}).get("summary", "")),
                str(data.get("content", {}).get("reasoning_detailed", ""))
            ]
        )
        inferred_targets = infer_target_silos(content_text)
        combined_targets = normalize_silos(normalized_targets + inferred_targets)
        data["target_silos"] = combined_targets

        needs_more_data = False
        if not is_sim and len(dates_found) < 2 and len(state.get("messages", [])) > 1:
            needs_more_data = True

        return {
            "final_insight": data,
            "target_silos": combined_targets,
            "needs_more_data": needs_more_data,
            "sql_retry_mode": "history_7d" if needs_more_data else None,
            "reasoning_steps": ["Causal analysis and formatting complete."]
        }
    except Exception as e:
        return {"final_insight": {"error": f"JSON Gap: {str(e)}", "raw": response.content}}
    
def security_node(state: AgentState):
    insight = state.get("final_insight")
    if not insight: return {"final_insight": {"error": "Security check bypassed; no data."}}
    
    # Scrub PII
    insight_str = json.dumps(insight)
    clean_str = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL_MASKED]", insight_str)
    return {"final_insight": json.loads(clean_str)}