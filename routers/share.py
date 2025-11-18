# routers/share.py
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dependencies import get_store
from services.license_service import LicenseStore

router = APIRouter(prefix="/share", tags=["share"])
R = get_store()
S = LicenseStore()

# 공유 링크 베이스 / 스토어 링크는 환경변수로 주입 가능
SHARE_BASE_URL = os.getenv("SHARE_BASE_URL", "https://gnom.ai/share")
STORE_URL = os.getenv("STORE_URL", "")


class ShareCreateBody(BaseModel):
    user_id: str
    title: str
    summary: str | None = ""


class ShareClaimBody(BaseModel):
    user_id: str
    share_id: str


@router.post("")
def share_create(b: ShareCreateBody):
    """
    공유용 링크 생성.
    - share_id 생성 후 메모리 스토어에 간단한 메타데이터 저장
    - 프론트에는 share_id / share_url / store_url 반환
    """
    share_id = str(uuid.uuid4())

    payload = {
        "user_id": b.user_id,
        "title": b.title,
        "summary": b.summary or "",
    }
    # JSON 형태로 저장
    R.set_json(f"share:{share_id}", payload)

    share_url = f"{SHARE_BASE_URL}/{share_id}"
    store_url = STORE_URL or None

    return {
        "share_id": share_id,
        "share_url": share_url,
        "store_url": store_url,
    }


@router.post("/claim")
def share_claim(b: ShareClaimBody):
    """
    공유 보상 지급 엔드포인트.

    - /share 에서 share_id를 생성하고, 사용자는 실제로 메시지를 공유 후
      앱 내에서 '보상 받기' 버튼을 눌렀을 때 이 API를 호출한다.
    - 동일 share_id 중복 차단
    - 하루 2회 한도(+1씩)
    """
    # 1) 존재하는 share_id 인지 확인
    if not R.get(f"share:{b.share_id}"):
        raise HTTPException(status_code=404, detail="INVALID_SHARE_ID")

    # 2) 이미 이 share_id로 보상 받은 적 있는지 확인
    if R.get(f"claim:{b.share_id}"):
        raise HTTPException(status_code=409, detail="ALREADY_CLAIMED")

    # 3) 하루 2회 초과인지 확인 + 티켓 지급
    ok = S.grant_share_daily(b.user_id, amount=1, daily_limit=2)
    if not ok:
        raise HTTPException(status_code=429, detail="DAILY_SHARE_LIMIT")

    # 4) 이 share_id는 사용 완료 표시
    R.set(f"claim:{b.share_id}", b.user_id)

    return {"ok": True}
