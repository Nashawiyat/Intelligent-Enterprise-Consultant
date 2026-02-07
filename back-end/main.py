from fastapi import FastAPI
from typing import Union, TypeAlias
import json

from helper_classes import SalesSimulation

app = FastAPI()



SimulationRequest: TypeAlias = Union[SalesSimulation]

def retrieveSimulationResults(data: SimulationRequest):
    return json.dumps(data.__dict__)

@app.post("/simulation")
def getSimulation(data: SimulationRequest):
    if data.domain == "sales":
        return retrieveSimulationResults(data=data)



