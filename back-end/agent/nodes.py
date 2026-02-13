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
    for silo in ALLOWED_SILOS:
        if silo.lower() in content:
            inferred.append(silo)
    return infer_only_allowed(inferred)

def infer_only_allowed(silos: list) -> list:
    filtered = [s for s in silos if s in ALLOWED_SILOS]
    return list(dict.fromkeys(filtered))

def should_query_trend(user_msg: str) -> bool:
    msg = (user_msg or "").lower()
    keywords = ["health check", "healthcheck", "anomaly", "trend", "correlation", "cross-domain", "cross domain"]
    return any(k in msg for k in keywords)

def merge_sql_results(previous, current) -> dict:
    prev_tables = parse_sql_results(previous)
    curr_tables = parse_sql_results(current)
    return {**prev_tables, **curr_tables}

def extract_dates(text: str) -> list:
    if not text:
        return []
    return sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)))

def extract_table_names(schema: str) -> list:
    if not schema:
        return []
    matches = re.findall(r"Table:\s*([^|]+)\|", schema)
    return [m.strip() for m in matches if m.strip()]

def extract_table_from_query(query: str) -> str | None:
    if not query:
        return None
    match = re.search(r"from\s+([\w_]+)", query, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

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

def coerce_rows(raw_result) -> list:
    if raw_result is None:
        return []
    if isinstance(raw_result, list):
        return raw_result
    if isinstance(raw_result, dict):
        return [raw_result]
    if not isinstance(raw_result, str):
        return []
    try:
        parsed = ast.literal_eval(raw_result)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except (ValueError, SyntaxError):
        return []
    return []

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
    if isinstance(sql_text, dict):
        sql_text = json.dumps(sql_text)
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
    if isinstance(sql_text, dict):
        sql_text = json.dumps(sql_text)
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

def strip_control_chars(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[\x00-\x1F\x7F]", "", text)

def clamp_score(value, default=0.7) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, numeric))

def parse_llm_json(text: str) -> dict | None:
    cleaned = strip_control_chars(clean_llm_json(text or ""))
    if not cleaned:
        return None
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    candidate = extract_largest_json_block(cleaned) or cleaned
    for _ in range(3):
        candidate = strip_control_chars(candidate)
        candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
        for parser in (json.loads, ast.literal_eval):
            try:
                data = parser(candidate)
                if isinstance(data, dict):
                    return data
            except (ValueError, SyntaxError, TypeError):
                continue
        if candidate.startswith("{") and candidate.endswith("}"):
            candidate = candidate[1:-1].strip()
        else:
            break

    for match in re.finditer(r"\{.*?\}", cleaned, re.DOTALL):
        candidate = strip_control_chars(match.group(0))
        candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
        for parser in (json.loads, ast.literal_eval):
            try:
                data = parser(candidate)
                if isinstance(data, dict):
                    return data
            except (ValueError, SyntaxError, TypeError):
                continue
    return None

def table_to_silo(table_name: str) -> str:
    name = (table_name or "").lower()
    if "erp_operations" in name or "operation" in name or "it" in name:
        return "Operations"
    if "erp_accounting" in name or "account" in name or "finance" in name:
        return "Accounting"
    if "crm" in name or "marketing" in name:
        return "CRM"
    if "sales" in name:
        return "Sales"
    if "hr" in name:
        return "HR"
    return "Operations"

def format_metric_label(field_name: str) -> str:
    label = str(field_name or "").replace("_", " ").strip()
    return " ".join(word.capitalize() for word in label.split()) or "Metric"

def collect_metric_candidates(fact_sheet: dict) -> list[dict]:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    candidates = []
    for table_name, table in tables.items():
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for field_name, values in fields.items():
            baseline = values.get("baseline") if isinstance(values, dict) else None
            current = values.get("current") if isinstance(values, dict) else None
            delta_pct = values.get("delta_pct") if isinstance(values, dict) else None
            if not isinstance(baseline, (int, float)) or not isinstance(current, (int, float)):
                continue
            if not isinstance(delta_pct, (int, float)):
                continue
            candidates.append({
                "table_name": table_name,
                "field_name": field_name,
                "baseline": baseline,
                "current": current,
                "delta_pct": delta_pct,
                "abs_delta": abs(delta_pct),
                "abs_change": abs(current - baseline)
            })
    return candidates

def semantic_sweep_fields(fact_sheet: dict) -> dict:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    field_rows = []
    for table_name, table in tables.items():
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for field_name, values in fields.items():
            if not isinstance(values, dict):
                continue
            field_rows.append({
                "table": table_name,
                "field": field_name,
                "baseline": values.get("baseline"),
                "current": values.get("current"),
                "delta_pct": values.get("delta_pct")
            })

    if not field_rows:
        return {
            "Operational_Cause": [],
            "Financial_Effect": [],
            "Customer_Sentiment": [],
            "Human_Capital": []
        }

    prompt = f"""
    Categorize each field into one of four buckets:
    - Operational_Cause
    - Financial_Effect
    - Customer_Sentiment
    - Human_Capital

    Output ONLY JSON with these exact keys and arrays of {{"table": str, "field": str}}.
    Fields:
    {json.dumps(field_rows)}
    """

    response = llm_smart.invoke(prompt)
    data = parse_llm_json(response.content)
    if isinstance(data, dict):
        buckets = {}
        for key in ["Operational_Cause", "Financial_Effect", "Customer_Sentiment", "Human_Capital"]:
            items = data.get(key, [])
            if not isinstance(items, list):
                items = []
            buckets[key] = [
                {"table": item.get("table"), "field": item.get("field")} for item in items
                if isinstance(item, dict)
            ]
        return buckets

    fallback = {
        "Operational_Cause": [],
        "Financial_Effect": [],
        "Customer_Sentiment": [],
        "Human_Capital": []
    }
    for row in field_rows:
        silo = table_to_silo(row["table"])
        if silo == "Operations":
            fallback["Operational_Cause"].append({"table": row["table"], "field": row["field"]})
        elif silo == "Accounting":
            fallback["Financial_Effect"].append({"table": row["table"], "field": row["field"]})
        elif silo == "CRM":
            fallback["Customer_Sentiment"].append({"table": row["table"], "field": row["field"]})
        elif silo == "HR":
            fallback["Human_Capital"].append({"table": row["table"], "field": row["field"]})
        else:
            fallback["Operational_Cause"].append({"table": row["table"], "field": row["field"]})
    return fallback

