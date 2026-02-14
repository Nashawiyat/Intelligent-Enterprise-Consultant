from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    orchestrator_node, 
    sql_agent_node, 
    reasoner_node, 
    security_node,
    simulation_specialist_node,
    quantitative_audit_node,
    insight_filter_node,
    strategic_reasoner_node,
    chart_generator_node
)

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("sql_specialist", sql_agent_node)
workflow.add_node("simulation_specialist", simulation_specialist_node) # Handles simulation logic
workflow.add_node("causal_reasoner", reasoner_node)
workflow.add_node("quantitative_audit", quantitative_audit_node)
workflow.add_node("insight_filter", insight_filter_node)
workflow.add_node("strategic_reasoner", strategic_reasoner_node)
workflow.add_node("chart_generator", chart_generator_node)
workflow.add_node("security_gatekeeper", security_node)

# Entry Point
workflow.set_entry_point("orchestrator")

def identify_intent_route(state: AgentState):
    messages = state.get("messages", [])
    user_text = ""
    if messages:
        last_msg = messages[-1]
        user_text = last_msg[1] if isinstance(last_msg, tuple) else str(getattr(last_msg, "content", ""))
    lower_text = (user_text or "").lower()

    fact_sheet_history = state.get("fact_sheet_history", [])
    has_history = isinstance(fact_sheet_history, list) and len(fact_sheet_history) > 0
    followup_keywords = [
        "elaborate", "why", "who", "fix", "explain", "mean",
        "what does", "what is", "how did", "how is", "tell me",
        "break down", "clarify", "more detail",
        "action", "actions", "should i", "should we", "amend",
        "steps", "recommend", "do about", "what can"
    ]
    if has_history and any(k in lower_text for k in followup_keywords):
        return "causal_reasoner"

    intent_mode = str(state.get("intent_mode", "STANDARD")).upper()
    if intent_mode == "COMPETITIVE_INTEL":
        return "sql_specialist"

    interaction_mode = str(state.get("interaction_mode", "")).upper()
    if interaction_mode in {"SOCIAL", "ANALYTICAL"}:
        return "causal_reasoner" if interaction_mode == "SOCIAL" else "sql_specialist"

    analytical_keywords = [
        "simulate", "simulation", "health-check", "health check", "healthcheck", "anomaly", "audit",
        "forensic", "revenue", "margin", "latency", "pipeline", "nps", "churn", "cash flow", "expenditure",
        "trend", "correlation", "projection", "what if"
    ]
    social_keywords = ["hi", "hello", "hey", "how are you", "thanks", "thank you"]

    if any(k in lower_text for k in analytical_keywords):
        return "sql_specialist"
    if any(k in lower_text for k in social_keywords) or not lower_text.strip():
        return "causal_reasoner"
    return "causal_reasoner"

# Router to check if user is asking for a LIVE insight or a simulation
def route_after_sql(state: AgentState):
    """After getting SQL baseline, decide if we need a simulation or direct reasoning."""
    interaction_mode = state.get("interaction_mode")
    intent_mode = str(state.get("intent_mode", "STANDARD")).upper()
    if state.get("is_simulation", False):
        return "simulation_specialist"
    if intent_mode == "COMPETITIVE_INTEL":
        return "causal_reasoner"
    if interaction_mode == "SOCIAL":
        return "causal_reasoner"
    if interaction_mode == "ANALYTICAL":
        return "quantitative_audit"
    return "causal_reasoner"

def route_after_reasoner(state: AgentState):
    """If reasoning needs more data, loop back to SQL; otherwise continue."""
    if state.get("needs_more_data", False):
        return "sql_specialist"
    return "security_gatekeeper"

def route_after_filter(state: AgentState):
    if state.get("is_simulation", False):
        return "strategic_reasoner"
    if state.get("end_early", False):
        return "security_gatekeeper"
    return "strategic_reasoner"

# Entry point
workflow.set_entry_point("orchestrator")

# Route intent-aware traffic after orchestration
workflow.add_conditional_edges(
    "orchestrator",
    identify_intent_route,
    {
        "causal_reasoner": "causal_reasoner",
        "sql_specialist": "sql_specialist"
    }
)

# Conditional routing
workflow.add_conditional_edges(
    "sql_specialist",
    route_after_sql,
    {
        "simulation_specialist": "simulation_specialist",
        "quantitative_audit": "quantitative_audit",
        "causal_reasoner": "causal_reasoner"
    }
)

workflow.add_edge("simulation_specialist", "quantitative_audit")
workflow.add_edge("causal_reasoner", "security_gatekeeper")
workflow.add_edge("quantitative_audit", "insight_filter")
workflow.add_conditional_edges(
    "insight_filter",
    route_after_filter,
    {
        "strategic_reasoner": "strategic_reasoner",
        "security_gatekeeper": "security_gatekeeper"
    }
)
workflow.add_edge("strategic_reasoner", "chart_generator")
workflow.add_conditional_edges(
    "chart_generator",
    route_after_reasoner,
    {
        "sql_specialist": "sql_specialist",
        "security_gatekeeper": "security_gatekeeper"
    }
)
workflow.add_edge("security_gatekeeper", END)

# Compile
enterprise_agent = workflow.compile()