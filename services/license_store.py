from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

class _MemStore:
    def __init__(self):
        self.data: Dict[str, dict] = {}

    def get(self, user_id: str) -> dict:
        if user_id not in self.data:
            self.data[user_id] = {
                "remaining_tokens": 0,
                "pass_active": False,
                "pass_expire_at": None,  # ISO string
            }
        return self.data[user_id]

    def set(self, user_id: str, payload: dict):
        self.data[user_id] = payload

STORE = _MemStore()

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat().replace("+00:00", "Z") if dt else None

def add_days(d: int) -> datetime:
    return now_utc() + timedelta(days=d)
