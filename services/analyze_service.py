import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from prompts.analyze_prompt import generate_prompt

# (v1.0) 호출 제한 토글: 기본 끔
LIMIT_ENABLED = os.getenv("ANALYZE_LIMIT_ENABLED", "false").lower() == "true"

# 🔐 환경 변수 로드
load_dotenv()

# OpenAI (당신 프로젝트에 맞게 유지)
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

# redis 안전 import (없어도 앱이 죽지 않도록)
try:
    import redis  # type: ignore
except Exception:
    redis = None

# 🔌 Redis 연결 (제한 토글이 켜진 경우에만 시도)
def init_redis():
    if not LIMIT_ENABLED:
        return None
    if redis is None:
        return None
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis.from_url(redis_url, decode_responses=True)
        else:
            return redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                decode_responses=True
            )
    except Exception as e:
        print("[REDIS INIT ERROR]", str(e))
        return None

redis_client = init_redis()

# 📊 호출 제한 설정
MAX_CALLS_PER_DAY = int(os.getenv("MAX_CALLS_PER_DAY", "3"))

def get_today_key(user_id: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"call_count:{user_id}:{today}"

def get_seconds_until_midnight() -> int:
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight - now).total_seconds())

def check_and_increment_call_count(user_id: str) -> bool:
    # v1.0: 제한 끔 → 항상 허용
    if not LIMIT_ENABLED:
        return True

    # 제한을 켠 경우에만 Redis 카운트, 실패 시에도 허용
    try:
        if not redis_client:
            return True

        unlock_key = f"call_unlocked:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
        if redis_client.get(unlock_key):
            return True

        key = get_today_key(user_id)
        count = redis_client.get(key)

        if count is None:
            redis_client.set(key, 1, ex=get_seconds_until_midnight())
            return True
        elif int(count) >= MAX_CALLS_PER_DAY:
            return False
        else:
            redis_client.incr(key)
            return True

    except Exception as e:
        print("[REDIS ERROR]", str(e))
        # Redis 문제는 v1.0에서 절대 사용자를 막지 않음
        return True


# 🧠 감정 분석
def analyze_emotion(message: str, relationship: str) -> dict:
    prompt = generate_prompt(message, relationship)
    print("🧪 [PROMPT]\n", prompt)

    try:
        # ✅ 구버전 방식 사용
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "감정 분석 전문가로 행동하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )

        content = response["choices"][0]["message"]["content"].strip()
        print("🧪 [GPT 응답]\n", content)

        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(content)
            return {
                "emotions": parsed.get("emotions", []),
                "reason": parsed.get("reason", "")
            }

        except json.JSONDecodeError as e:
            print("[JSON PARSE ERROR]", str(e))
            return {
                "emotions": [],
                "reason": "GPT 응답 파싱 실패"
            }

    except Exception as e:
        print("[GPT REQUEST ERROR]", str(e))
        return {
            "emotions": [],
            "reason": "서버 내부 오류 발생"
        }
