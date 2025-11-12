# models/analyze_model.py
from pydantic import BaseModel
from typing import List

class AnalyzeRequest(BaseModel):
    message: str
    relationship: str | None = None
    user_id: str | None = None

class AnalyzeResponse(BaseModel):
    interpretation: str
    insight: str
    tags: List[str]
    emojis: List[str]
