from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.license_service import LicenseStore

router = APIRouter(prefix="/license", tags=["license"])
S = LicenseStore()

class UserBody(BaseModel):
    user_id: str

@router.post("/bootstrap")
def bootstrap(b: UserBody):
    return S.bootstrap_free(b.user_id)

@router.post("/status")
def status(b: UserBody):
    return S.status(b.user_id)

@router.post("/consume")
def consume(b: UserBody):
    ok = S.consume_one(b.user_id)
    if not ok:
        raise HTTPException(402, "NO_ACCESS")
    return {"ok": True}
