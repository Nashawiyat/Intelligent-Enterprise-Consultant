from pydantic import BaseModel
from typing import Literal, TypeAlias, Union

class InsightRequest(BaseModel):
    domain: str
    role_context: str

class PromptRequest(BaseModel):
    domain: str
    role_context: str
    prompt: str

class SalesSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str
    price: float
    discount_quantity: int
    client_retention_rate: float
    lead_inflow_volume: int
    prompt: str | None = None

class HRSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str

    # TODO: Add fields
    
    prompt: str | None = None

class AccountingSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str

    # TODO: Add fields
    
    prompt: str | None = None

class OperationSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str

    # TODO: Add fields
    
    prompt: str | None = None

SimulationRequest: TypeAlias = Union[
    SalesSimulation,
    HRSimulation,
    AccountingSimulation,
    OperationSimulation
]