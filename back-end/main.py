from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
import json
import asyncio

from db_helper_functions import init_db_insights, close_db_insights, recordInsight, getLatestInsightRecordFromDB
from helper_classes import PromptRequest, InsightRequest, SimulationRequest, BaseSimulationRequest

# LangGraph agent to process queries
from agent import enterprise_agent

# Set to true to have system get latest insights periodically from LLM
# instead of per request from frontend
PERIODIC_UPDATES = False

async def query_langgraph(messages, domain, is_simulation=False, simulation_inputs=[]):
    # Input format required by LangGraph
    inputs = {
        "messages": messages,
        "role": domain,
        is_simulation: is_simulation,
        simulation_inputs: simulation_inputs
    }

    try:
        final_state = await enterprise_agent.ainvoke(inputs)
        insight = final_state.get("final_insight")

        if not insight:
            raise HTTPException(status_code=500, detail="LangGraph was unable to get a response")
        
        return insight
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
            
            json_result = query_langgraph(**proactive_inputs)
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
async def getSimulation(data: SimulationRequest):
    return await retrieveSimulationResults(data=data)

# Function to get latest row from insights table in the database 
def getLatestInsights(domain, role_context):
    if PERIODIC_UPDATES:
        insight_result = getLatestInsightRecordFromDB(domain)
    else:
        proactive_inputs = {
            "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
            "role": role_context, # Placeholder for now
            "is_simulation": False,
            "current_silo": domain # Initializing to avoid KeyErrors
        }
        
        insight_result = query_langgraph(proactive_inputs)
    return insight_result

@app.post("/insights")
async def getInsights(data: InsightRequest):
    domain = data.domain
    role_context = data.role_context

    return getLatestInsights(domain, role_context)

# TODO: Connect to LangGraph
@app.post("/prompt")
async def getPrompt(data: PromptRequest):
    inputs = {
        "messages": [
            ("user", "Perform a health check."),
            ("user", "Why exactly is the latency affecting revenue? Give me the breakdown.")
        ],
        "role": "CEO",
        "is_simulation": False
    }
    return {"prompt": data.prompt, "response":"TODO"}