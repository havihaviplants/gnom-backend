# routers/share.py
import uuid, json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dependencies import get_store
from services.license_service import LicenseStore

router = APIRouter(prefix="/share", tags=["share"])
R = get_store()
S = LicenseStore()

class ShareCreateBody(BaseModel):
    user_id: str
    title: str
    summary: str | None = ""

class ShareCreateResp(BaseModel):
    share_id: str
    share_url: str
    store_url: str | None = None

class ShareClaimBody(BaseModel):
    user_id: str
    share_id: str

@router.post("", response_model=ShareCreateResp)
@router.post("/", response_model=ShareCreateResp)
def create(b: ShareCreateBody):
    """
    - share:{id}에 세션 저장(30분)
    - share_url/store_url은 앱에서 메시지 구성할 때 사용
    """
    share_id = uuid.uuid4().hex[:12]
    payload = {"user_id": b.user_id, "title": b.title, "summary": b.summary or ""}
    R.set(f"share:{share_id}", json.dumps(payload), ttl_seconds=60 * 30)
    # 설치/공개 페이지 링크(필요에 맞게 교체)
    share_url = "https://play.google.com/store/apps/details?id=com.leehyodong.gnomfrontend"
    return {"share_id": share_id, "share_url": share_url, "store_url": share_url}

@router.post("/claim")
def claim(b: ShareClaimBody):
    """
    자동 지급 금지. 사용자가 명시적으로 '보상받기'를 누를 때만 지급.
    - 동일 share_id 중복 차단
    - 하루 2회 한도(+1씩)
    """
    if not R.get(f"share:{b.share_id}"):
        raise HTTPException(status_code=404, detail="INVALID_SHARE_ID")
    if R.get(f"claim:{b.share_id}"):
        raise HTTPException(status_code=409, detail="ALREADY_CLAIMED")

    ok = S.grant_share_daily(b.user_id, amount=1, daily_limit=2)
    if not ok:
        raise HTTPException(status_code=429, detail="DAILY_SHARE_LIMIT")

    R.set(f"claim:{b.share_id}", b.user_id)
    return {"ok": True}
