from pydantic import BaseModel
from typing import Optional

class LicenseStatus(BaseModel):
    remaining_tokens: int = 0
    pass_active: bool = False
    pass_expire_at: Optional[str] = None  # ISO string
