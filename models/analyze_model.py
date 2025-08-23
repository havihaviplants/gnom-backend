from typing import List
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    message: str
    relationship: str

class AnalyzeResponse(BaseModel):
    emotions: List[str]
    reason: str

class AnalyzeResponse(BaseModel):
    # 프론트에서 쓰는 필드 이름에 맞춰 둔다
    emotion: List[str]           # 최대 3개 감정 라벨
    tone: str                    # 주 톤(대표 감정)
    summary: str                 # 한 줄 요약
    insight: str                 # 해석/한줄 인사이트