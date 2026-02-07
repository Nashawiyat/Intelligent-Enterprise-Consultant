from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    orchestrator_node, 
    sql_agent_node, 
    reasoner_node, 
    security_node,
    simulation_specialist_node
)

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("sql_specialist", sql_agent_node)
workflow.add_node("simulation_specialist", simulation_specialist_node) # Handles simulation logic
workflow.add_node("causal_reasoner", reasoner_node)
workflow.add_node("security_gatekeeper", security_node)

# Entry Point
workflow.set_entry_point("orchestrator")

# Router to check if user is asking for a LIVE insight or a simulation
def route_after_sql(state: AgentState):
    """After getting SQL baseline, decide if we need a simulation or direct reasoning."""
    if state.get("is_simulation", False):
        return "simulation_specialist"
    return "causal_reasoner"

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
        "causal_reasoner": "causal_reasoner"
    }
)

workflow.add_edge("simulation_specialist", "causal_reasoner")
workflow.add_edge("causal_reasoner", "security_gatekeeper")
workflow.add_edge("security_gatekeeper", END)

# Compile
enterprise_agent = workflow.compile()