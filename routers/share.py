from fastapi import APIRouter, HTTPException
import uuid, json, os

try:
    import redis  # 선택 요소
except Exception:
    redis = None  # 미설치/미연결 시 방어

router = APIRouter(tags=["share"])

REDIS_URL = os.getenv("REDIS_URL")  # e.g. redis://:pass@host:6379/0
r = None
if redis and REDIS_URL:
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
    except Exception:
        r = None  # 연결 실패 시 비활성

@router.post("/share")
def create_share(data: dict):
    """
    해석 결과를 단기 보관하고 share 링크 발급.
    - Redis 없으면 503 방어 (나중에 Render Redis 애드온 붙이면 자동 활성화)
    """
    if not r:
        raise HTTPException(status_code=503, detail="Share storage unavailable (Redis 미연결)")

    share_id = str(uuid.uuid4())[:8]
    # 30일 TTL
    r.setex(f"share:{share_id}", 60 * 60 * 24 * 30, json.dumps(data))
    # 실제 프론트 경로에 맞춰 도메인만 바꿔주면 됨
    return {"share_url": f"https://gnom.ai/share/{share_id}"}

@router.get("/share/{share_id}")
def get_share(share_id: str):
    if not r:
        raise HTTPException(status_code=503, detail="Share storage unavailable (Redis 미연결)")

    raw = r.get(f"share:{share_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Not found")
    return json.loads(raw)
