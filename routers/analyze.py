import os
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime

# ❗여기서만 쓰는 BaseModel은 필요 없음 (중복정의 제거)
from models.analyze_model import AnalyzeRequest, AnalyzeResponse
from services.analyze_service import (
    analyze_emotion,
    check_and_increment_call_count,
    get_seconds_until_midnight,
    redis_client,
)

router = APIRouter()

# 🔥 중복/섀도잉 제거: AnalyzeRequest를 다시 정의하지 않습니다.

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(data: AnalyzeRequest):
    user_id = "anonymous"  # TODO: 프론트에서 user_id 넘겨받게 개선

    if not check_and_increment_call_count(user_id):
        raise HTTPException(status_code=403, detail="하루 3회 감정 분석 제한을 초과했습니다.")

    try:
        # 예시: raw = {"emotions": ["두려움"], "reason": "…"}
        raw = analyze_emotion(data.message, data.relationship)  # sync 함수면 그대로 호출

        emotions = (raw or {}).get("emotions") or []
        reason = (raw or {}).get("reason") or ""

        payload = {
            "emotion": emotions,                             # List[str]
            "tone": (emotions[0] if emotions else "중립"),    # str
            "summary": (reason[:120] if reason else "분석 요약을 생성하지 못했습니다."),  # str
            "insight": (reason or "추가 인사이트 없음."),      # str
        }
        return AnalyzeResponse(**payload)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@router.post("/unlock")
async def unlock_limit(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "anonymous")
    today = datetime.now().strftime("%Y-%m-%d")
    redis_key = f"call_unlocked:{user_id}:{today}"

    redis_client.set(redis_key, 1, ex=get_seconds_until_midnight())
    return {"status": "unlocked", "message": "오늘 분석 제한이 해제되었습니다."}

print(">>> 현재 실행 중인 파일 경로:", __file__)
print(">>> 현재 작업 디렉토리:", os.getcwd())