def role_silo_preferences(user_role: str, target_silos: list | None) -> list[str]:
    role = (user_role or "").lower()
    if "sales" in role:
        return ["Sales", "CRM"]
    if "crm" in role:
        return ["CRM", "Sales"]
    if "cto" in role or "ops" in role or "operations" in role:
        return ["Operations"]
    if "hr" in role:
        return ["HR"]
    if "account" in role or "finance" in role:
        return ["Accounting"]
    if "ceo" in role:
        return ["Operations", "Accounting", "CRM", "Sales", "HR"]
    return normalize_silos(target_silos or [])

def select_trace_fields(fact_sheet: dict, user_role: str | None, target_silos: list | None) -> tuple[dict | None, dict | None]:
    candidates = collect_metric_candidates(fact_sheet)
    if not candidates:
        return None, None

    buckets = fact_sheet.get("semantic_buckets", {}) if isinstance(fact_sheet, dict) else {}
    bucket_lookup = {}
    for bucket_name, items in buckets.items() if isinstance(buckets, dict) else []:
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                bucket_lookup[(item.get("table"), item.get("field"))] = bucket_name

    role = (user_role or "").lower()
    preferred_bucket = "Operational_Cause"
    if "sales" in role or "crm" in role:
        preferred_bucket = "Customer_Sentiment"
    elif "hr" in role:
        preferred_bucket = "Human_Capital"

    def bucket_for(candidate):
        return bucket_lookup.get((candidate["table_name"], candidate["field_name"]))

    primary_pool = [c for c in candidates if bucket_for(c) == preferred_bucket]
    if not primary_pool:
        primary_pool = candidates
    primary = max(primary_pool, key=lambda c: (c["abs_delta"], c["abs_change"]))

    financial_pool = [c for c in candidates if bucket_for(c) == "Financial_Effect"]
    secondary_pool = [c for c in financial_pool if c is not primary]
    if not secondary_pool:
        secondary_pool = [c for c in candidates if c is not primary]
    secondary = max(secondary_pool, key=lambda c: (c["abs_change"], c["abs_delta"])) if secondary_pool else None
    return primary, secondary

def select_financial_fields(fact_sheet: dict) -> list[dict]:
    candidates = collect_metric_candidates(fact_sheet)
    buckets = fact_sheet.get("semantic_buckets", {}) if isinstance(fact_sheet, dict) else {}
    bucket_items = buckets.get("Financial_Effect", []) if isinstance(buckets, dict) else []
    bucket_keys = {(item.get("table"), item.get("field")) for item in bucket_items if isinstance(item, dict)}
    financial = [c for c in candidates if (c["table_name"], c["field_name"]) in bucket_keys]
    if not financial:
        financial = candidates
    return sorted(financial, key=lambda c: (c["abs_change"], c["abs_delta"]), reverse=True)

def map_tables_to_silos(fact_sheet: dict) -> list[str]:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    silos = [table_to_silo(name) for name in tables.keys()]
    return normalize_silos(silos)

def ensure_minimum_silos(silos: list[str]) -> list[str]:
    normalized = normalize_silos(silos)
    if len(normalized) >= 2:
        return normalized
    if "Accounting" not in normalized:
        normalized.append("Accounting")
    if len(normalized) < 2 and "Operations" not in normalized:
        normalized.append("Operations")
    return normalize_silos(normalized)

def build_headline_from_traces(primary: dict | None, secondary: dict | None) -> str:
    if primary and secondary:
        return (
            f"{format_metric_label(primary['field_name'])} Change in {table_to_silo(primary['table_name'])} "
            f"Impacting {format_metric_label(secondary['field_name'])} in {table_to_silo(secondary['table_name'])}"
        )
    if primary:
        return f"{format_metric_label(primary['field_name'])} Change in {table_to_silo(primary['table_name'])} Impacting Finance"
    return "Cross-silo Change in Operations Impacting Finance"

def build_simulation_comparison_visuals(fact_sheet: dict, simulation_summary: dict | None) -> dict:
    x_values = ["Current Actual", "Simulated Projection"]
    financial = select_financial_fields(fact_sheet)
    projected = simulation_summary.get("projected") if isinstance(simulation_summary, dict) else {}

    traces = []
    revenue_metric = None
    expenditure_metric = None
    if len(financial) >= 2:
        first = financial[0]
        second = financial[1]
        if first.get("current", 0.0) >= second.get("current", 0.0):
            revenue_metric, expenditure_metric = first, second
        else:
            revenue_metric, expenditure_metric = second, first
    elif financial:
        revenue_metric = financial[0]
        expenditure_metric = financial[0]

    projected_revenue = None
    if isinstance(projected, dict):
        numeric_values = [v for v in projected.values() if isinstance(v, (int, float))]
        projected_revenue = numeric_values[0] if numeric_values else None
    if revenue_metric is None:
        projected_revenue = projected_revenue or 0.0
    else:
        projected_revenue = projected_revenue if projected_revenue is not None else revenue_metric.get("current", 0.0)

    if revenue_metric and expenditure_metric:
        revenue_current = revenue_metric.get("current", 0.0)
        expenditure_current = expenditure_metric.get("current", 0.0)
        margin = 0.0
        if revenue_current:
            margin = (revenue_current - expenditure_current) / revenue_current
        projected_expenditure = projected_revenue * (1 - margin)

        traces.append({
            "type": "bar",
            "name": format_metric_label(revenue_metric["field_name"]),
            "x": x_values,
            "y": [revenue_current, projected_revenue]
        })
        traces.append({
            "type": "bar",
            "name": format_metric_label(expenditure_metric["field_name"]),
            "x": x_values,
            "y": [expenditure_current, projected_expenditure]
        })

    if not traces:
        traces = [
            {"type": "bar", "name": "Projected Impact", "x": x_values, "y": [0.0, 0.0]}
        ]

    return {"chart_type": "bar", "plotly_data": {"data": traces}}

