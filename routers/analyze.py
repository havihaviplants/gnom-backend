# routers/analyze.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from services.analyze_service import analyze_emotion, check_and_increment_call_count, redis_client, get_seconds_until_midnight
from models.analyze_model import AnalyzeRequest, AnalyzeResponse

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_message(data: AnalyzeRequest):
    user_id = "anonymous"  # 추후 프론트에서 받아오면 교체

    if not check_and_increment_call_count(user_id):
        raise HTTPException(status_code=403, detail="하루 3회 감정 분석 제한을 초과했습니다.")

    try:
        result = analyze_emotion(data.message, data.relationship)  # 함수 정의가 2인자 받는다면 OK
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unlock")
async def unlock_call_limit(request: Request):
    body = await request.json()
    user_id = body.get("user_id") or "anonymous"
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"call_unlocked:{user_id}:{today}"
    redis_client.set(key, 1, ex=get_seconds_until_midnight())
    return {"status": "unlocked", "message": "오늘 제한이 해제되었습니다."}


# 입력 스키마
class AnalysisRequest(BaseModel):
    message: str
    relationship: str  # 예: 전남친, 친구, 직장상사 등

# 출력 스키마
class AnalysisResponse(BaseModel):
    emotion: str
    insight: str
    tone: str
    summary: str
