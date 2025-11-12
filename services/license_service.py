# back/services/license_service.py
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from dependencies import get_store

UTC = timezone.utc

class LicenseStore:
    def __init__(self):
        self.r = get_store()

    # Key schema
    def k_free(self, u: str) -> str: return f"free:{u}"                 # int
    def k_ticket(self, u: str) -> str: return f"ticket:{u}"             # int
    def k_pass(self, u: str) -> str: return f"pass:{u}"                 # json {"active": bool, "until": iso}
    def k_share_cnt_day(self, u: str, day: str) -> str: return f"sharecnt:{u}:{day}"  # 일일 리워드 횟수

    # --- helpers
    def _now(self) -> datetime:
        return datetime.now(tz=UTC)

    def _daykey(self) -> str:
        return self._now().strftime("%Y-%m-%d")

    def _load_pass(self, user_id: str) -> Dict[str, Any]:
        raw = self.r.get(self.k_pass(user_id))
        if not raw:
            return {"active": False, "until": None}
        try:
            data = json.loads(raw)
        except:
            data = {"active": False, "until": None}
        # 만료 판정
        if data.get("active") and data.get("until"):
            try:
                until = datetime.fromisoformat(data["until"])
            except:
                until = None
            if not until or self._now() >= until:
                data = {"active": False, "until": None}
                self.r.set(self.k_pass(user_id), json.dumps(data))
        return data

    # --- public APIs used by routers

    def bootstrap_free(self, user_id: str) -> Dict[str, Any]:
        # 최초 진입 시 무료 2회 지급(이미 있으면 보존)
        if self.r.get(self.k_free(user_id)) is None:
            self.r.set(self.k_free(user_id), "2")
        if self.r.get(self.k_ticket(user_id)) is None:
            self.r.set(self.k_ticket(user_id), "0")
        if self.r.get(self.k_pass(user_id)) is None:
            self.r.set(self.k_pass(user_id), json.dumps({"active": False, "until": None}))
        return self.status(user_id)

    def status(self, user_id: str) -> Dict[str, Any]:
        p = self._load_pass(user_id)
        free = int(self.r.get(self.k_free(user_id)) or "0")
        ticket = int(self.r.get(self.k_ticket(user_id)) or "0")
        return {
            "free": free,
            "ticket": ticket,
            "pass_active": bool(p.get("active")),
            "pass_until": p.get("until"),
        }

    def grant_one_time(self, user_id: str, amount: int = 1):
        n = int(self.r.get(self.k_ticket(user_id)) or "0")
        self.r.set(self.k_ticket(user_id), str(n + int(amount)))

    def grant_pass_days(self, user_id: str, days: int):
        # days가 0 이하면 즉시 만료 처리
        base = self._now()
        until = base + timedelta(days=max(days, 0))
        if days <= 0:
            data = {"active": False, "until": None}
        else:
            data = {"active": True, "until": until.isoformat()}
        self.r.set(self.k_pass(user_id), json.dumps(data))

    def grant_share_daily(self, user_id: str, amount: int = 1, daily_limit: int = 2) -> bool:
        key = self.k_share_cnt_day(user_id, self._daykey())
        cnt = int(self.r.get(key) or "0")
        if cnt >= daily_limit:
            return False
        new_cnt = cnt + 1
        self.r.set(key, str(new_cnt), ttl_seconds=24*60*60)
        cur = int(self.r.get(self.k_free(user_id)) or "0")
        self.r.set(self.k_free(user_id), str(cur + int(amount)))
        return True


    def consume_one(self, user_id: str) -> bool:
        # pass > ticket > free
        st = self.status(user_id)
        if st["pass_active"]:
            return True
        t = int(self.r.get(self.k_ticket(user_id)) or "0")
        if t > 0:
            self.r.set(self.k_ticket(user_id), str(t - 1))
            return True
        f = int(self.r.get(self.k_free(user_id)) or "0")
        if f > 0:
            self.r.set(self.k_free(user_id), str(f - 1))
            return True
        return False
