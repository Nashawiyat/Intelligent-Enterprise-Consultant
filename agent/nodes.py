from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from .state import AgentState
from .tools import query_enterprise_database, get_competitive_intel, get_database_schema
import sqlite3
import re
import json
import re

# LLM initialization
llm_smart = ChatGroq(model="llama-3.3-70b-versatile")
llm_fast = ChatGroq(model="llama-3.1-8b-instant")
tools = [query_enterprise_database, get_competitive_intel, get_database_schema]
llm_with_tools = llm_fast.bind_tools(tools)

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

#TODO: Check if it is using the state properly
def sql_agent_node(state: AgentState):
    schema = get_database_schema.invoke({})
    user_msg = get_message_content(state["messages"][-1])
    # Minimalist prompt to ensure the 8B model doesn't drift
    query_prompt = f"SCHEMA: {schema}\nREQUEST: {user_msg}\nTASK: Use 'query_enterprise_database'. Output ONLY the tool call."
    response = llm_with_tools.invoke(query_prompt)
    
    if response.tool_calls:
        results = query_enterprise_database.invoke(response.tool_calls[0]["args"])
    else:
        # Regex fallback for 8B model reliability
        query = re.search(r"SELECT.*FROM.*", response.content, re.IGNORECASE)
        results = query_enterprise_database.invoke({"sql_query": query.group()}) if query else "No data found."

    return {"sql_results": str(results), "reasoning_steps": ["SQL node retrieved specific domain data."]}

def get_message_content(msg):
    """Helper to safely extract content from a tuple or BaseMessage object."""
    if isinstance(msg, tuple):
        return msg[1]
    return msg.content

def simulation_specialist_node(state: AgentState):
    schema = get_database_schema.invoke({})
    user_msg = get_message_content(state["messages"][-1])
    # Minimalist prompt to ensure the 8B model doesn't drift
    query_prompt = f"SCHEMA: {schema}\nREQUEST: {user_msg}\nTASK: Use 'query_enterprise_database'. Output ONLY the tool call."
    response = llm_with_tools.invoke(query_prompt)
    
    if response.tool_calls:
        results = query_enterprise_database.invoke(response.tool_calls[0]["args"])
    else:
        # Regex fallback for 8B model reliability
        query = re.search(r"SELECT.*FROM.*", response.content, re.IGNORECASE)
        results = query_enterprise_database.invoke({"sql_query": query.group()}) if query else "No data found."

    return {"sql_results": str(results), "reasoning_steps": ["SQL node retrieved specific domain data."]}

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
    last_msg = get_message_content(state['messages'][-1]).lower()
    is_chat = len(state['messages']) > 1 and not is_sim and "health check" not in last_msg

    # PERSONA FILTER: Prevent database leaks in chat 
    if is_chat:
        mission = f"CHAT MODE: You are the {user_role}. Answer the user's specific question. DO NOT list raw database rows. SYNTHESIZE the answer."
        format_inst = "Output: Conversational text only."
    else:
        mission = f"REPORT MODE: Act as a CIO for {user_role}. Triangulate Ops/Finance correlations."
        format_inst = "Output: STRICT JSON SCHEMA ONLY."

    prompt = f"""
    MISSION: {mission}
    CONTEXT DATA: {sql_context}
    USER ROLE: {user_role}
    {format_inst}
    
    TASK (If JSON):
    1. TARGETING: Choose from [Operations, Sales, Marketing, HR, Executive, Accounting].
    2. MATH: Calculate ((New-Old)/Old)*100 manually.
    
    STRICT JSON TEMPLATE:
    {{
      "insight_id": "INC-2026-NXS",
      "meta": {{ "urgency_score": 0.9, "confidence_score": 0.9, "role_context": "{user_role}" }},
      "target_silos": ["Finance", "IT"], 
      "content": {{
        "headline": "str",
        "summary": "str with numbers",
        "reasoning_detailed": "layman cross-silo explanation",
        "recommendations": [{{ "action": "Task", "detail": "Steps", "expected_impact": "Impact" }}]
      }},
      "reasoning_chain": [{{ "step": 1, "agent": "Auditor", "thought": "Calculated deltas from context." }}],
      "visuals": {{ "chart_type": "bar", "plotly_data": {{ "data": [] }} }}
    }}
    """

    response = llm_smart.invoke(prompt)
    if is_chat: return {"final_insight": {"chat_response": response.content}}

    try:
        # ROBUST JSON CLEANING: Remove any text before the first '{' and after the last '}'
        # 
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if not json_match: raise ValueError("JSON block missing")
        
        raw_json = json_match.group(0)
        clean_json = re.sub(r',\s*([\]}])', r'\1', raw_json) # Remove trailing commas
        data = json.loads(clean_json)

        return {
            "final_insight": data,
            "target_silos": data.get("target_silos", ["Executive"]),
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