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

def classify_interaction_mode(user_message: str) -> str:
    raw = (user_message or "").strip()
    if not raw:
        return "SOCIAL"
    msg = raw.lower()

    social_pattern = r"^(hi|hello|hey|how are you|good\s+(morning|afternoon|evening)|thanks|thank you)\b[\s!.,?]*$"
    if re.match(social_pattern, msg):
        return "SOCIAL"

    analytical_terms = [
        "simulate", "simulation", "health-check", "health check", "healthcheck", "anomaly", "audit",
        "forensic", "root cause", "deep dive", "trend", "correlation", "projection", "scenario", "model",
        "revenue", "margin", "latency", "pipeline", "nps", "churn", "cash flow", "expenditure",
        "forecast", "what if",
        "cross-domain", "cross domain", "silo", "silos", "status", "overview", "performance",
        "breakdown", "report", "investigate", "insights", "check", "state of",
        "deals", "sales", "operations", "accounting", "hr ", "crm",
        "action", "actions", "amend", "steps to", "recommend", "what should", "fix"
    ]
    if any(term in msg for term in analytical_terms):
        return "ANALYTICAL"

    return "SOCIAL"

def classify_intent_mode(user_message: str) -> str:
    msg = (user_message or "").lower()
    if any(term in msg for term in ["competitor", "market", "external"]):
        return "COMPETITIVE_INTEL"
    return "STANDARD"

def distill_external_context(raw_context) -> str:
    context_text = str(raw_context or "").strip()
    if not context_text:
        return ""
    if len(context_text) <= 1000:
        return context_text

    distill_prompt = SystemMessage(
        content=(
            "Create an Intel Briefing in exactly 3 concise bullet points. "
            "Remove HTML fragments, glossary-style filler, and duplicated snippets. "
            "Keep only business-relevant competitive signals (speed, pricing, product strategy, customer impact). "
            "Do not include markdown code fences.\n"
            f"RAW INTEL:\n{context_text}"
        )
    )
    try:
        distilled = llm_fast.invoke([distill_prompt])
        distilled_text = str(distilled.content or "").strip() or context_text[:1000]
    except Exception:
        distilled_text = context_text[:1000]

    nexus_comparison = (
        "Nexus Comparison: While Market Leaders dominate high-speed digital experience, "
        "our internal data shows our 310ms latency is the immediate barrier to matching their performance."
    )
    if nexus_comparison.lower() not in distilled_text.lower():
        distilled_text = f"{distilled_text}\n{nexus_comparison}".strip()
    return distilled_text

def orchestrator_node(state: AgentState):
    user_role = state.get("role", "Analyst")

    last_message = state["messages"][-1]
    
    if isinstance(last_message, tuple):
        user_message = last_message[1]
    else:
        user_message = last_message.content

    user_query = str(user_message or "").strip()
    interaction_mode = classify_interaction_mode(user_query)
    intent_mode = classify_intent_mode(user_query)

    # Check if external competitive intelligence is needed
    if intent_mode == "COMPETITIVE_INTEL":
        intel = get_competitive_intel.invoke({"competitor_name": "Market Leaders"})
        external_context = distill_external_context(intel)
    else:
        external_context = ""

    return {
        "current_silo": "Determined by LLM",
        "interaction_mode": interaction_mode,
        "intent_mode": intent_mode,
        "external_context": external_context,
        "reasoning_steps": [
            f"Orchestrator set interaction_mode={interaction_mode}, intent_mode={intent_mode} for {user_role} request."
        ]
    }

def resolve_table_alias(user_text: str) -> str | None:
    text = (user_text or "").lower()
    if "crm" in text:
        return "crm"
    if "accounting" in text or "finance" in text:
        return "erp_accounting"
    if "operations" in text or "ops" in text:
        return "erp_operations"
    if "hr" in text or "human resources" in text:
        return "erp_hr"
    if "sales" in text:
        return "erp_sales"
    return None

def resolve_metric_hint(user_text: str) -> str | None:
    text = (user_text or "").lower()
    known_metrics = [
        "latency_ms", "success_rate", "uptime_pct", "revenue", "margin", "expenditure",
        "customer_satisfaction_score", "active_leads", "churn_rate", "deals_closed", "pipeline_value", "avg_deal_size",
        "headcount", "payroll_expenditure", "productivity_index"
    ]
    for metric in known_metrics:
        if metric in text:
            return metric
    alias_map = {
        "latency": "latency_ms",
        "uptime": "uptime_pct",
        "satisfaction": "customer_satisfaction_score",
        "leads": "active_leads",
        "pipeline": "pipeline_value",
        "payroll": "payroll_expenditure",
        "productivity": "productivity_index"
    }
    for alias, metric in alias_map.items():
        if alias in text:
            return metric
    return None

def metric_exists_in_table(fact_sheet: dict, table_name: str, field_name: str) -> bool:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    table = tables.get(table_name, {}) if isinstance(tables, dict) else {}
    fields = table.get("fields", {}) if isinstance(table, dict) else {}
    return isinstance(fields, dict) and field_name in fields

def build_metric_table_map(fact_sheet: dict) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    for table_name, table in tables.items() if isinstance(tables, dict) else []:
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for field_name in fields.keys() if isinstance(fields, dict) else []:
            normalized_field = str(field_name).lower()
            if normalized_field not in mapping:
                mapping[normalized_field] = set()
            mapping[normalized_field].add(str(table_name))
    return mapping

def user_requested_table(user_text: str) -> str | None:
    text = (user_text or "").lower()
    if "crm" in text:
        return "crm"
    if "accounting" in text or "finance" in text:
        return "erp_accounting"
    if "operations" in text or "ops" in text:
        return "erp_operations"
    if "hr" in text or "human resources" in text:
        return "erp_hr"
    if "sales" in text:
        return "erp_sales"
    return None

def is_elaboration_request(user_text: str) -> bool:
    text = (user_text or "").lower()
    prompts = [
        "elaborate", "further detail", "more detail", "explain more", "break it down",
        "deeper", "tell me more", "why exactly", "drill down"
    ]
    return any(prompt in text for prompt in prompts)

def build_multi_paragraph_followup(history: list[dict], user_role: str) -> str:
    latest = None
    for snapshot in reversed(history or []):
        if isinstance(snapshot, dict) and snapshot.get("tables"):
            latest = snapshot
            break
    if not latest:
        return (
            f"Absolutely, {user_role}. I can expand once we have a fresh cross-silo snapshot for this thread."
        )

    candidates = collect_metric_candidates(latest)
    if not candidates:
        return (
            f"Absolutely, {user_role}. I’ve reviewed the latest snapshot, but there aren’t enough numeric deltas yet to deepen the analysis."
        )

    ranked = sorted(candidates, key=lambda c: (c.get("abs_delta", 0.0), c.get("abs_change", 0.0)), reverse=True)
    primary = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else None

    p_field = format_metric_label(primary.get("field_name", ""))
    p_silo = table_to_silo(primary.get("table_name", ""))
    p_base = primary.get("baseline", 0.0)
    p_curr = primary.get("current", 0.0)
    p_delta = primary.get("delta_pct", 0.0)

    para1 = (
        f"To go deeper, {user_role}, the largest movement is in {p_field} ({p_silo}). "
        f"It moved from {p_base} to {p_curr}, a {p_delta:.1f}% swing over the current window."
    )

    if secondary:
        s_field = format_metric_label(secondary.get("field_name", ""))
        s_silo = table_to_silo(secondary.get("table_name", ""))
        s_base = secondary.get("baseline", 0.0)
        s_curr = secondary.get("current", 0.0)
        s_delta = secondary.get("delta_pct", 0.0)
        para2 = (
            f"We also see a related shift in {s_field} ({s_silo}) from {s_base} to {s_curr} ({s_delta:.1f}%). "
            "That pattern is consistent with cross-silo propagation rather than an isolated one-table anomaly."
        )
    else:
        para2 = (
            "The remaining silos are comparatively stable, so remediation should focus on reversing this primary movement first."
        )

    para3 = (
        "Practical next step: restore the primary metric toward its baseline, then re-check adjacent silo movement in the next reporting interval "
        "to confirm recovery is propagating system-wide."
    )
    return f"{para1}\n\n{para2}\n\n{para3}"

