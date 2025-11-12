# back/dependencies.py
import time
import json
from typing import Any, Optional

_STORE = {}  # { key: {"val": str, "exp": int|None} }

def now_ts() -> int:
    return int(time.time())

class MemoryStore:
    def get(self, key: str) -> Optional[str]:
        item = _STORE.get(key)
        if not item:
            return None
        exp = item.get("exp")
        if exp and now_ts() >= exp:
            _STORE.pop(key, None)
            return None
        return item.get("val")

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None):
        exp = now_ts() + int(ttl_seconds) if ttl_seconds else None
        _STORE[key] = {"val": value, "exp": exp}

    def set_json(self, key: str, obj: Any, ttl_seconds: Optional[int] = None):
        self.set(key, json.dumps(obj), ttl_seconds)

    def get_json(self, key: str) -> Any:
        raw = self.get(key)
        return json.loads(raw) if raw else None

    def incr(self, key: str, ttl_seconds: Optional[int] = None) -> int:
        v = self.get(key)
        try:
            n = int(v) if v is not None else 0
        except:
            n = 0
        n += 1
        self.set(key, str(n), ttl_seconds)
        return n

def get_store() -> MemoryStore:
    return MemoryStore()
