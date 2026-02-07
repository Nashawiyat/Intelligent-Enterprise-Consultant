from fastapi import FastAPI
from contextlib import asynccontextmanager
import json
import asyncio

from db_helper_functions import init_db_insights, close_db_insights, recordInsight, getLatestInsightRecordFromDB
from helper_classes import PromptRequest, InsightRequest, SimulationRequest

# Function to periodically get the latest insights from LangGraph
# every 60 seconds and then insert it into the database
async def retrieveUpdatedInsights():
    while True:
        # TODO: retrieve latest insights from LangGraph
        # and store in database
        # recordInsight(json, domain)
        print("TODO: retrieveUpdatedInsights") # Testing that asynchronous calling works
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup function
    task = asyncio.create_task(retrieveUpdatedInsights())
    init_db_insights()

    # Run teh app
    yield

    # Close database connection when no longer required
    close_db_insights()
    # Cancel the task once the app closes
    task.cancel()

    try:
        # Trigger it one more time to cancel it.
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

def retrieveSimulationResults(data: SimulationRequest):
    return json.dumps(data.__dict__)

@app.post("/simulation")
async def getSimulation(data: SimulationRequest):
    if data.domain == "sales":
        return retrieveSimulationResults(data=data)

# TODO: Figure out where to use role_context
# Function to get latest row from insights table in the database 
def getLatestInsights(domain, role_context):
    domain, insight_json = getLatestInsightRecordFromDB()
    return {"domain": domain, "insight": insight_json}

@app.post("/insights")
async def getInsights(data: InsightRequest):
    domain = data.domain
    role_context = data.role_context

    return getLatestInsights(domain, role_context)

# TODO: Connect to LangGraph
@app.post("/prompt")
async def getPrompt(data: PromptRequest):
    return {"prompt": data.prompt, "response":"TODO"}