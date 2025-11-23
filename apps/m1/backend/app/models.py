from pydantic import BaseModel
from typing import List

class ModelSignal(BaseModel):
    name: str
    signal: float
    confidence: float

class SigmaSignal(BaseModel):
    timestamp: str
    symbol: str
    regime: str
    score: float
    confidence: float
    models: List[ModelSignal]
