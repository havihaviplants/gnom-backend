from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime

from services.analyze_service import (
    analyze_emotion,
    check_and_increment_call_count,
    get_seconds_until_midnight,
    redis_client,
)

router = APIRouter()


# ✅ 입력 모델
class AnalyzeRequest(BaseModel):
    message: str
    relationship: str  # 예: 전남친, 친구, 직장상사 등


# ✅ 출력 모델
class AnalyzeResponse(BaseModel):
    emotion: str
    tone: str
    summary: str
    insight: str


# ✅ 분석 요청
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(data: AnalyzeRequest):
    user_id = "anonymous"  # 이후 프론트에서 user_id 넘기도록

    if not check_and_increment_call_count(user_id):
        raise HTTPException(status_code=403, detail="하루 3회 감정 분석 제한을 초과했습니다.")

    try:
        result = analyze_emotion(data.message, data.relationship)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


# ✅ 광고 시청 등으로 제한 해제
@router.post("/unlock")
async def unlock_limit(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "anonymous")
    today = datetime.now().strftime("%Y-%m-%d")
    redis_key = f"call_unlocked:{user_id}:{today}"

    redis_client.set(redis_key, 1, ex=get_seconds_until_midnight())
    return {"status": "unlocked", "message": "오늘 분석 제한이 해제되었습니다."}
