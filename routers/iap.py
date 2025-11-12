# routers/iap.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
from services.license_service import LicenseStore

router = APIRouter(prefix="/iap", tags=["iap"])
S = LicenseStore()

ALLOWED_PRODUCTS = {
    "gnom.one_time": "consumable",
    "gnom.pass_7d": "subscription",
}

class VerifyBody(BaseModel):
    user_id: str
    platform: str
    product_id: str
    token: Optional[str] = None
    purchase_token: Optional[str] = None
    receipt: Optional[str] = None
    type: Optional[Literal["consumable", "subscription"]] = None

@router.post("/verify")
def verify(b: VerifyBody):
    try:
        if b.product_id not in ALLOWED_PRODUCTS:
            raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT")
        token = b.token or b.purchase_token or b.receipt
        if not token:
            raise HTTPException(status_code=422, detail="token missing")
        t = b.type or ALLOWED_PRODUCTS[b.product_id]
        if b.product_id == "gnom.one_time":
            S.grant_ticket(b.user_id, amount=1)
        elif b.product_id == "gnom.pass_7d":
            S.activate_pass(b.user_id, days=7)
        return {"ok": True, "type": t}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"VERIFY_FAILED: {e}")
