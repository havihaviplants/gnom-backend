# routers/license.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.license_service import LicenseStore

router = APIRouter(prefix="/license", tags=["license"])
S = LicenseStore()  # 싱글톤처럼 재사용

class LicenseBootstrapBody(BaseModel):
    user_id: str

class LicenseStatusBody(BaseModel):
    user_id: str

class LicenseConsumeBody(BaseModel):
    user_id: str


@router.post("/bootstrap")
def license_bootstrap(b: LicenseBootstrapBody):
    """
    최초 1회 무료 2회 지급용 엔드포인트.
    이미 부트스트랩된 유저는 그냥 상태만 돌려줌.
    """
    # 부트스트랩만 수행 (리턴값 사용 X)
    S.bootstrap(b.user_id)
    # 항상 최신 상태를 반환해서 프론트에서 바로 st 세팅 가능하게.
    return S.status(b.user_id)


@router.post("/status")
def license_status(b: LicenseStatusBody):
    """
    현재 무료권/티켓/7일 패스 상태 조회.
    """
    return S.status(b.user_id)


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