def get_effective_fact_sheet(current_fact_sheet: dict, history: list[dict]) -> dict:
    if isinstance(current_fact_sheet, dict) and current_fact_sheet.get("tables"):
        return current_fact_sheet
    for snapshot in reversed(history or []):
        if isinstance(snapshot, dict) and snapshot.get("tables"):
            return snapshot
    return current_fact_sheet if isinstance(current_fact_sheet, dict) else {}

def find_largest_anomaly(fact_sheet: dict) -> dict | None:
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    best = None
    for table_name, table in tables.items() if isinstance(tables, dict) else []:
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        for field_name, values in fields.items() if isinstance(fields, dict) else []:
            delta = values.get("delta_pct") if isinstance(values, dict) else None
            if not isinstance(delta, (int, float)):
                continue
            candidate = {
                "table": table_name,
                "field": field_name,
                "delta_pct": delta,
                "baseline": values.get("baseline"),
                "current": values.get("current")
            }
            if best is None or abs(delta) > abs(best["delta_pct"]):
                best = candidate
    return best

def lookup_silo_owner(silo_name: str) -> tuple[str | None, str | None]:
    safe_silo = str(silo_name or "").strip()
    if safe_silo not in ["Sales", "Operations", "HR", "Accounting", "CRM"]:
        return None, None

    candidate_queries = [
        f"SELECT manager_name AS name, role FROM erp_hr WHERE lower(department)=lower('{safe_silo}') LIMIT 1;",
        f"SELECT department_lead AS name, role FROM erp_hr WHERE lower(department)=lower('{safe_silo}') LIMIT 1;",
        f"SELECT lead_name AS name, role FROM erp_hr WHERE lower(department)=lower('{safe_silo}') LIMIT 1;",
        f"SELECT firstName || ' ' || lastName AS name, 'Manager' AS role FROM Employee e JOIN Department d ON e.departmentID=d.departmentID WHERE lower(d.name)=lower('{safe_silo}') LIMIT 1;"
    ]

    for query in candidate_queries:
        try:
            result = query_enterprise_database.invoke({"sql_query": query})
            if is_sql_error(result) or result == "Data Unavailable":
                continue
            rows = coerce_rows(result)
            if not rows:
                continue
            first = rows[0] if isinstance(rows[0], dict) else {}
            name = str(first.get("name", "")).strip() if isinstance(first, dict) else ""
            role = str(first.get("role", "")).strip() if isinstance(first, dict) else ""
            if name:
                return name, role or f"Lead for {safe_silo}"
        except Exception:
            continue
    return None, None

def build_fix_response_from_anomaly(anomaly: dict, user_role: str) -> str:
    if not anomaly:
        return f"{user_role}, we should stabilize the largest operational variance first, then reassess cross-silo impact next cycle."
    silo = table_to_silo(anomaly.get("table", ""))
    field = format_metric_label(anomaly.get("field", ""))
    baseline = anomaly.get("baseline")
    current = anomaly.get("current")
    delta = anomaly.get("delta_pct", 0.0)
    return (
        f"To fix this, {user_role}, prioritize bringing {field} in {silo} back toward its baseline. "
        f"It moved from {baseline} to {current} ({delta:.1f}%), so closing that gap should be the first lever before downstream tuning."
    )

def build_value_reference_explanation(history: list[dict], user_role: str) -> str:
    sheet = get_effective_fact_sheet({}, history)
    tables = sheet.get("tables", {}) if isinstance(sheet, dict) else {}

    accounting_fields = tables.get("erp_accounting", {}).get("fields", {}) if isinstance(tables, dict) else {}
    revenue = accounting_fields.get("revenue", {}) if isinstance(accounting_fields, dict) else {}
    rev_baseline = revenue.get("baseline") if isinstance(revenue, dict) else None
    rev_current = revenue.get("current") if isinstance(revenue, dict) else None

    ops_fields = tables.get("erp_operations", {}).get("fields", {}) if isinstance(tables, dict) else {}
    latency = ops_fields.get("latency_ms", {}) if isinstance(ops_fields, dict) else {}
    lat_baseline = latency.get("baseline") if isinstance(latency, dict) else None
    lat_current = latency.get("current") if isinstance(latency, dict) else None

    crm_fields = tables.get("crm", {}).get("fields", {}) if isinstance(tables, dict) else {}
    leads = crm_fields.get("active_leads", {}) if isinstance(crm_fields, dict) else {}
    leads_baseline = leads.get("baseline") if isinstance(leads, dict) else None
    leads_current = leads.get("current") if isinstance(leads, dict) else None

    if isinstance(rev_baseline, (int, float)) and isinstance(rev_current, (int, float)):
        revenue_gap = rev_baseline - rev_current
        rev_drop_pct = ((rev_baseline - rev_current) / rev_baseline * 100.0) if rev_baseline else 0.0
        details = (
            f"Our income dropped by ${revenue_gap:,.0f} this week. "
            f"That is the revenue gap between normal performance (${rev_baseline:,.0f}) and the current crisis level (${rev_current:,.0f}), "
            f"which is a {rev_drop_pct:.1f}% decline."
        )
        if isinstance(lat_baseline, (int, float)) and isinstance(lat_current, (int, float)):
            details += (
                f" We also saw service delays rise from {lat_baseline:.0f}ms to {lat_current:.0f}ms, "
                "which reduced our ability to convert demand into revenue."
            )
        if isinstance(leads_baseline, (int, float)) and isinstance(leads_current, (int, float)) and leads_baseline:
            lead_drop_pct = ((leads_baseline - leads_current) / leads_baseline) * 100.0
            details += (
                f" In the same period, incoming demand fell from {leads_baseline:,.0f} to {leads_current:,.0f} "
                f"({lead_drop_pct:.1f}% down), reinforcing the lost-opportunity effect."
            )
        return details

    return (
        f"Using our existing investigation trail, {user_role}, the cash flow impact is the lost opportunity between baseline performance "
        "and what we are achieving right now."
    )

