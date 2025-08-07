from pydantic import BaseModel
from typing import List

class AnalyzeRequest(BaseModel):
    message: str
    relationship: str

class AnalyzeResponse(BaseModel):
    emotions: List[str]
    reason: str
