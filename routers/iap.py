# routers/iap.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from .license import get_or_create_license  # 같은 패키지 사용 시 상대 import 경로 맞추세요

router = APIRouter(prefix="/iap", tags=["iap"])

def get_user_id():
    return "demo-user"

class VerifyRequest(BaseModel):
    orderId: str | None = None
    productId: str
    purchaseToken: str | None = None
    transactionReceipt: str | None = None

@router.post("/verify")
def verify(req: VerifyRequest, user_id: str = Depends(get_user_id)):
    # TODO: 실제 스토어 영수증 검증 로직 (Google/Apple API 호출) 추가
    lic = get_or_create_license(user_id)
    now = datetime.now(timezone.utc)

    if req.productId == "gnom_ticket_1":
        lic["remaining"] += 1
    elif req.productId == "gnom_pass_7":
        expire = now + timedelta(days=7)
        if lic["pass_expire"] and lic["pass_expire"] > now:
            lic["pass_expire"] = max(lic["pass_expire"], expire)
        else:
            lic["pass_expire"] = expire
    else:
        raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT")

    # TODO: 영수증 재사용 방지 저장(mark used)
    return {"ok": True}
