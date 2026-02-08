from typing import TypedDict, Annotated, List, Dict, Any, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    role: str
    sql_query: str
    sql_results: str
    external_context: str
    reasoning_steps: Annotated[List[str], operator.add]
    confidence_score: float
    is_simulation: bool
    simulation_inputs: Dict[str, Any]
    target_silos: List[str]
    final_insight: Dict[str, Any]