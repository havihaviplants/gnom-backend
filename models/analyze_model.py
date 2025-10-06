from typing import List
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    message: str
    relationship: str

class AnalyzeResponse(BaseModel):
    interpretation: str   # 해석 본문
    insight: str          # 한 줄 통찰
    tags: List[str]       # 감정 분류(최대 3개)
    emojis: List[str]     # 이모지 3개