def get_field_values(fact_sheet: dict, keys: list[str]) -> dict | None:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    candidate = find_field_by_keys(tables, keys)
    if not candidate:
        return None
    table_name, field_name, table = candidate
    fields = table.get("fields", {}) if isinstance(table, dict) else {}
    values = fields.get(field_name, {}) if isinstance(fields, dict) else {}
    baseline = values.get("baseline")
    current = values.get("current")
    delta_pct = values.get("delta_pct")
    return {
        "table_name": table_name,
        "field_name": field_name,
        "baseline": baseline,
        "current": current,
        "delta_pct": delta_pct
    }

def build_reasoning_from_fact_sheet(fact_sheet: dict, user_role: str) -> dict:
    candidates = collect_metric_candidates(fact_sheet)
    accounting_candidates = [
        c for c in candidates
        if table_to_silo(c.get("table_name")) == "Accounting"
    ]
    if fact_sheet.get("semantic_buckets") and accounting_candidates:
        bucket_items = fact_sheet.get("semantic_buckets", {}).get("Financial_Effect", [])
        bucket_keys = {
            (item.get("table"), item.get("field"))
            for item in bucket_items
            if isinstance(item, dict)
        }
        accounting_candidates = [
            c for c in accounting_candidates
            if (c.get("table_name"), c.get("field_name")) in bucket_keys
        ] or accounting_candidates

    revenue_source = None
    if accounting_candidates:
        revenue_source = max(accounting_candidates, key=lambda c: c.get("current", 0.0))
    actual_revenue = revenue_source.get("current", 0.0) if revenue_source else 0.0
    baseline_revenue = revenue_source.get("baseline", 0.0) if revenue_source else 0.0
    cash_flow_impact = actual_revenue - baseline_revenue

    expenditure_source = None
    if accounting_candidates:
        expenditure_pool = [c for c in accounting_candidates if c is not revenue_source]
        if not expenditure_pool:
            expenditure_pool = accounting_candidates
        expenditure_source = max(expenditure_pool, key=lambda c: c.get("abs_change", 0.0))
    expenditure_delta = 0.0
    if expenditure_source:
        expenditure_delta = expenditure_source.get("current", 0.0) - expenditure_source.get("baseline", 0.0)

    variable_mapping = {
        "ACTUAL_REVENUE": actual_revenue,
        "BASELINE_REVENUE": baseline_revenue,
        "CASH_FLOW_IMPACT": cash_flow_impact,
        "ACCOUNTING_TABLE": revenue_source.get("table_name") if revenue_source else None,
        "ACCOUNTING_FIELD": revenue_source.get("field_name") if revenue_source else None
    }

    primary, secondary = select_trace_fields(fact_sheet, user_role, map_tables_to_silos(fact_sheet))
    head = build_headline_from_traces(primary, secondary)

    summary_parts = []
    if primary and isinstance(primary.get("baseline"), (int, float)) and isinstance(primary.get("current"), (int, float)):
        summary_parts.append(
            f"{format_metric_label(primary['field_name'])} moved from {primary['baseline']} to {primary['current']}."
        )
    if secondary and isinstance(secondary.get("baseline"), (int, float)) and isinstance(secondary.get("current"), (int, float)):
        summary_parts.append(
            f"{format_metric_label(secondary['field_name'])} moved from {secondary['baseline']} to {secondary['current']}."
        )
    summary = " ".join(summary_parts) or "Review of baseline vs current metrics across available tables."

    ops_silo = table_to_silo(primary["table_name"]) if primary else "Operations"
    fin_silo = table_to_silo(secondary["table_name"]) if secondary else "Accounting"
    ops_metric = format_metric_label(primary["field_name"]) if primary else "Metric"
    fin_metric = format_metric_label(secondary["field_name"]) if secondary else "Metric"
    reasoning = (
        f"Total Expenditure changed by ${abs(expenditure_delta):.0f} due to {ops_silo} bottleneck. "
        f"The {ops_metric} spike in {ops_silo} is the root cause of the {fin_metric} drop in {fin_silo}. "
        f"Impact on Cash Flow: ${abs(variable_mapping['CASH_FLOW_IMPACT']):.0f}. "
        f"Estimated Expenditure: ${abs(expenditure_delta):.0f}."
    )

    recommendations = [
        {
            "action": "Validate root cause",
            "detail": f"Investigate {ops_silo} drivers behind {ops_metric} changes.",
            "expected_impact": "Stabilize operational performance and protect revenue."
        }
    ]

    return {
        "headline": head,
        "summary": summary,
        "reasoning_detailed": reasoning,
        "recommendations": recommendations
    }

