from pydantic import BaseModel
from typing import Literal

Side = Literal["bid", "ask"]

class OrderRequest(BaseModel):
    market: str
    side: Side
    volume: str | None = None
    price: str | None = None
    ord_type: str  # limit/price/market

class OrderResponse(BaseModel):
    uuid: str
    market: str
    side: Side
    state: str