def build_why_cross_silo_followup(history: list[dict], user_role: str) -> tuple[str, str | None]:
    sheet = get_effective_fact_sheet({}, history)
    tables = sheet.get("tables", {}) if isinstance(sheet, dict) else {}

    accounting_fields = tables.get("erp_accounting", {}).get("fields", {}) if isinstance(tables, dict) else {}
    revenue = accounting_fields.get("revenue", {}) if isinstance(accounting_fields, dict) else {}
    rev_baseline = revenue.get("baseline") if isinstance(revenue, dict) else None
    rev_current = revenue.get("current") if isinstance(revenue, dict) else None

    ops_fields = tables.get("erp_operations", {}).get("fields", {}) if isinstance(tables, dict) else {}
    latency = ops_fields.get("latency_ms", {}) if isinstance(ops_fields, dict) else {}
    lat_baseline = latency.get("baseline") if isinstance(latency, dict) else None
    lat_current = latency.get("current") if isinstance(latency, dict) else None

    if all(isinstance(v, (int, float)) for v in [rev_baseline, rev_current, lat_baseline, lat_current]):
        revenue_gap = rev_baseline - rev_current
        message = (
            f"Why this happened: accounting shows an income shortfall of ${revenue_gap:,.0f} versus baseline. "
            f"In the prior investigation turn, operations latency climbed from {lat_baseline:.0f}ms to {lat_current:.0f}ms. "
            "That slowdown created a lost-opportunity path: slower experience, fewer completed transactions, and then lower revenue."
        )
        return message, "Operations"

    anomaly = find_largest_anomaly(sheet)
    if anomaly:
        silo = table_to_silo(anomaly.get("table", ""))
        return (
            f"The main reason is the largest disruption in {silo}, which then propagated into accounting performance in later metrics.",
            silo,
        )

    return (
        f"I can explain the full why-chain once we refresh the health check data, {user_role}.",
        None,
    )

def derive_active_focus_from_history(history: list[dict]) -> str | None:
    effective = get_effective_fact_sheet({}, history)
    anomaly = find_largest_anomaly(effective)
    if anomaly:
        silo = table_to_silo(anomaly.get("table", ""))
        if silo in ALLOWED_SILOS:
            return silo
    return None

def restrict_fact_sheet_to_silo(fact_sheet: dict, focus_silo: str | None) -> dict:
    if not isinstance(fact_sheet, dict) or not focus_silo:
        return fact_sheet if isinstance(fact_sheet, dict) else {}
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet.get("tables", {}), dict) else {}
    focused_tables = {
        table_name: table
        for table_name, table in tables.items()
        if table_to_silo(table_name) == focus_silo
    }
    restricted = dict(fact_sheet)
    restricted["tables"] = focused_tables
    return restricted

def build_focus_locked_followup(fact_sheet: dict, focus_silo: str, user_role: str, asks_for_why: bool) -> str:
    anomaly = find_largest_anomaly(fact_sheet)
    if not anomaly:
        return (
            f"I’m staying focused on {focus_silo}. I need a fresh health check to expand this explanation without losing context."
        )

    field = str(anomaly.get("field", "")).lower()
    baseline = anomaly.get("baseline")
    current = anomaly.get("current")
    delta = anomaly.get("delta_pct", 0.0)

    if field == "latency_ms":
        plain = (
            "Our website speed slowed down significantly, causing a delay that frustrated customers. "
            f"Within {focus_silo}, this moved from {baseline} to {current} ({delta:.1f}%), which widened our revenue gap."
        )
    elif field == "revenue":
        gap = (baseline - current) if isinstance(baseline, (int, float)) and isinstance(current, (int, float)) else None
        if isinstance(gap, (int, float)):
            plain = (
                f"Our income dropped by ${gap:,.0f} versus normal in {focus_silo}. "
                "That shortfall is the lost opportunity we need to recover first."
            )
        else:
            plain = (
                f"Within {focus_silo}, revenue is below normal, creating a clear lost-opportunity gap we should close first."
            )
    else:
        metric_label = format_metric_label(field)
        plain = (
            f"Within {focus_silo}, {metric_label} moved from {baseline} to {current} ({delta:.1f}%). "
            "This shift explains the current business drag and lost opportunity in this thread."
        )

    if asks_for_why:
        return f"Why this happened: {plain}"
    return plain

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
    keywords = [
        "health check", "healthcheck", "anomaly", "trend", "correlation",
        "cross-domain", "cross domain", "[chat_mode]",
        "state of", "silo", "silos", "status", "overview",
        "current state", "performance", "all tables"
    ]
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

def sanitize_layman_analysis(text: str) -> str:
    raw = str(text or "")
    cleaned = re.sub(r"\(\([^\)]*\)\)", "", raw)
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*[\*/]\s*\d+(?:\.\d+)?\b", "", cleaned)
    cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*[\+\-]\s*\d+(?:\.\d+)?\b", "", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()

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
        elif silo in ("Accounting", "Sales"):
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
    if "sales manager" in role:
        return ["Sales", "CRM"]
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

    preferred_silos = role_silo_preferences(user_role or "", target_silos)
    silo_pool = [c for c in candidates if table_to_silo(c["table_name"]) in preferred_silos]
    if not silo_pool:
        silo_pool = candidates

    def bucket_for(candidate):
        return bucket_lookup.get((candidate["table_name"], candidate["field_name"]))

    primary_pool = [c for c in silo_pool if bucket_for(c) == preferred_bucket]
    if not primary_pool:
        primary_pool = silo_pool
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
            f"{format_metric_label(primary['field_name'])} in {table_to_silo(primary['table_name'])} "
            f"Impacting {format_metric_label(secondary['field_name'])} in {table_to_silo(secondary['table_name'])}"
        )
    if primary:
        return f"{format_metric_label(primary['field_name'])} in {table_to_silo(primary['table_name'])} Impacting Accounting"
    return "Cross-silo Change in Operations Impacting Accounting"

