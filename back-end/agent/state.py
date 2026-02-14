from typing import TypedDict, Annotated, List, Dict, Any, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    interaction_mode: str
    intent_mode: str
    active_focus: Union[str, None]
    role: str
    sql_query: str
    sql_results: Dict[str, Any]
    external_context: str
    reasoning_steps: Annotated[List[str], operator.add]
    confidence_score: float
    is_simulation: bool
    simulation_inputs: Dict[str, Any]
    simulation_summary: Dict[str, Any]
    target_silos: List[str]
    fact_sheet: Annotated[Dict[str, Any], operator.or_]
    fact_sheet_history: Annotated[List[Dict[str, Any]], operator.add]
    audit_summary: str
    end_early: bool
    needs_more_data: bool
    sql_retry_mode: Union[str, None]
    final_insight: Dict[str, Any]