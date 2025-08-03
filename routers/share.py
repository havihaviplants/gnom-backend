# gnom-backend/routers/share.py

from fastapi import APIRouter, HTTPException
import uuid, json
import redis

router = APIRouter()

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

@router.post("/share")
def create_share(data: dict):
    share_id = str(uuid.uuid4())[:8]
    r.setex(f"share:{share_id}", 60*60*24*30, json.dumps(data))  # 30일 TTL
    return {"share_url": f"https://gnom.ai/share/{share_id}"}

@router.get("/share/{share_id}")
def get_share(share_id: str):
    raw = r.get(f"share:{share_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Not found")
    return json.loads(raw)