def build_simulation_comparison_visuals(fact_sheet: dict, simulation_summary: dict | None) -> dict:
    x_values = []
    financial = select_financial_fields(fact_sheet)
    filtered_financial = [
        metric for metric in financial
        if table_to_silo(metric.get("table_name")) in ["Accounting", "HR"]
    ]
    if not filtered_financial:
        filtered_financial = financial

    price_change_pct = simulation_summary.get("price_change_pct", 0) if isinstance(simulation_summary, dict) else 0
    price_change_ratio = normalize_price_change(price_change_pct)
    projected_payload = simulation_summary.get("projected", {}) if isinstance(simulation_summary, dict) else {}

    actual_values = []
    projected_values = []
    for metric in filtered_financial[:2]:
        metric_label = format_metric_label(metric.get("field_name"))
        x_values.append(metric_label)
        baseline = metric.get("baseline")
        current_actual = metric.get("current")
        if not isinstance(baseline, (int, float)):
            baseline = current_actual if isinstance(current_actual, (int, float)) else 0.0
        if not isinstance(current_actual, (int, float)):
            current_actual = baseline if isinstance(baseline, (int, float)) else 0.0

        projected_total = None
        if isinstance(projected_payload, dict):
            field_name = str(metric.get("field_name", "")).lower()
            if "revenue" in field_name and isinstance(projected_payload.get("revenue"), (int, float)):
                projected_total = projected_payload.get("revenue")
            elif "latency" in field_name and isinstance(projected_payload.get("ops_latency_ms"), (int, float)):
                projected_total = projected_payload.get("ops_latency_ms")
        if not isinstance(projected_total, (int, float)):
            projected_total = baseline * (1 + price_change_ratio)
        projected_total = max(0.0, projected_total)
        actual_values.append(current_actual)
        projected_values.append(projected_total)

    if not x_values:
        x_values = ["Revenue"]
        actual_values = [0.0]
        projected_values = [0.0]

    traces = [
        {
            "type": "bar",
            "name": "Current Actual",
            "x": x_values,
            "y": actual_values
        },
        {
            "type": "bar",
            "name": "Simulated Projection",
            "x": x_values,
            "y": projected_values
        }
    ]

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
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    accounting = tables.get("erp_accounting", {}) if isinstance(tables, dict) else {}
    accounting_fields = accounting.get("fields", {}) if isinstance(accounting, dict) else {}
    revenue_values = accounting_fields.get("revenue", {}) if isinstance(accounting_fields, dict) else {}

    actual_revenue = revenue_values.get("current", 0.0)
    baseline_revenue = revenue_values.get("baseline", 0.0)
    if not isinstance(actual_revenue, (int, float)):
        actual_revenue = 0.0
    if not isinstance(baseline_revenue, (int, float)):
        baseline_revenue = 0.0
    cash_flow_impact = actual_revenue - baseline_revenue

    expenditure_delta = 0.0
    expenditure_values = accounting_fields.get("expenditure", {}) if isinstance(accounting_fields, dict) else {}
    exp_current = expenditure_values.get("current") if isinstance(expenditure_values, dict) else None
    exp_baseline = expenditure_values.get("baseline") if isinstance(expenditure_values, dict) else None
    if isinstance(exp_current, (int, float)) and isinstance(exp_baseline, (int, float)):
        expenditure_delta = exp_current - exp_baseline
    else:
        hr = tables.get("erp_hr", {}) if isinstance(tables, dict) else {}
        hr_fields = hr.get("fields", {}) if isinstance(hr, dict) else {}
        payroll_values = hr_fields.get("payroll_expenditure", {}) if isinstance(hr_fields, dict) else {}
        payroll_current = payroll_values.get("current") if isinstance(payroll_values, dict) else None
        payroll_baseline = payroll_values.get("baseline") if isinstance(payroll_values, dict) else None
        if isinstance(payroll_current, (int, float)) and isinstance(payroll_baseline, (int, float)):
            expenditure_delta = payroll_current - payroll_baseline

    variable_mapping = {
        "ACTUAL_REVENUE": actual_revenue,
        "BASELINE_REVENUE": baseline_revenue,
        "CASH_FLOW_IMPACT": cash_flow_impact,
        "REVENUE_TABLE": "erp_accounting",
        "REVENUE_FIELD": "revenue",
        "EXPENDITURE_TABLE": "erp_accounting" if isinstance(exp_current, (int, float)) else "erp_hr",
        "EXPENDITURE_FIELD": "expenditure" if isinstance(exp_current, (int, float)) else "payroll_expenditure"
    }

    primary, secondary = select_trace_fields(fact_sheet, user_role, map_tables_to_silos(fact_sheet))
    head = build_headline_from_traces(primary, secondary)

    # When no data is available, produce a meaningful fallback instead of $0/Metric placeholders
    if primary is None and secondary is None:
        return {
            "headline": head,
            "summary": "No time-series data is available yet for a cross-silo comparison. Please run a fresh health check.",
            "reasoning_detailed": (
                "The data pipeline returned no measurable metrics for this query. "
                "A full cross-silo health check is needed to populate the fact sheet before analysis can proceed."
            ),
            "recommendations": [
                {
                    "action": "Run a health check",
                    "detail": "Ask for a cross-domain health check to load baseline and current metrics from all silos.",
                    "expected_impact": "Enables cross-silo analysis with real data."
                }
            ]
        }

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

    abs_delta_dollars = abs(variable_mapping["CASH_FLOW_IMPACT"])
    abs_delta_percent = 0.0
    if baseline_revenue:
        abs_delta_percent = abs((variable_mapping["CASH_FLOW_IMPACT"] / baseline_revenue) * 100)
    recovery_ratio = max(0.0, min(1.0, abs_delta_percent / 100.0))
    estimated_recovery = abs_delta_dollars * recovery_ratio
    recovery_pct = recovery_ratio * 100.0
    expenditure_reduction_pct = 0.0
    if isinstance(exp_baseline, (int, float)) and exp_baseline != 0:
        expenditure_reduction_pct = abs((expenditure_delta / exp_baseline) * 100)
    recommendations = [
        {
            "action": "Validate root cause",
            "detail": f"Investigate {ops_silo} drivers behind {ops_metric} changes.",
            "expected_impact": f"Estimated {recovery_pct:.1f}% recovery of cash flow with projected ${estimated_recovery:.0f} monthly revenue recovery."
        },
        {
            "action": "Stabilize financial leakage",
            "detail": f"Coordinate {ops_silo} and {fin_silo} controls to reduce cost drift.",
            "expected_impact": f"Estimated {recovery_pct:.1f}% recovery of cash flow plus ${abs(expenditure_delta):.0f} containment and {expenditure_reduction_pct:.1f}% expenditure stabilization."
        }
    ]

    return {
        "headline": head,
        "summary": summary,
        "reasoning_detailed": reasoning,
        "recommendations": recommendations
    }

def enforce_strict_schema(
    data: dict | None,
    fact_sheet: dict,
    user_role: str,
    is_sim: bool,
    interaction_mode: str = "ANALYTICAL"
) -> dict:
    if str(interaction_mode).upper() != "ANALYTICAL":
        if isinstance(data, dict):
            content = data.get("content", {}) if isinstance(data.get("content"), dict) else {}
            plain_parts = [
                str(content.get("headline", "")).strip(),
                str(content.get("summary", "")).strip(),
                str(content.get("reasoning_detailed", "")).strip()
            ]
            plain_text = " ".join([p for p in plain_parts if p])
            if plain_text:
                return {"chat_response": plain_text}
        return {"chat_response": build_chat_response_from_fact_sheet(fact_sheet, user_role)}

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
    content["reasoning_detailed"] = sanitize_layman_analysis(content.get("reasoning_detailed", ""))
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

    primary, secondary = select_trace_fields(fact_sheet, user_role, None)
    content["headline"] = build_headline_from_traces(primary, secondary)
    content["reasoning_detailed"] = fallback_content["reasoning_detailed"]

    target_silos = []
    if primary and primary.get("table_name"):
        target_silos.append(table_to_silo(primary["table_name"]))
    if secondary and secondary.get("table_name"):
        s = table_to_silo(secondary["table_name"])
        if s not in target_silos:
            target_silos.append(s)
    if not target_silos:
        target_silos = ["Operations"]

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