def enforce_strict_schema(data: dict | None, fact_sheet: dict, user_role: str, is_sim: bool) -> dict:
    if not isinstance(data, dict):
        data = {}

    insight_id = data.get("insight_id") or ("SIM-2026-NXS" if is_sim else "INC-2026-NXS")
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    meta = {
        "urgency_score": clamp_score(meta.get("urgency_score"), 0.7),
        "confidence_score": clamp_score(meta.get("confidence_score"), 0.7),
        "role_context": meta.get("role_context") or user_role
    }

    content = data.get("content") if isinstance(data.get("content"), dict) else {}
    fallback_content = build_reasoning_from_fact_sheet(fact_sheet, user_role)
    content = {
        "headline": content.get("headline") or fallback_content["headline"],
        "summary": content.get("summary") or fallback_content["summary"],
        "reasoning_detailed": content.get("reasoning_detailed") or fallback_content["reasoning_detailed"],
        "recommendations": content.get("recommendations") or fallback_content["recommendations"]
    }
    if not isinstance(content.get("recommendations"), list) or not content.get("recommendations"):
        content["recommendations"] = fallback_content["recommendations"]

    reasoning_chain = data.get("reasoning_chain")
    if not isinstance(reasoning_chain, list) or not reasoning_chain:
        reasoning_chain = [{"step": 1, "agent": "Auditor", "thought": "Structured insight from fact sheet."}]
    else:
        normalized_chain = []
        for idx, item in enumerate(reasoning_chain, start=1):
            if isinstance(item, dict):
                normalized_chain.append({
                    "step": int(item.get("step", idx)),
                    "agent": str(item.get("agent", "Analyst")),
                    "thought": str(item.get("thought", ""))
                })
        reasoning_chain = normalized_chain or [{"step": 1, "agent": "Analyst", "thought": "Structured insight."}]

    visuals = data.get("visuals") if isinstance(data.get("visuals"), dict) else {}
    plotly = visuals.get("plotly_data") if isinstance(visuals.get("plotly_data"), dict) else {}
    traces = plotly.get("data") if isinstance(plotly.get("data"), list) else []
    if not traces:
        visuals = generate_plotly_from_fact_sheet(fact_sheet, user_role, data.get("target_silos"))
    else:
        normalized_traces = []
        for trace in traces:
            if isinstance(trace, dict) and "x" in trace and "y" in trace:
                normalized_traces.append({
                    "x": trace.get("x"),
                    "y": trace.get("y"),
                    "name": trace.get("name", "Trace"),
                    "type": trace.get("type", "scatter")
                })
        visuals = {
            "chart_type": visuals.get("chart_type") or ("bar" if is_sim else "line"),
            "plotly_data": {"data": normalized_traces}
        }

    primary, secondary = select_trace_fields(fact_sheet, user_role, data.get("target_silos"))
    content["headline"] = build_headline_from_traces(primary, secondary)

    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    mapped = [table_to_silo(name) for name in tables.keys()]
    target_silos = infer_only_allowed(mapped)

    return {
        "insight_id": insight_id,
        "meta": meta,
        "content": content,
        "reasoning_chain": reasoning_chain,
        "visuals": visuals,
        "target_silos": target_silos
    }

def extract_largest_json_block(text: str) -> str | None:
    if not text:
        return None
    matches = list(re.finditer(r"\{.*?\}", text, re.DOTALL))
    if not matches:
        return None
    largest = max(matches, key=lambda m: len(m.group(0)))
    return largest.group(0)

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

def parse_schema_tables(schema: str) -> list:
    if not schema:
        return []
    tables = []
    for line in schema.splitlines():
        if "Table:" not in line:
            continue
        try:
            name_part, columns_part = line.split("|", 1)
        except ValueError:
            continue
        table_name = name_part.replace("Table:", "").strip()
        columns = []
        if "Columns:" in columns_part:
            raw_cols = columns_part.split("Columns:", 1)[1]
            for col in raw_cols.split(","):
                col_name = col.split("(", 1)[0].strip()
                if col_name:
                    columns.append(col_name)
        if table_name:
            tables.append((table_name, columns))
    return tables

def find_date_column(columns: list) -> str | None:
    if not columns:
        return None
    for col in columns:
        col_lower = str(col).lower()
        if "date" in col_lower or "time" in col_lower or "created" in col_lower:
            return col
    return None

def build_table_query(table: str, columns: list) -> str:
    date_col = find_date_column(columns)
    if date_col:
        return f"SELECT * FROM {table} ORDER BY {date_col} DESC LIMIT 10;"
    return f"SELECT * FROM {table} LIMIT 10;"

def parse_sql_results(sql_results) -> dict:
    if not sql_results:
        return {}
    if isinstance(sql_results, dict):
        if "tables" in sql_results and isinstance(sql_results.get("tables"), dict):
            return sql_results.get("tables", {})
        return sql_results
    if isinstance(sql_results, list):
        return {"default": sql_results}
    if not isinstance(sql_results, str):
        return {}
    raw = sql_results.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        candidate = json_match.group(0)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "tables" in parsed:
                return parsed.get("tables", {})
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "tables" in parsed:
            return parsed.get("tables", {})
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"default": parsed}
    except (ValueError, TypeError):
        pass
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return {"default": parsed}
        if isinstance(parsed, dict):
            if "tables" in parsed:
                return parsed.get("tables", {})
            return parsed
    except (ValueError, SyntaxError):
        pass
    return {}

def collect_tables_from_sql_results(sql_results: str) -> dict:
    if not sql_results:
        return {}
    if isinstance(sql_results, dict):
        if "tables" in sql_results and isinstance(sql_results.get("tables"), dict):
            return sql_results.get("tables", {})
        return sql_results
    parsed = parse_sql_results(sql_results)
    if parsed:
        return parsed
    if isinstance(sql_results, str):
        json_match = re.search(r"\{.*\}", sql_results, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict) and "tables" in parsed:
                    return parsed.get("tables", {})
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, TypeError):
                return {}
    return {}

