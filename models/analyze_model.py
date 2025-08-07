from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    message: str
    relationship: str  # 🔥 이 줄 추가하면 100% 해결됨

class AnalyzeResponse(BaseModel):
    result: str  # 또는 summary, emotion 등 실제 응답 구조에 맞춰서 확장 가능