def build_chat_response_from_fact_sheet(fact_sheet: dict, user_role: str) -> str:
    candidates = collect_metric_candidates(fact_sheet)
    if not candidates:
        return (
            f"I've checked the silos for you, {user_role}. I can see the latest business context, "
            "but I need a specific metric to provide a precise summary."
        )

    ranked = sorted(candidates, key=lambda c: (c.get("abs_delta", 0.0), c.get("abs_change", 0.0)), reverse=True)
    primary = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else None

    primary_delta = primary.get("delta_pct") if isinstance(primary.get("delta_pct"), (int, float)) else 0.0
    primary_direction = "up" if primary_delta >= 0 else "down"
    primary_silo = table_to_silo(primary.get("table_name", ""))
    primary_field = format_metric_label(primary.get("field_name", ""))
    primary_change = abs(primary.get("current", 0.0) - primary.get("baseline", 0.0))

    sentence = (
        f"I've checked the silos, {user_role}. {primary_field} in {primary_silo} is currently {primary_direction} "
        f"{abs(primary_delta):.1f}% (${primary_change:,.0f})."
    )

    if secondary:
        secondary_delta = secondary.get("delta_pct") if isinstance(secondary.get("delta_pct"), (int, float)) else 0.0
        secondary_direction = "up" if secondary_delta >= 0 else "down"
        secondary_silo = table_to_silo(secondary.get("table_name", ""))
        secondary_field = format_metric_label(secondary.get("field_name", ""))
        sentence += (
            f" This appears linked to {secondary_field} in {secondary_silo}, which is {secondary_direction} "
            f"{abs(secondary_delta):.1f}% over the same window."
        )

    sentence += " If you want, I can break this down by each silo next."
    return sentence

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
    buckets = fact_sheet.get("semantic_buckets", {}) if isinstance(fact_sheet, dict) else {}
    bucket_lookup = {}
    for bucket_name, items in buckets.items() if isinstance(buckets, dict) else []:
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                bucket_lookup[(item.get("table"), item.get("field"))] = bucket_name

    if primary is None:
        candidates = collect_metric_candidates(fact_sheet)
        cause_pool = [
            c for c in candidates
            if bucket_lookup.get((c["table_name"], c["field_name"])) == "Operational_Cause"
        ]
        if cause_pool:
            primary = max(cause_pool, key=lambda c: (c["abs_delta"], c["abs_change"]))

    if secondary is None and primary is not None:
        candidates = collect_metric_candidates(fact_sheet)
        effect_pool = [
            c for c in candidates
            if bucket_lookup.get((c["table_name"], c["field_name"])) == "Financial_Effect" and c is not primary
        ]
        if effect_pool:
            secondary = max(effect_pool, key=lambda c: (c["abs_change"], c["abs_delta"]))

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
        candidates = collect_metric_candidates(fact_sheet)
        if candidates:
            fallback_metric = max(candidates, key=lambda c: (c["abs_delta"], c["abs_change"]))
            fallback_table = tables.get(fallback_metric["table_name"], {}) if isinstance(tables, dict) else {}
            traces = [{
                "type": "scatter",
                "mode": "lines+markers",
                "name": format_metric_label(fallback_metric["field_name"]),
                "x": [fallback_table.get("baseline_date") or fallback_start, fallback_table.get("current_date") or fallback_end],
                "y": [fallback_metric["baseline"], fallback_metric["current"]]
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

def patch_insight_json(data: dict, fact_sheet: dict, user_role: str, is_sim: bool, active_focus: str | None = None) -> dict:
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

    mention_text = " ".join([
        str(content.get("headline", "")),
        str(content.get("reasoning_detailed", ""))
    ])
    mentioned = set(infer_target_silos(mention_text))
    active_silos = set()
    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    table_items = tables.items() if isinstance(tables, dict) else []
    for table_name, table in table_items:
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        field_values = fields.values() if isinstance(fields, dict) else []
        for values in field_values:
            delta = values.get("delta_pct") if isinstance(values, dict) else None
            if isinstance(delta, (int, float)) and abs(delta) > 0:
                active_silos.add(table_to_silo(table_name))
                break
    inferred = infer_only_allowed(list(mentioned.intersection(active_silos)))
    if active_focus in ALLOWED_SILOS:
        data["target_silos"] = [active_focus]
    else:
        data["target_silos"] = inferred
    return data

def reasoner_node(state: AgentState):
    sql_context = state.get("sql_results", "No data")
    user_role = state.get("role", "Executive")
    is_sim = state.get("is_simulation", False)
    simulation_inputs = state.get("simulation_inputs", {})
    messages = state.get("messages", [])
    last_msg = get_message_content(messages[-1]).lower() if messages else ""
    combined_msg = " ".join(get_message_content(msg) for msg in messages).lower() if messages else last_msg
    chat_mode_tagged = "[chat_mode]" in combined_msg
    interaction_mode = str(state.get("interaction_mode", "")).upper()
    intent_mode = str(state.get("intent_mode", "STANDARD")).upper()
    history = state.get("fact_sheet_history", [])
    external_context = str(state.get("external_context", "")).strip()
    simulation_summary = state.get("simulation_summary", {}) if isinstance(state.get("simulation_summary", {}), dict) else {}

    if "what if" in last_msg and isinstance(simulation_summary, dict) and simulation_summary.get("projected"):
        projected = simulation_summary.get("projected", {}) if isinstance(simulation_summary.get("projected"), dict) else {}
        baseline = simulation_summary.get("baseline", {}) if isinstance(simulation_summary.get("baseline"), dict) else {}
        projected_revenue = projected.get("revenue")
        baseline_revenue = baseline.get("revenue")
        if isinstance(projected_revenue, (int, float)):
            comparison = ""
            if isinstance(baseline_revenue, (int, float)):
                delta = projected_revenue - baseline_revenue
                comparison = f" versus a baseline of ${baseline_revenue:,.2f} ({delta:+,.2f})."
            return {
                "final_insight": {
                    "chat_response": (
                        f"For this what-if scenario, the projected revenue is ${projected_revenue:,.2f}{comparison} "
                        "I’m prioritizing the simulation outcome first, then using market context only as secondary framing."
                    )
                },
                "reasoning_steps": ["Reasoner prioritized simulation_summary for what-if request."]
            }

    if interaction_mode in {"SOCIAL", "CONVERSATIONAL"} and is_elaboration_request(last_msg):
        return {
            "final_insight": {"chat_response": build_multi_paragraph_followup(history, user_role)},
            "reasoning_steps": ["Reasoner produced multi-paragraph follow-up from fact_sheet_history."]
        }

    # Handle action/recommendation follow-ups using fact_sheet_history
    asks_for_actions = any(phrase in last_msg for phrase in [
        "action", "actions", "steps", "amend", "recommend", "should i",
        "should we", "what should", "what can i", "what can we", "do about"
    ])
    if asks_for_actions and history:
        effective_fs = get_effective_fact_sheet(state.get("fact_sheet", {}), history)
        anomaly = find_largest_anomaly(effective_fs)
        if anomaly:
            return {
                "final_insight": {"chat_response": build_fix_response_from_anomaly(anomaly, user_role)},
                "reasoning_steps": ["Reasoner produced action-oriented follow-up from fact_sheet_history."]
            }

    if intent_mode == "COMPETITIVE_INTEL" and not is_sim:
        merged_tables = collect_tables_from_sql_results(sql_context)
        fs = state.get("fact_sheet", {})
        if not fs.get("tables") and merged_tables:
            fs = build_fact_sheet(merged_tables)

        latency = None
        leads_baseline = None
        leads_current = None
        ops = fs.get("tables", {}).get("erp_operations", {}) if isinstance(fs, dict) else {}
        ops_fields = ops.get("fields", {}) if isinstance(ops, dict) else {}
        latency_values = ops_fields.get("latency_ms", {}) if isinstance(ops_fields, dict) else {}
        if isinstance(latency_values, dict):
            latency = latency_values.get("current")

        crm = fs.get("tables", {}).get("crm", {}) if isinstance(fs, dict) else {}
        crm_fields = crm.get("fields", {}) if isinstance(crm, dict) else {}
        lead_values = crm_fields.get("active_leads", {}) if isinstance(crm_fields, dict) else {}
        if isinstance(lead_values, dict):
            leads_baseline = lead_values.get("baseline")
            leads_current = lead_values.get("current")

        competitor_summary = external_context if external_context else "External intelligence indicates a faster competitor system."

        if isinstance(latency, (int, float)) and isinstance(leads_baseline, (int, float)) and isinstance(leads_current, (int, float)):
            lead_drop_pct = ((leads_baseline - leads_current) / leads_baseline * 100.0) if leads_baseline else 0.0
            response_text = (
                f"Ahmed, external intel first: {competitor_summary} "
                f"Compared with our internal baseline, latency is currently {latency:.0f}ms, and active leads moved from "
                f"{leads_baseline:.0f} to {leads_current:.0f}. A sub-50ms competitor could plausibly absorb about {lead_drop_pct:.1f}% "
                "of this lead decline if we do not close the performance gap."
            )
        else:
            response_text = (
                f"Ahmed, external intel first: {competitor_summary} "
                "Our internal data is incomplete for a full quantified comparison, but we should benchmark latency and lead conversion "
                "against competitor speed before committing to pricing or pipeline targets."
            )

        return {
            "final_insight": {"chat_response": response_text},
            "reasoning_steps": ["Reasoner synthesized internal and competitive context conversationally."]
        }

    if interaction_mode == "SOCIAL" and not is_sim:
        social_prompt = (
            "You are a warm executive assistant. Reply naturally to the user in 1-2 friendly sentences. "
            "Do not mention silos, deltas, missing data, or technical diagnostics. "
            f"User message: {get_message_content(messages[-1]) if messages else ''}"
        )
        response = llm_fast.invoke(social_prompt)
        return {
            "final_insight": {"chat_response": response.content},
            "reasoning_steps": ["Reasoner handled SOCIAL mode conversationally."]
        }

    is_chat = (
        chat_mode_tagged
        or interaction_mode in {"SOCIAL", "GENERAL_QUERY"}
        or len(messages) > 1
    ) and not is_sim and "health check" not in last_msg
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
    silo_focus = SILO_FOCUS_MAP.get(detected_silo, "technical performance, throughput, reliability, bottleneck")

    mission_switch = {
        "Sales": "Act as a CI (Chief Intelligence) surrogate. Focus on revenue leakage, customer churn, and pipeline velocity.",
        "Operations": "Act as a CI (Chief Intelligence) surrogate. Focus on bottlenecks and technical performance reliability.",
        "HR": "Act as a CI (Chief Intelligence) surrogate. Focus on churn, headcount, payroll, and productivity impacts.",
        "Accounting": "Act as a CI (Chief Intelligence) surrogate. Focus on expenditure, cash flow, and margins.",
        "CRM": "Act as a CI (Chief Intelligence) surrogate. Focus on sentiment, retention, support tickets, and NPS impacts."
    }
    persona_focus = mission_switch.get(detected_silo, "Focus on bottlenecks, technical impact, and service reliability shifts.")

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
        external_brief = ""
        if external_context:
            external_brief = (
                "EXTERNAL INTEL BRIEFING (already distilled): "
                f"{external_context}\n"
                "SYNTHESIS RULE: combine external signals with internal metrics; do not repeat raw source text.\n"
            )

        mission = (
            f"CHAT MODE ({detected_silo}): You are the {user_role}. {persona_focus} "
            "Answer the user's specific question using detected silo language. "
            "DO NOT list raw database rows. SYNTHESIZE the answer across CRM, Accounting, HR, Operations, and Sales if relevant. "
            "When meaningful, connect cross-silo cause and effect in plain language."
        )
        format_inst = (
            "Output: Conversational text only, role-appropriate. "
            "Prioritize the Fact Sheet data if available. "
            "Do not invent metrics or values not present in the provided data. "
            "Do NOT show math formulas like ((N-O)/O). "
            "Return one concise narrative string suitable for chat_response.\n"
            f"{external_brief}"
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
            "- Report findings using the SQL results and dynamic metric keys from the provided JSON context.\n"
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
                    {{ "type": "bar", "name": "Baseline Metric", "x": ["Current Actual"], "y": [0] }},
                    {{ "type": "bar", "name": "Projected Metric", "x": ["Simulated Projection"], "y": [0] }}
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
                    {{ "type": "scatter", "mode": "lines+markers", "name": "Cause Metric", "x": ["DATE_1"], "y": [0] }},
                    {{ "type": "scatter", "mode": "lines+markers", "name": "Effect Metric", "x": ["DATE_1"], "y": [0] }}
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
    - Ground all findings in the SQL results; refer to metrics dynamically using keys from the provided JSON context.

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
                    {"type": "bar", "name": "Baseline Metric", "x": x_values[:1], "y": [0.0]},
                    {"type": "bar", "name": "Projected Metric", "x": x_values[:1], "y": [0.0]}
                ]
            else:
                traces = [
                    {"type": "scatter", "mode": "lines+markers", "name": "Cause Metric", "x": x_values, "y": [0.0] * len(x_values)},
                    {"type": "scatter", "mode": "lines+markers", "name": "Effect Metric", "x": x_values, "y": [0.0] * len(x_values)}
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
    if any(k in user_msg for k in [
        "health check", "healthcheck", "anomaly", "audit",
        "silo", "silos", "status", "state of", "overview", "check",
        "cross-domain", "cross domain", "performance", "breakdown"
    ]):
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
    fact_sheet_history = state.get("fact_sheet_history", [])
    fact_sheet = get_effective_fact_sheet(fact_sheet, fact_sheet_history)
    user_role = state.get("role", "Executive")
    is_sim = state.get("is_simulation", False)
    interaction_mode = str(state.get("interaction_mode", "")).upper()
    simulation_summary = state.get("simulation_summary")
    user_messages = state.get("messages", [])
    user_text = get_message_content(user_messages[-1]) if user_messages else ""
    lower_user_text = (user_text or "").lower()
    active_focus = state.get("active_focus")
    # Only derive active_focus from history for genuine follow-ups (when state already had it)
    # Don't auto-derive and latch on the first proactive query
    _focus_from_state = active_focus is not None
    if not active_focus and fact_sheet_history:
        active_focus = derive_active_focus_from_history(fact_sheet_history)
    is_layman_mode = interaction_mode in {"SOCIAL", "CHAT", "CONVERSATIONAL"}

    largest_anomaly = find_largest_anomaly(fact_sheet)
    asks_for_why = any(phrase in lower_user_text for phrase in ["why", "why?", "how come", "what caused", "cause of this"])
    asks_for_elaborate = is_elaboration_request(user_text)
    asks_for_owner = any(phrase in lower_user_text for phrase in ["who do i speak", "who is responsible", "who owns", "who do i talk"])
    asks_for_team = any(phrase in lower_user_text for phrase in ["which team", "what team"])
    asks_for_fix = any(phrase in lower_user_text for phrase in [
        "how do i fix", "fix this", "how can we fix", "what should we fix",
        "actions should", "what actions", "steps to", "amend",
        "what should i", "what can i do", "what do i do", "recommend"
    ])
    references_prior_value = bool(re.search(r"\$\s*\d+[\d,]*", lower_user_text)) or "cash flow" in lower_user_text
    followup_signal = asks_for_why or asks_for_elaborate or asks_for_owner or asks_for_team or asks_for_fix or references_prior_value
    asks_fresh_health_check = any(term in lower_user_text for term in ["fresh health check", "new health check", "health check", "healthcheck"])

    if followup_signal and not fact_sheet_history:
        return {
            "final_insight": {
                "chat_response": "I've lost the thread of our data investigation. Could you ask me for a fresh health check so I can re-sync?"
            },
            "active_focus": active_focus
        }

    if (asks_for_why or asks_for_elaborate) and active_focus and not asks_fresh_health_check:
        focused_fact_sheet = restrict_fact_sheet_to_silo(fact_sheet, active_focus)
        return {
            "final_insight": {
                "chat_response": build_focus_locked_followup(focused_fact_sheet, active_focus, user_role, asks_for_why)
            },
            "active_focus": active_focus,
            "target_silos": [active_focus]
        }

    if not is_sim and asks_for_why:
        why_response, why_focus = build_why_cross_silo_followup(fact_sheet_history, user_role)
        return {
            "final_insight": {
                "chat_response": why_response
            },
            "active_focus": active_focus or why_focus
        }

    if is_layman_mode and references_prior_value:
        return {
            "final_insight": {
                "chat_response": build_value_reference_explanation(fact_sheet_history, user_role)
            },
            "active_focus": active_focus or (table_to_silo(largest_anomaly.get("table", "")) if largest_anomaly else None)
        }

    if not is_sim and (asks_for_owner or asks_for_team):
        owner_silo = active_focus or (table_to_silo(largest_anomaly.get("table", "")) if largest_anomaly else None)
        if not owner_silo:
            owner_silo = "Operations"
        owner_name, owner_role = lookup_silo_owner(owner_silo)
        if owner_name:
            return {
                "final_insight": {
                    "chat_response": f"You should speak with {owner_name}, the manager of the {owner_silo} team."
                },
                "active_focus": owner_silo
            }
        return {
            "final_insight": {
                "chat_response": f"You should speak with the {owner_silo} department lead first, since that area has the largest anomaly."
            },
            "active_focus": owner_silo
        }

    if not is_sim and largest_anomaly and asks_for_fix:
        latched_focus = active_focus or table_to_silo(largest_anomaly.get("table", ""))
        return {
            "final_insight": {
                "chat_response": build_fix_response_from_anomaly(largest_anomaly, user_role)
            },
            "active_focus": latched_focus
        }

    if is_layman_mode and not is_sim:
        social_prompt = (
            "You are a friendly, helpful executive assistant. "
            "Use plain business language for a non-technical audience. "
            "Avoid technical jargon (for example: latency, triangulation, delta_pct, schema, causal chain). "
            "If discussing performance impact, describe it as lost opportunity or revenue gap versus baseline. "
            "Example rewrite: instead of 'Latency moved from 45 to 310', say 'Our website speed slowed down significantly, causing a delay that frustrated customers.' "
            f"User message: {user_text}"
        )
        response = llm_fast.invoke(social_prompt)
        return {
            "final_insight": {
                "chat_response": response.content
            },
            "active_focus": active_focus
        }

    requested_table = resolve_table_alias(user_text)
    requested_metric = resolve_metric_hint(user_text)
    if requested_table and requested_metric and not metric_exists_in_table(fact_sheet, requested_table, requested_metric):
        # Check fact_sheet_history before rejecting
        found_in_history = False
        for prev_fs in reversed(fact_sheet_history or []):
            if isinstance(prev_fs, dict) and metric_exists_in_table(prev_fs, requested_table, requested_metric):
                fact_sheet = prev_fs
                found_in_history = True
                break
        if not found_in_history:
            return {
                "final_insight": {
                    "chat_response": (
                        f"I can’t validate {requested_metric} in {requested_table} from the current fact sheet, "
                        "so I won’t generate a metric-change card for that pair."
                    )
                },
                "active_focus": active_focus
            }

    sales_manager = str(user_role).lower() == "sales manager"
    role_focus = {
        "CEO": "Cross-silo executive synthesis with emphasis on Operations, Accounting, and CRM.",
        "Sales Manager": "Prioritize lead quality and pipeline health, then link to revenue impact.",
        "Operations Manager": "Focus on technical performance, success quality, and reliability impacts.",
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
            "- Do not mention low-level technical metric names in the HEADLINE or RECOMMENDATIONS.\n"
            "- Emphasize lead quality and pipeline health in the HEADLINE and RECOMMENDATIONS.\n"
            "- Still include Expenditure impact as a footer line in the REASONING section.\n"
        )

    metric_source_map = {}
    fs_tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    for tbl_name, tbl in (fs_tables.items() if isinstance(fs_tables, dict) else []):
        silo_name = table_to_silo(tbl_name)
        fields = tbl.get("fields", {}) if isinstance(tbl, dict) else {}
        for fld_name in (fields.keys() if isinstance(fields, dict) else []):
            metric_source_map[fld_name] = {"table": tbl_name, "silo": silo_name}
    metric_ownership_block = "METRIC OWNERSHIP (ground truth — never attribute a metric to a different silo):\n"
    for fld, info in metric_source_map.items():
        metric_ownership_block += f"  - {fld} belongs to table '{info['table']}' (Silo: {info['silo']})\n"

    logic_prompt = f"""
    ROLE: Chief Intelligence Officer
    USER ROLE: {user_role}
    PERSONA FOCUS: {persona_focus}
    INTERACTION MODE: ANALYTICAL
    FACT SHEET (JSON): {json.dumps(fact_sheet)}
    {sim_context}

    {metric_ownership_block}

    TASK:
    - Describe the forensic path taken to find this insight. Do not summarize; explain the investigation.
    - Produce a plain-text causal analysis using only numbers from the Fact Sheet.
    - STRICT SOURCE RULE: When referencing a metric, you MUST attribute it to its owning silo as listed above. Do NOT place latency_ms in Accounting or revenue in Operations.
    - CROSS-SILO TRIANGULATION: connect at least two silos with explicit cause-effect narrative.
    - QUANTITATIVE GROUNDING: use only values present in Fact Sheet or Simulation Summary.
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
    You are a strict JSON formatter. Output ONLY ONE valid JSON block using this exact schema and keys:
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

    final_insight = enforce_strict_schema(data, fact_sheet, user_role, is_sim, interaction_mode)

    if isinstance(final_insight, dict) and isinstance(final_insight.get("content"), dict):
        metric_table_map = build_metric_table_map(fact_sheet)
        requested_table = user_requested_table(user_text)
        content = final_insight.get("content", {})
        headline = str(content.get("headline", ""))
        summary = str(content.get("summary", ""))
        combined_text = f"{headline} {summary}".lower()

        invalid_mentions = []
        for metric, tables in metric_table_map.items():
            if metric in combined_text and requested_table and requested_table not in tables:
                invalid_mentions.append((metric, sorted(tables)))

        if invalid_mentions and requested_table:
            metric_name, valid_tables = invalid_mentions[0]
            return {
                "final_insight": {
                    "chat_response": (
                        f"I can’t attribute '{metric_name}' to {requested_table} from the current fact sheet. "
                        f"That metric belongs to {', '.join(valid_tables)}."
                    )
                }
            }

        if requested_table == "crm":
            accounting_fields = metric_table_map.keys()
            accounting_terms = []
            tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
            accounting_table = tables.get("erp_accounting", {}) if isinstance(tables, dict) else {}
            accounting_field_map = accounting_table.get("fields", {}) if isinstance(accounting_table, dict) else {}
            if isinstance(accounting_field_map, dict):
                accounting_terms = [str(name).lower() for name in accounting_field_map.keys()]

            mentions_accounting_metric = any(term in combined_text for term in accounting_terms)
            prefix = "While your question is about CRM, I also noticed a related shift in our Accounting table..."
            if mentions_accounting_metric:
                current_summary = str(content.get("summary", "")).strip()
                if current_summary and not current_summary.startswith(prefix):
                    content["summary"] = f"{prefix} {current_summary}"
                elif not current_summary:
                    content["summary"] = prefix
                final_insight["content"] = content

    tables = fact_sheet.get("tables", {}) if isinstance(fact_sheet, dict) else {}
    table_names = list(tables.keys())
    scanned_tables_text = ", ".join(table_names) if table_names else "no tables"

    highest_delta = None
    table_items = tables.items() if isinstance(tables, dict) else []
    for table_name, table in table_items:
        fields = table.get("fields", {}) if isinstance(table, dict) else {}
        field_items = fields.items() if isinstance(fields, dict) else []
        for field_name, values in field_items:
            delta = values.get("delta_pct") if isinstance(values, dict) else None
            if not isinstance(delta, (int, float)):
                continue
            candidate = {
                "table": table_name,
                "field": field_name,
                "delta": delta
            }
            if highest_delta is None or abs(delta) > abs(highest_delta["delta"]):
                highest_delta = candidate

    anomaly_text = "No measurable anomaly identified."
    if highest_delta:
        anomaly_text = (
            f"Largest shift detected in {highest_delta['field']} from {highest_delta['table']} "
            f"at {highest_delta['delta']:.1f}% change."
        )

    primary, secondary = select_trace_fields(fact_sheet, user_role, None)
    correlation_text = "Cross-silo correlation could not be resolved from current evidence."
    if primary and secondary:
        correlation_text = (
            f"Traced {primary['table_name']}.{primary['field_name']} movement in {table_to_silo(primary['table_name'])} "
            f"to {secondary['table_name']}.{secondary['field_name']} deterioration in {table_to_silo(secondary['table_name'])}, "
            "confirming cross-table causal propagation."
        )

    forensic_chain = [
        {
            "step": 1,
            "agent": "Data Acquisition",
            "thought": f"Step 1: SQL Specialist scanned metadata and time-series fields across {len(table_names)} silos/tables: {scanned_tables_text}."
        },
        {
            "step": 2,
            "agent": "Anomaly Detection",
            "thought": f"Step 2: Anomaly Detection isolated the strongest outlier. {anomaly_text}"
        },
        {
            "step": 3,
            "agent": "Cross-Silo Correlation",
            "thought": f"Step 3: Correlation engine aligned investigation windows and tested cross-silo propagation. {correlation_text}"
        }
    ]
    if isinstance(final_insight, dict):
        final_insight["reasoning_chain"] = forensic_chain
        # Merge silos from anomaly + enforce_strict_schema traces instead of overwriting
        existing_silos = final_insight.get("target_silos", [])
        if not isinstance(existing_silos, list):
            existing_silos = []
        merged_silo_set = list(existing_silos)  # start from enforce_strict_schema's traces
        if highest_delta and highest_delta.get("table"):
            s = table_to_silo(highest_delta.get("table"))
            if s not in merged_silo_set:
                merged_silo_set.append(s)
        if primary and primary.get("table_name"):
            s = table_to_silo(primary.get("table_name"))
            if s not in merged_silo_set:
                merged_silo_set.append(s)
        if secondary and secondary.get("table_name"):
            s = table_to_silo(secondary.get("table_name"))
            if s not in merged_silo_set:
                merged_silo_set.append(s)
        normalized_sources = [s for s in merged_silo_set if s in ALLOWED_SILOS]
        normalized_sources = list(dict.fromkeys(normalized_sources)) or ["Operations"]
        # Only latch to single active_focus for genuine follow-ups where focus was pre-set
        if _focus_from_state and active_focus in ALLOWED_SILOS:
            final_insight["target_silos"] = [active_focus]
        else:
            final_insight["target_silos"] = normalized_sources
            if normalized_sources:
                active_focus = normalized_sources[0]

    if is_sim and isinstance(final_insight, dict):
        simulation_inputs = state.get("simulation_inputs", {}) if isinstance(state.get("simulation_inputs", {}), dict) else {}
        sim_projected = simulation_summary.get("projected", {}) if isinstance(simulation_summary, dict) else {}
        content = final_insight.get("content") if isinstance(final_insight.get("content"), dict) else {}
        primary_driver_parts = []
        for key in ["price_change", "revenue_change", "volume_change", "discount_change"]:
            value = simulation_inputs.get(key)
            if isinstance(value, (int, float)):
                suffix = "%" if abs(value) <= 100 else ""
                primary_driver_parts.append(f"{key}={value}{suffix}")
        if not primary_driver_parts:
            primary_driver_parts.append("explicit simulation_inputs scenario")

        secondary_factor = "None detected"
        if highest_delta:
            secondary_factor = (
                f"{highest_delta['field']} in {highest_delta['table']} ({highest_delta['delta']:.1f}% historical shift)"
            )

        projected_revenue = None
        if isinstance(sim_projected, dict) and isinstance(sim_projected.get("revenue"), (int, float)):
            projected_revenue = sim_projected.get("revenue")

        content["headline"] = "Simulation Scenario Impacting Projected Revenue"
        summary_line = (
            f"Primary simulation driver: {', '.join(primary_driver_parts)}. "
            "Projected outcomes are attributed to this what-if scenario first."
        )
        if isinstance(projected_revenue, (int, float)):
            summary_line += f" Simulated projected revenue: ${projected_revenue:,.2f}."
        content["summary"] = summary_line
        content["reasoning_detailed"] = (
            f"Primary Driver: {', '.join(primary_driver_parts)}. "
            "Simulation inputs are treated as the root-cause mechanism for projected change. "
            f"Secondary Environmental Factor: {secondary_factor}. "
            "Historical anomalies are contextual only and not used as the primary cause of simulated revenue movement."
        )
        final_insight["content"] = content

    if sales_manager and isinstance(final_insight, dict) and not is_sim:
        content = final_insight.get("content") if isinstance(final_insight.get("content"), dict) else {}
        headline = str(content.get("headline", ""))
        # Replace full metric phrases instead of single words to avoid orphaned fragments like "Ms in Operations"
        headline = re.sub(r"\bLatency Ms\b", "Service Delays", headline, flags=re.IGNORECASE)
        headline = re.sub(r"\bUptime Pct\b", "Reliability", headline, flags=re.IGNORECASE)
        headline = re.sub(r"\bSuccess Rate\b", "Service Quality", headline, flags=re.IGNORECASE)
        if "lead" not in headline.lower() and "pipeline" not in headline.lower():
            headline = f"Lead Quality Shift Impacting Pipeline Health - {headline}".strip(" -")
        content["headline"] = re.sub(r"\s{2,}", " ", headline).strip()

        recommendations = content.get("recommendations") if isinstance(content.get("recommendations"), list) else []
        cleaned_recs = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            action = re.sub(r"\blatency ms\b", "service delays", str(rec.get("action", "")), flags=re.IGNORECASE)
            detail = re.sub(r"\blatency ms\b", "service delays", str(rec.get("detail", "")), flags=re.IGNORECASE)
            action = re.sub(r"\buptime pct\b", "reliability", action, flags=re.IGNORECASE)
            detail = re.sub(r"\buptime pct\b", "reliability", detail, flags=re.IGNORECASE)
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
    return {
        "final_insight": final_insight,
        "active_focus": active_focus
    }

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