def build_fact_sheet(sql_tables: dict) -> dict:
    fact_sheet = {"tables": {}}
    for table, rows in sql_tables.items():
        if not isinstance(rows, list) or not rows:
            continue
        date_col = None
        for key in rows[0].keys() if isinstance(rows[0], dict) else []:
            if "date" in str(key).lower():
                date_col = key
                break
        if not date_col:
            continue
        filtered = [r for r in rows if isinstance(r, dict) and r.get(date_col)]
        if len(filtered) < 2:
            continue
        filtered.sort(key=lambda r: str(r.get(date_col)))
        baseline = filtered[0]
        current = filtered[-1]
        fields = {}
        for key, value in baseline.items():
            if key == date_col:
                continue
            if not isinstance(value, (int, float)):
                continue
            current_val = current.get(key)
            if not isinstance(current_val, (int, float)):
                continue
            if value == 0:
                delta_pct = None
            else:
                delta_pct = ((current_val - value) / value) * 100
            fields[key] = {
                "baseline": value,
                "current": current_val,
                "delta_pct": delta_pct
            }
        fact_sheet["tables"][table] = {
            "baseline_date": baseline.get(date_col),
            "current_date": current.get(date_col),
            "fields": fields
        }
    return fact_sheet

def resolve_date_pair(fact_sheet: dict) -> tuple[str, str]:
    for table in fact_sheet.get("tables", {}).values():
        if not isinstance(table, dict):
            continue
        baseline = table.get("baseline_date")
        current = table.get("current_date")
        if baseline and current:
            return str(baseline), str(current)
    return "2026-02-01", "2026-02-07"

def find_field_by_keys(tables: dict, keys: list[str]) -> tuple[str, str, dict] | None:
    for table_name, table in tables.items():
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for field_name in fields.keys():
            field_lower = field_name.lower()
            for key in keys:
                if field_lower == key or key in field_lower:
                    return table_name, field_name, table
    return None

def extract_revenue_drop(fact_sheet: dict) -> tuple[float, float, float] | None:
    financial = select_financial_fields(fact_sheet)
    if not financial:
        return None
    metric = financial[0]
    baseline = metric.get("baseline")
    current = metric.get("current")
    if not isinstance(baseline, (int, float)) or not isinstance(current, (int, float)):
        return None
    if baseline == 0:
        return baseline, current, 0.0
    delta_pct = ((current - baseline) / baseline) * 100
    return baseline, current, delta_pct

def detect_material_change(fact_sheet: dict, threshold: float = 5.0) -> bool:
    def walk(value) -> bool:
        if isinstance(value, dict):
            delta = value.get("delta_pct")
            if isinstance(delta, (int, float)) and abs(delta) >= threshold:
                return True
            for child in value.values():
                if walk(child):
                    return True
        elif isinstance(value, list):
            for item in value:
                if walk(item):
                    return True
        return False

    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    if isinstance(tables, dict) and tables:
        for table in tables.values():
            if walk(table):
                return True
        return False

    return walk(fact_sheet)

def extract_latest_revenue_from_tables(sql_tables: dict) -> float | None:
    for rows in sql_tables.values():
        if not isinstance(rows, list):
            continue
        revenue = extract_latest_revenue(str(rows))
        if revenue is not None:
            return revenue
    return None

def has_numeric_values(fact_sheet: dict) -> bool:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    for table in tables.values():
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for values in fields.values():
            for key in ("baseline", "current"):
                if isinstance(values.get(key), (int, float)):
                    return True
    return False

def generate_plotly_from_fact_sheet(
    fact_sheet: dict,
    user_role: str | None = None,
    target_silos: list | None = None
) -> dict:
    tables = fact_sheet.get("tables", {})
    primary, secondary = select_trace_fields(fact_sheet, user_role, target_silos)
    traces = []
    fallback_start, fallback_end = resolve_date_pair(fact_sheet)
    if primary:
        table = tables.get(primary["table_name"], {}) if isinstance(tables, dict) else {}
        x_values = [table.get("baseline_date") or fallback_start, table.get("current_date") or fallback_end]
        y_values = [primary["baseline"], primary["current"]]
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "name": format_metric_label(primary["field_name"]),
            "x": x_values,
            "y": y_values
        })
    if secondary:
        table = tables.get(secondary["table_name"], {}) if isinstance(tables, dict) else {}
        x_values = [table.get("baseline_date") or fallback_start, table.get("current_date") or fallback_end]
        y_values = [secondary["baseline"], secondary["current"]]
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "name": format_metric_label(secondary["field_name"]),
            "x": x_values,
            "y": y_values
        })
    if not traces:
        first_field = None
        first_table = None
        for table in tables.values():
            fields = table.get("fields", {}) if isinstance(table, dict) else {}
            for field_name in fields.keys():
                first_field = field_name
                first_table = table
                break
            if first_field:
                break
        if first_field and first_table:
            traces = [{
                "type": "scatter",
                "mode": "lines+markers",
                "name": format_metric_label(first_field),
                "x": [first_table.get("baseline_date") or fallback_start, first_table.get("current_date") or fallback_end],
                "y": [
                    first_table["fields"][first_field]["baseline"],
                    first_table["fields"][first_field]["current"]
                ]
            }]
        else:
            traces = [{
                "type": "scatter",
                "mode": "lines+markers",
                "name": "No Data",
                "x": [fallback_start, fallback_end],
                "y": [0, 0]
            }]
    return {"chart_type": "line", "plotly_data": {"data": traces}}

