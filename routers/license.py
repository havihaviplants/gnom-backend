# routers/license.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/license", tags=["license"])

# ===== 저장소 대체: 초기엔 메모리(배포 시 Redis/DB로 교체) =====
LICENSES = {}         # user_id -> {"remaining": int, "pass_expire": datetime|None}
SHARE_COUNT = {}      # (user_id, YYYYMMDD) -> int

def get_user_id():
    # TODO: JWT에서 user_id 추출 (당장은 더미)
    return "demo-user"

def today_key():
    return datetime.now(timezone.utc).strftime("%Y%m%d")

class LicenseStatus(BaseModel):
    remaining_tokens: int
    pass_active: bool
    pass_expire_at: str | None = None

def get_or_create_license(uid: str):
    if uid not in LICENSES:
        LICENSES[uid] = {"remaining": 2, "pass_expire": None}  # 최초 2회 지급
    return LICENSES[uid]

@router.get("/status", response_model=LicenseStatus)
def status(user_id: str = Depends(get_user_id)):
    lic = get_or_create_license(user_id)
    active = lic["pass_expire"] and lic["pass_expire"] > datetime.now(timezone.utc)
    return LicenseStatus(
        remaining_tokens=lic["remaining"],
        pass_active=bool(active),
        pass_expire_at=lic["pass_expire"].isoformat() if lic["pass_expire"] else None,
    )

@router.post("/consume", response_model=LicenseStatus)
def consume(user_id: str = Depends(get_user_id)):
    lic = get_or_create_license(user_id)
    now = datetime.now(timezone.utc)
    if lic["pass_expire"] and lic["pass_expire"] > now:
        # 패스 중이면 소비하지 않음
        active = True
    else:
        active = False
        if lic["remaining"] <= 0:
            raise HTTPException(status_code=402, detail="NO_TOKENS")
        lic["remaining"] -= 1
    return LicenseStatus(
        remaining_tokens=lic["remaining"], pass_active=active,
        pass_expire_at=lic["pass_expire"].isoformat() if lic["pass_expire"] else None
    )

@router.post("/reward", response_model=LicenseStatus)
def reward(user_id: str = Depends(get_user_id)):
    key = (user_id, today_key())
    cnt = SHARE_COUNT.get(key, 0)
    if cnt >= 2:
        raise HTTPException(status_code=429, detail="DAILY_LIMIT")
    SHARE_COUNT[key] = cnt + 1

    lic = get_or_create_license(user_id)
    lic["remaining"] += 1
    active = lic["pass_expire"] and lic["pass_expire"] > datetime.now(timezone.utc)
    return LicenseStatus(
        remaining_tokens=lic["remaining"],
        pass_active=bool(active),
        pass_expire_at=lic["pass_expire"].isoformat() if lic["pass_expire"] else None
    )
