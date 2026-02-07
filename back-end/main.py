from fastapi import FastAPI

import asyncio
import json

from helper_classes import InsightRequest, SimulationRequest

app = FastAPI()

def retrieveSimulationResults(data: SimulationRequest):
    return json.dumps(data.__dict__)

@app.post("/simulation")
def getSimulation(data: SimulationRequest):
    if data.domain == "sales":
        return retrieveSimulationResults(data=data)

# Function to periodically get the latest insights from LangGraph
# and then insert it into the database
async def retrieveUpdatedInsights():
    # TODO: retrieve latest insights from LangGraph
    # and store in database
    await asyncio.sleep(60)

# Function to get latest row from insights table in the database 
def getLatestInsights(domain, role_context):
    # TODO: run an SQL statement to get the latest record from insights table
    # SELECT insight FROM insights ORDER BY timestamp DESC LIMIT 1;
    return {"insight":f"Insight for domain: {domain} and role_context: {role_context}"}

@app.post("/insights")
def getInsights(data: InsightRequest):
    domain = data.domain
    role_context = data.role_context

asyncio.run(retrieveSimulationResults)