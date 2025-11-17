# routers/license.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.license_service import LicenseStore

router = APIRouter(prefix="/license", tags=["license"])
S = LicenseStore()  # 싱글톤처럼 재사용

class LicenseBootstrapBody(BaseModel):
    user_id: str

class LicenseConsumeBody(BaseModel):
    user_id: str

@router.post("/bootstrap")
def license_bootstrap(b: LicenseBootstrapBody):
    """
    최초 1회 무료 2회 지급용 엔드포인트.
    이미 뭔가 지급된 상태면 그냥 True만 돌려줌.
    """
    ok = S.bootstrap(b.user_id)  # ✅ 이름 수정: bootstrap_free -> bootstrap
    if not ok:
        raise HTTPException(status_code=500, detail="LICENSE_BOOTSTRAP_FAILED")
    return {"ok": True}

@router.post("/consume")
def license_consume(b: LicenseConsumeBody):
    """
    해석 1회 소비. free > 0 또는 ticket > 0 또는 7일패스가 있으면 통과.
    """
    ok = S.consume_one(b.user_id)
    if not ok:
        # 프론트에서는 이 코드를 보고 "사용권 없음" 문구를 보여주게 됨.
        raise HTTPException(status_code=402, detail="NO_TOKENS")
    return {"ok": True}
