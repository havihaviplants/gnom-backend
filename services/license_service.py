# services/license_service.py
import datetime as dt
from typing import Optional, Tuple

from dependencies import get_store

def _today_str(tz: dt.tzinfo | None = None) -> str:
    return dt.datetime.now(tz).strftime("%Y%m%d")

class LicenseStore:
    """
    - free: 최초 부트스트랩 무료권(예: 2)
    - ticket: 1회권
    - pass_until: ISO datetime (패스 만료 시각)
    - 공유 보상: 하루 +1, 최대 2회
    """
    def __init__(self):
        self.R = get_store()

    # ---- 내부 KV 유틸 ----
    def _k(self, user_id: str, name: str) -> str:
        return f"user:{user_id}:{name}"

    def _get_int(self, key: str) -> int:
        v = self.R.get(key)
        try:
            return int(v)
        except Exception:
            return 0

    def _set_int(self, key: str, val: int):
        self.R.set(key, str(val))

    # ---- 상태 ----
    def status(self, user_id: str) -> dict:
        free = self._get_int(self._k(user_id, "free"))
        ticket = self._get_int(self._k(user_id, "ticket"))
        pass_until = self.R.get(self._k(user_id, "pass_until"))
        pass_active = False
        if pass_until:
            try:
                until = dt.datetime.fromisoformat(pass_until)
                pass_active = until > dt.datetime.utcnow()
            except Exception:
                pass_active = False
        return {
            "free": free,
            "ticket": ticket,
            "pass_active": pass_active,
            "pass_until": pass_until or "",
        }

    # ---- 초기 지급 ----
    def bootstrap(self, user_id: str, free_default: int = 2):
        key = self._k(user_id, "boot")
        if self.R.get(key):
            return
        self._set_int(self._k(user_id, "free"), free_default)
        self.R.set(key, "1")

    # ---- 소비/검증 ----
    def has_token(self, user_id: str) -> bool:
        st = self.status(user_id)
        return st["free"] > 0 or st["ticket"] > 0 or st["pass_active"]

    def consume_one(self, user_id: str) -> bool:
        # 패스 우선 소모 X (패스는 카운트 안 줄음) → free → ticket 순
        st = self.status(user_id)
        if st["pass_active"]:
            return True
        if st["free"] > 0:
            self._set_int(self._k(user_id, "free"), st["free"] - 1)
            return True
        if st["ticket"] > 0:
            self._set_int(self._k(user_id, "ticket"), st["ticket"] - 1)
            return True
        return False

    # ---- 지급 계열 (IAP/공유) ----
    def grant_ticket(self, user_id: str, amount: int = 1):
        cur = self._get_int(self._k(user_id, "ticket"))
        self._set_int(self._k(user_id, "ticket"), cur + max(0, amount))

    def activate_pass(self, user_id: str, days: int = 7):
        now = dt.datetime.utcnow()
        until = now + dt.timedelta(days=days)
        self.R.set(self._k(user_id, "pass_until"), until.isoformat())

    def grant_share_daily(self, user_id: str, amount: int = 1, daily_limit: int = 2) -> bool:
        # 하루 합계가 daily_limit 넘으면 False
        today = _today_str()
        kcnt = f"sharecnt:{user_id}:{today}"
        cur = self._get_int(kcnt)
        if cur >= daily_limit:
            return False
        # 지급
        self.grant_ticket(user_id, amount=amount)
        self._set_int(kcnt, cur + 1)
        return True