def sql_agent_node(state: AgentState):
    schema = get_database_schema.invoke({})
    messages = state.get("messages") or []
    user_msg = get_message_content(messages[-1]) if messages else ""
    combined_msg = " ".join(get_message_content(msg) for msg in messages) if messages else user_msg
    trend_required = should_query_trend(combined_msg)
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
            f"REQUEST: {combined_msg or user_msg}"
        )
    )

    results = "No data found."
    last_query = None
    if trend_required or retry_mode == "history_7d":
        table_results = {}
        for table_name, columns in parse_schema_tables(schema):
            query = build_table_query(table_name, columns)
            attempt = query_enterprise_database.invoke({"sql_query": query})
            if is_sql_error(attempt) or attempt == "Data Unavailable":
                continue
            try:
                parsed = ast.literal_eval(attempt)
                if isinstance(parsed, list):
                    table_results[table_name] = parsed
            except (ValueError, SyntaxError):
                continue
        previous_results = state.get("sql_results")
        if not table_results and previous_results:
            merged_results = previous_results
        else:
            merged_results = merge_sql_results(previous_results, table_results)
        return {
            "sql_results": merged_results,
            "sql_retry_mode": None,
            "reasoning_steps": ["SQL node retrieved specific domain data."]
        }
    try:
        response = llm_with_tools.invoke([query_prompt])
        if getattr(response, "tool_calls", None):
            tool_args = response.tool_calls[0].get("args", {})
            last_query = tool_args.get("sql_query")
            results = query_enterprise_database.invoke(tool_args)
        else:
            # Regex fallback for 8B model reliability
            query = re.search(r"SELECT\s+.*?\s+FROM\s+.*?(;|$)", response.content, re.IGNORECASE | re.DOTALL)
            if query:
                last_query = query.group(0).strip()
                results = query_enterprise_database.invoke({"sql_query": last_query})
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
        table_name = extract_table_from_query(last_query or "") or "default"
        rows = coerce_rows(results)
        new_tables = {table_name: rows} if rows else {}
        merged_results = merge_sql_results(previous_results, new_tables)

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
    table_results = {}
    for table_name, columns in parse_schema_tables(schema):
        query = build_table_query(table_name, columns)
        attempt = query_enterprise_database.invoke({"sql_query": query})
        if is_sql_error(attempt) or attempt == "Data Unavailable":
            continue
        try:
            parsed = ast.literal_eval(attempt)
            if isinstance(parsed, list):
                table_results[table_name] = parsed
        except (ValueError, SyntaxError):
            continue

    baseline_revenue = extract_latest_revenue_from_tables(table_results)
    if baseline_revenue is None:
        baseline_source = state.get("sql_results")
        if isinstance(baseline_source, dict):
            baseline_source = json.dumps(baseline_source)
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

    projected = {
        "revenue": projected_revenue,
        "ops_latency_ms": ops_latency
    }

    simulation_summary = {
        "tables": table_results,
        "baseline": {"revenue": baseline_revenue},
        "projected": projected,
        "baseline_available": baseline_available,
        "price_change_pct": price_change,
        "ops_latency_ms": ops_latency,
        "scenario_description": (
            "Price change combined with operational conditions can shift demand and retention. "
            "Explain impacts using the SQL results."
        ),
        "note": "Baseline vs Projected for simulation"
    }

    return {
        "sql_results": merge_sql_results(state.get("sql_results"), simulation_summary.get("tables", {})),
        "simulation_summary": simulation_summary,
        "reasoning_steps": ["Simulation node computed baseline vs projected revenue."]
    }

def validate_insight_json(data: dict) -> bool:
    """
    Validates that the generated JSON contains minimum required content.
    Visuals and reasoning chain can be patched later.
    """
    if not isinstance(data, dict):
        return False
    content = data.get("content")
    if not isinstance(content, dict):
        return False
    if not any(key in content for key in ["headline", "summary", "reasoning_detailed", "recommendations"]):
        return False
    return True

