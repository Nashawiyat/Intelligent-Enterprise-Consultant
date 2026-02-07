from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated, TypeAlias
import json

app = FastAPI()

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



