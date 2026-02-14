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

# Router to check if user is asking for a LIVE insight or a simulation
def route_after_sql(state: AgentState):
    """After getting SQL baseline, decide if we need a simulation or direct reasoning."""
    if state.get("is_simulation", False):
        return "simulation_specialist"
    if len(state.get("messages", [])) > 1:
        return "causal_reasoner"
    return "quantitative_audit"

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

# orchestrator always goes to SQL first if data is missing
workflow.add_edge("orchestrator", "sql_specialist")

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