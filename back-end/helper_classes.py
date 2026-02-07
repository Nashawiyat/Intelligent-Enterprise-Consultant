from pydantic import BaseModel
from typing import Literal

class SalesSimulation(BaseModel):
    domain: Literal["sales"]
    role_context: str
    price: float
    discount_quantity: int
    client_retention_rate: float
    lead_inflow_volume: int
    prompt: str | None = None