def patch_insight_json(data: dict, fact_sheet: dict, user_role: str, is_sim: bool) -> dict:
    if not isinstance(data, dict):
        data = {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    meta.setdefault("urgency_score", 0.7)
    meta.setdefault("confidence_score", 0.7)
    meta.setdefault("role_context", user_role)
    data["meta"] = meta

    content = data.get("content") if isinstance(data.get("content"), dict) else {}
    primary, secondary = select_trace_fields(fact_sheet, user_role, map_tables_to_silos(fact_sheet))
    headline = build_headline_from_traces(primary, secondary)
    fallback_content = build_reasoning_from_fact_sheet(fact_sheet, user_role)
    content.setdefault("headline", headline)
    content.setdefault("summary", fallback_content["summary"])
    content.setdefault("reasoning_detailed", fallback_content["reasoning_detailed"])
    recommendations = content.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        recommendations = [
            {
                "action": "Validate source metrics",
                "detail": "Confirm the baseline and current values in the Fact Sheet.",
                "expected_impact": "Improved confidence in the analysis."
            }
        ]
    content["recommendations"] = recommendations
    data["content"] = content

    reasoning_chain = data.get("reasoning_chain")
    if not isinstance(reasoning_chain, list) or not reasoning_chain:
        reasoning_chain = [{"step": 1, "agent": "Auditor", "thought": "Patched missing reasoning chain."}]
    data["reasoning_chain"] = reasoning_chain

    visuals = data.get("visuals") if isinstance(data.get("visuals"), dict) else {}
    if not visuals:
        visuals = generate_plotly_from_fact_sheet(fact_sheet, user_role, map_tables_to_silos(fact_sheet))
        visuals["chart_type"] = "bar" if is_sim else visuals.get("chart_type", "line")
    data["visuals"] = visuals

    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    mapped = [table_to_silo(name) for name in tables.keys()]
    data["target_silos"] = infer_only_allowed(mapped)
    return data

def reasoner_node(state: AgentState):
    sql_context = state.get("sql_results", "No data")
    user_role = state.get("role", "Executive")
    is_sim = state.get("is_simulation", False)
    simulation_inputs = state.get("simulation_inputs", {})
    last_msg = get_message_content(state["messages"][-1]).lower()
    is_chat = len(state["messages"]) > 1 and not is_sim and "health check" not in last_msg
    fact_sheet = state.get("fact_sheet", {})
    if is_chat:
        if not fact_sheet.get("tables"):
            history = state.get("fact_sheet_history", [])
            for previous in reversed(history):
                if isinstance(previous, dict) and previous.get("tables"):
                    fact_sheet = previous
                    break
        if not fact_sheet.get("tables"):
            merged_tables = collect_tables_from_sql_results(sql_context)
            if merged_tables:
                fact_sheet = build_fact_sheet(merged_tables)
        if fact_sheet.get("tables"):
            sql_context = json.dumps(fact_sheet)
        elif isinstance(sql_context, dict):
            sql_context = json.dumps(sql_context)
    elif isinstance(sql_context, dict):
        sql_context = json.dumps(sql_context)

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
        revenue_fact = ""
        revenue_drop = extract_revenue_drop(fact_sheet)
        if revenue_drop:
            baseline, current, delta_pct = revenue_drop
            revenue_fact = (
                f"KNOWN FACTS: Accounting revenue dropped from {baseline} to {current} "
                f"({delta_pct:.1f}%). Use this in your response.\n"
            )
        mission = (
            f"CHAT MODE ({detected_silo}): You are the {user_role}. {persona_focus} "
            "Answer the user's specific question using the detected silo language. "
            "DO NOT list raw database rows. SYNTHESIZE the answer."
        )
        format_inst = (
            "Output: Conversational text only, role-appropriate. "
            "Prioritize the Fact Sheet data if available. "
            "Do not invent metrics or values not present in the provided data. "
            "Do NOT show math formulas like ((N-O)/O).\n"
            f"{revenue_fact}"
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
    - Prefer expenditure values from Accounting tables when available.
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
    if is_chat:
        history = [fact_sheet] if fact_sheet.get("tables") else []
        return {
            "final_insight": {"chat_response": response.content},
            "fact_sheet": fact_sheet,
            "fact_sheet_history": history
        }

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

def quantitative_audit_node(state: AgentState):
    sql_context = state.get("sql_results", "")
    merged_tables = collect_tables_from_sql_results(sql_context)
    if not merged_tables:
        merged_tables = parse_sql_results(sql_context)
    fact_sheet = build_fact_sheet(merged_tables)
    if not fact_sheet.get("tables"):
        fact_sheet = state.get("fact_sheet", {}) or fact_sheet
    semantic_buckets = {}
    if fact_sheet.get("tables"):
        semantic_buckets = semantic_sweep_fields(fact_sheet)
        fact_sheet["semantic_buckets"] = semantic_buckets
    history = [fact_sheet] if fact_sheet.get("tables") else []
    return {
        "sql_results": state.get("sql_results"),
        "fact_sheet": fact_sheet,
        "fact_sheet_history": history,
        "semantic_buckets": semantic_buckets,
        "audit_summary": "Fact sheet generated from SQL results.",
        "reasoning_steps": ["Quantitative audit completed."]
    }

def insight_filter_node(state: AgentState):
    if state.get("is_simulation", False):
        return {"end_early": False}
    if len(state.get("messages", [])) > 1:
        return {"end_early": False}
    user_msg = ""
    if state.get("messages"):
        user_msg = get_message_content(state["messages"][-1]).lower()
    if any(k in user_msg for k in ["health check", "healthcheck", "anomaly", "audit"]):
        return {"end_early": False}
    fact_sheet = state.get("fact_sheet", {})
    if detect_material_change(fact_sheet):
        return {"end_early": False}
    return {"final_insight": None, "end_early": True}

def build_fallback_insight(fact_sheet: dict, user_role: str) -> dict:
    headline = "Cross-silo summary"
    summary = "Reviewed latest baseline vs current metrics across available tables."
    reasoning = "Total Expenditure changed by $0 due to [Silo] bottleneck. Data Unavailable for triangulation."
    visuals = generate_plotly_from_fact_sheet(fact_sheet, user_role) if fact_sheet else {"chart_type": "line", "plotly_data": {"data": []}}
    target_silos = ensure_minimum_silos(map_tables_to_silos(fact_sheet))
    return {
        "insight_id": "FALLBACK-2026-NXS",
        "meta": {"urgency_score": 0.5, "confidence_score": 0.5, "role_context": user_role},
        "target_silos": normalize_silos(target_silos),
        "content": {
            "headline": headline,
            "summary": summary,
            "reasoning_detailed": reasoning,
            "recommendations": [
                {
                    "action": "Verify data coverage",
                    "detail": "Confirm latest tables and dates are loaded before conclusions.",
                    "expected_impact": "Higher confidence in cross-silo insights."
                }
            ]
        },
        "reasoning_chain": [
            {"step": 1, "agent": "Auditor", "thought": "Fact sheet used for fallback synthesis."}
        ],
        "visuals": visuals
    }

def strategic_reasoner_node(state: AgentState):
    fact_sheet = state.get("fact_sheet", {})
    user_role = state.get("role", "Executive")
    is_sim = state.get("is_simulation", False)
    simulation_summary = state.get("simulation_summary")
    sales_manager = str(user_role).lower() == "sales manager"
    role_focus = {
        "CEO": "Cross-silo executive synthesis with emphasis on Operations, Accounting, and CRM.",
        "Sales Manager": "Prioritize lead quality and pipeline health, then link to revenue impact.",
        "Operations Manager": "Focus on latency, success rate, and uptime impacts.",
        "HR Manager": "Focus on productivity and payroll expenditure impacts.",
    }
    persona_focus = role_focus.get(user_role, "Executive synthesis with cross-silo triangulation.")

    has_numbers = has_numeric_values(fact_sheet)
    constraint_line = (
        "You are forbidden from stating 'Data Unavailable' if the Fact Sheet contains any numbers. "
        "You must triangulate across at least two tables (e.g., Operations and Accounting)."
        if has_numbers else
        "If numeric data is missing, explain what is unavailable without using the phrase 'Data Unavailable'."
    )
    sim_context = ""
    if is_sim and isinstance(simulation_summary, dict):
        sim_context = f"SIMULATION SUMMARY (JSON): {json.dumps(simulation_summary)}"

    role_filter_block = ""
    if sales_manager:
        role_filter_block = (
            "ROLE FILTERING:\n"
            "- Do not mention latency or uptime in the HEADLINE or RECOMMENDATIONS.\n"
            "- Emphasize lead quality and pipeline health in the HEADLINE and RECOMMENDATIONS.\n"
            "- Still include Expenditure impact as a footer line in the REASONING section.\n"
        )

    logic_prompt = f"""
    ROLE: Chief Intelligence Officer
    USER ROLE: {user_role}
    PERSONA FOCUS: {persona_focus}
    FACT SHEET (JSON): {json.dumps(fact_sheet)}
    {sim_context}

    TASK:
    - Produce a plain-text causal analysis using only numbers from the Fact Sheet.
    - {constraint_line}
    - Triangulate across at least two tables.
    - If Simulation Summary is provided, prioritize Projected values over Historical values.
    - Headline format must be: "[Metric] Change in [Silo] Impacting [Metric] in [Silo]".
    - Avoid any JSON or code formatting.
    {role_filter_block}

    OUTPUT FORMAT:
    HEADLINE: ...
    SUMMARY: ...
    REASONING: ...
    RECOMMENDATIONS:
    - ...
    - ...
    """

    analysis_response = llm_smart.invoke(logic_prompt)
    analysis_text = analysis_response.content

    format_prompt = f"""
    You are a strict JSON formatter. Output ONLY valid JSON using this exact schema and keys:
    {{
      "insight_id": "str",
      "meta": {{"urgency_score": float, "confidence_score": float, "role_context": "str"}},
      "content": {{
        "headline": "str",
        "summary": "str",
        "reasoning_detailed": "str",
        "recommendations": [{{"action": "str", "detail": "str", "expected_impact": "str"}}]
      }},
      "reasoning_chain": [{{"step": int, "agent": "str", "thought": "str"}}],
      "visuals": {{"chart_type": "line/bar", "plotly_data": {{"data": [{{"x": [], "y": [], "name": "str", "type": "str"}}]}}}}
    }}
    Do not add any keys outside this schema. Use the analysis below to fill values.

    ANALYSIS:
    {analysis_text}
    """

    formatted_response = llm_smart.invoke(format_prompt)
    data = parse_llm_json(formatted_response.content)
    if data is None:
        retry_prompt = f"""
        The JSON output was invalid. Fix it to match the exact schema. Output ONLY JSON.
        ORIGINAL OUTPUT:
        {formatted_response.content}
        """
        formatted_response = llm_smart.invoke(retry_prompt)
        data = parse_llm_json(formatted_response.content)

    final_insight = enforce_strict_schema(data, fact_sheet, user_role, is_sim)
    if sales_manager and isinstance(final_insight, dict):
        content = final_insight.get("content") if isinstance(final_insight.get("content"), dict) else {}
        headline = str(content.get("headline", ""))
        headline = re.sub(r"\b(latency|uptime)\b", "", headline, flags=re.IGNORECASE).strip()
        if "lead" not in headline.lower() and "pipeline" not in headline.lower():
            headline = f"Lead Quality Shift Impacting Pipeline Health - {headline}".strip(" -")
        content["headline"] = re.sub(r"\s{2,}", " ", headline).strip()

        recommendations = content.get("recommendations") if isinstance(content.get("recommendations"), list) else []
        cleaned_recs = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            action = re.sub(r"\b(latency|uptime)\b", "", str(rec.get("action", "")), flags=re.IGNORECASE)
            detail = re.sub(r"\b(latency|uptime)\b", "", str(rec.get("detail", "")), flags=re.IGNORECASE)
            if "lead" not in (action + detail).lower() and "pipeline" not in (action + detail).lower():
                detail = f"Improve lead quality and pipeline health. {detail}".strip()
            cleaned_recs.append({
                "action": re.sub(r"\s{2,}", " ", action).strip() or "Improve lead quality",
                "detail": re.sub(r"\s{2,}", " ", detail).strip(),
                "expected_impact": rec.get("expected_impact", "Protect revenue performance.")
            })
        content["recommendations"] = cleaned_recs or content.get("recommendations", [])

        accounting_candidates = [
            c for c in collect_metric_candidates(fact_sheet)
            if table_to_silo(c.get("table_name")) == "Accounting"
        ]
        expenditure_footer = ""
        if accounting_candidates:
            source = max(accounting_candidates, key=lambda c: c.get("abs_change", 0.0))
            delta = source.get("current", 0.0) - source.get("baseline", 0.0)
            expenditure_footer = f"Expenditure impact: ${abs(delta):.0f}."
        reasoning = str(content.get("reasoning_detailed", "")).strip()
        if expenditure_footer and expenditure_footer.lower() not in reasoning.lower():
            reasoning = f"{reasoning}\n{expenditure_footer}".strip()
        content["reasoning_detailed"] = reasoning
        final_insight["content"] = content
    return {"final_insight": final_insight}

def chart_generator_node(state: AgentState):
    fact_sheet = state.get("fact_sheet", {})
    final_insight = state.get("final_insight")
    if isinstance(final_insight, dict):
        is_sim = state.get("is_simulation", False)
        visuals = final_insight.get("visuals") if isinstance(final_insight.get("visuals"), dict) else None
        plotly_data = visuals.get("plotly_data") if isinstance(visuals, dict) else None
        traces = plotly_data.get("data") if isinstance(plotly_data, dict) else None
        if is_sim:
            visuals = build_simulation_comparison_visuals(fact_sheet, state.get("simulation_summary"))
        elif not isinstance(traces, list) or not traces:
            visuals = generate_plotly_from_fact_sheet(
                fact_sheet,
                state.get("role"),
                state.get("target_silos")
            )
        final_insight = {**final_insight, "visuals": visuals}
    return {"final_insight": final_insight}
    
def security_node(state: AgentState):
    insight = state.get("final_insight")
    if insight is None:
        return {"final_insight": None}
    if not insight:
        return {"final_insight": {"error": "Security check bypassed; no data."}}
    
    # Scrub PII
    insight_str = json.dumps(insight)
    clean_str = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL_MASKED]", insight_str)
    return {"final_insight": json.loads(clean_str)}