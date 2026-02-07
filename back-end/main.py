from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated, TypeAlias
import json

app = FastAPI()

class InsightRequest(BaseModel):
    domain: str
    role_context: str

@app.post("/insights")
def getLatestInsight(data: InsightRequest):
    domain = data.domain
    role_context = data.role_context

    return {"insight":f"Insight for domain: {domain} and role_context: {role_context}"}

class SalesSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str
    price: float
    discount_quantity: int
    client_retention_rate: float
    lead_inflow_volume: int
    prompt: str | None = None

SimulationRequest: TypeAlias = Union[SalesSimulation]

def retrieveSimulationResults(data: SimulationRequest):
    return json.dumps(data.__dict__)

@app.post("/simulation")
def getSimulation(data: SimulationRequest):
    if data.domain == "sales":
        return retrieveSimulationResults(data=data)



