from fastapi import APIRouter, HTTPException, Request
from models.analyze_model import AnalyzeRequest, AnalyzeResponse
from services.analyze_service import (
    analyze_emotion,
    check_and_increment_call_count,
    get_seconds_until_midnight,
)

router = APIRouter(tags=["analyze"])

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    """
    메시지 감정/맥락 해석 엔드포인트.
    - 일일 한도는 서비스에서 토글(LIMIT_ENABLED)로 제어
    - 서비스 레이어가 dict을 돌려주면 Pydantic이 자동 검증/정형화
    """
    try:
        # 프론트에서 user_id를 body에 포함했다면 레이트리밋 키로 사용
        body = await request.json()
        user_id = body.get("user_id")

        allowed, _count = check_and_increment_call_count(user_id)
        if not allowed:
            raise HTTPException(status_code=429, detail="분석 요청 한도를 초과했습니다. 내일 다시 시도하세요.")

        result = analyze_emotion(req.message, req.relationship)
        # FastAPI가 AnalyzeResponse로 변환/검증
        return AnalyzeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@router.post("/unlock")
async def unlock_limit(request: Request):
    """
    (선택) 광고 시청 등으로 일일 한도 해제 시 쓰는 엔드포인트.
    현재는 스텁: 성공 응답만 내려주고, 실제 TTL/상태 저장은 나중에 Redis 도입 후 구현.
    """
    _ = await request.json()
    # ex_seconds = get_seconds_until_midnight()  # 나중에 Redis 키 EXPIRE에 사용
    return {"status": "unlocked", "message": "오늘 분석 제한이 해제되었습니다."}
