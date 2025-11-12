# routers/share.py
import uuid, json, os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dependencies import get_store
from services.license_service import LicenseStore

router = APIRouter(prefix="/share", tags=["share"])
S = LicenseStore()
R = get_store()

STORE_URL = os.getenv(
    "STORE_URL",
    "https://play.google.com/store/apps/details?id=com.leehyodong.gnomfrontend",
)

class ShareCreateBody(BaseModel):
    user_id: str
    title: str
    summary: str | None = ""

class ShareCreateResp(BaseModel):
    share_id: str
    share_url: str        # 안내용(스토어 링크)
    store_url: str | None = None

class ShareClaimBody(BaseModel):
    user_id: str
    share_id: str
    shared: bool = False  # 클라이언트가 실제 공유액션 성공 시 true로 보냄

@router.post("", response_model=ShareCreateResp)
@router.post("/", response_model=ShareCreateResp)
def create(b: ShareCreateBody):
    """
    공유 세션 생성.
    - share:{id} 저장(24h)
    - 실제 전송 여부 판단은 클라이언트가 shared=true로 보내는지로 처리
      (요구사항: '실제 전송을 탭하면 지급, 공유창만 띄우고 취소하면 미지급')
    """
    share_id = uuid.uuid4().hex[:12]
    payload = {"user_id": b.user_id, "title": b.title, "summary": b.summary or ""}
    R.set(f"share:{share_id}", json.dumps(payload), ttl_seconds=60 * 60 * 24)
    return {"share_id": share_id, "share_url": STORE_URL, "store_url": STORE_URL}

@router.post("/claim")
def claim(b: ShareClaimBody):
    """
    지급 규칙:
    - 유효한 share_id
    - shared == True (클라에서 RN Share.sharedAction일 때만 호출)
    - 동일 share_id 중복지급 방지
    - 하루 2회 한도, 1회당 +1
    """
    if not R.get(f"share:{b.share_id}"):
        raise HTTPException(status_code=404, detail="INVALID_SHARE_ID")

    if not b.shared:
        # 클라이언트가 공유 취소/닫기한 케이스
        raise HTTPException(status_code=412, detail="SHARE_NOT_CONFIRMED")

    if R.get(f"claim:{b.share_id}"):
        raise HTTPException(status_code=409, detail="ALREADY_CLAIMED")

    ok = S.grant_share_daily(b.user_id, amount=1, daily_limit=2)
    if not ok:
        raise HTTPException(status_code=429, detail="DAILY_SHARE_LIMIT")

    R.set(f"claim:{b.share_id}", b.user_id)
    return {"ok": True}
