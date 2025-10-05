from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from fastapi import APIRouter, HTTPException
from models.analyze_model import AnalyzeRequest, AnalyzeResponse
from services.analyze_service import (
    analyze_emotion,
    check_and_increment_call_count,
)


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
        # 예: raw = {"interpretation":"...", "insight":"...", "tags":["거리감","포기"], "emojis":["🥶","💬","🌫️"]}
        raw = analyze_emotion(data.message, data.relationship)

        # 1) LLM이 바로 위 스키마로 주는 경우
        if isinstance(raw, dict) and {"interpretation","insight","tags","emojis"} <= set(raw.keys()):
            return AnalyzeResponse(**raw)

        # 2) 예전 포맷(예: {"emotions":[...], "reason":"..."})도 안전하게 수용
        emotions = (raw or {}).get("emotions") or []
        reason = (raw or {}).get("reason") or ""

        tags = emotions[:3]
        interpretation = reason or "감정 해석을 생성하지 못했습니다."
        insight = (reason[:60] + "...") if reason else "추가 인사이트 없음."

        # 간단 이모지 매핑(필요 시 확장)
        EMOJI_MAP = {
            "거리감":"🥶", "포기":"🏳️", "냉소":"😒", "불신":"🤨", "짜증":"😤",
            "애정":"💗", "기대감":"✨", "두려움":"😨", "혼란":"🌫️", "미안함":"🙏",
        }
        emojis = [EMOJI_MAP.get(t, "💬") for t in tags][:3]
        if len(emojis) < 3: emojis += ["💬"] * (3 - len(emojis))

        return AnalyzeResponse(
            interpretation=interpretation,
            insight=insight,
            tags=tags,
            emojis=emojis
        )

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
