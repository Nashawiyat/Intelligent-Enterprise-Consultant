from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
import json
import os
import asyncio

from db_helper_functions import init_db_insights, close_db_insights, recordInsight, getLatestInsightRecordFromDB
from helper_classes import PromptRequest, InsightRequest, SimulationRequest, BaseSimulationRequest

# LangGraph agent to process queries

from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
# Pre-flight check
if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not found in .env")
    exit(1)
from agent import enterprise_agent

# Set to true to have system get latest insights periodically from LLM
# instead of per request from frontend
PERIODIC_UPDATES = False

async def query_langgraph(messages, role, current_silo:str, is_simulation=False, simulation_inputs=[]):
    # Input format required by LangGraph
    inputs = {
        "messages": messages,
        "role": role,
        "is_simulation": is_simulation,
        "simulation_inputs": simulation_inputs,
        "current_silo": current_silo,
        "sql_results": {},
        "fact_sheet_history": []
    }

    try:
        final_state = await enterprise_agent.ainvoke(inputs)
        insight = final_state.get("final_insight")

        if insight is None or (isinstance(insight, dict) and len(insight) == 0):
            return {
                "status": "no_insight",
                "message": "No insight generated for this request.",
                "end_early": bool(final_state.get("end_early", False)),
                "needs_more_data": bool(final_state.get("needs_more_data", False)),
                "audit_summary": final_state.get("audit_summary")
            }

        if not isinstance(insight, dict):
            raise HTTPException(status_code=500, detail="LangGraph returned invalid final_insight format")
        
        return insight
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Function to periodically get the latest insights from LangGraph
# every 60 seconds and then insert it into the database
valid_domains = ["crm", "accounting", "hr", "operations", "sales"]
async def retrievePeriodicUpdatedInsights():
    while True:
        for domain in valid_domains:
            proactive_inputs = {
                "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
                "role": "CEO", # Placeholder for now
                "is_simulation": False,
                "current_silo": domain # Initializing to avoid KeyErrors
            }
            
            json_result = await query_langgraph(**proactive_inputs)
            recordInsight(json_result, domain)
        
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup function
    if PERIODIC_UPDATES:
        task = asyncio.create_task(retrievePeriodicUpdatedInsights())
    init_db_insights()

    # Run teh app
    yield

    # Close database connection when no longer required
    close_db_insights()

    if PERIODIC_UPDATES:
        # Cancel the task once the app closes
        task.cancel()

        try:
            # Trigger it one more time to cancel it.
            await task
        except asyncio.CancelledError: # Expectde
            pass

app = FastAPI(lifespan=lifespan)

async def retrieveSimulationResults(request: Request, set_fields: BaseSimulationRequest):
    try:
        extra_params = await request.json()
    except Exception as e:
        return HTTPException(status_code=500, detail="Could not parse JSON inpu")
    
    # Remove set fields (domain, role_context, and prompt) from this
    # to leave only extra parameters for the simulation
    for field in set_fields.model_dump().keys():
        if field in extra_params:
            del extra_params[field]
    
    if set_fields.prompt is None:
        set_fields.prompt = "Use simulation inputs to build a baseline query for revenue and latency trends."

    sim_inputs = {
        "messages": [(set_fields.role_context, set_fields.prompt)],
        "role": set_fields.role_context,
        "is_simulation": True,
        "simulation_inputs": extra_params,
        "current_silo": set_fields.domain
    }

    response = await query_langgraph(**sim_inputs)

    return response

@app.post("/simulation")
async def getSimulation(request: Request, set_fields: BaseSimulationRequest):
    return await retrieveSimulationResults(request, set_fields)

# Function to get latest row from insights table in the database 
async def getLatestInsights(domain, role_context):
    if PERIODIC_UPDATES:
        insight_result = getLatestInsightRecordFromDB(domain)
    else:
        proactive_inputs = {
            "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
            "role": role_context, # Placeholder for now
            "is_simulation": False,
            "current_silo": domain # Initializing to avoid KeyErrors
        }
        
        insight_result = await query_langgraph(**proactive_inputs)
    return insight_result

@app.post("/insights")
async def getInsights(data: InsightRequest):
    domain = data.domain
    role_context = data.role_context

    return await getLatestInsights(domain, role_context)

@app.post("/prompt")
async def getPrompt(data: PromptRequest):
    inputs = {
        "messages": [
            ("user", data.prompt),
        ],
        "role": data.role_context,
        "is_simulation": False,
        "current_silo": data.domain
    }

    json_result = await query_langgraph(**inputs)
    return json_result