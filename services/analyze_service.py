import os
import openai
import redis
from dotenv import load_dotenv
from datetime import datetime, timedelta
from prompts.analyze_prompt import generate_prompt
import json

# 🔐 환경 변수 로드
load_dotenv()

# 🔑 OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🧠 Redis 클라이언트 설정 (URL → 분리형 우선)
try:
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    else:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True
        )
except Exception:
    redis_client = None  # Redis 연결 실패 시 fallback

# 📊 하루 호출 제한 수
MAX_CALLS_PER_DAY = 3

def get_today_key(user_id: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"call_count:{user_id}:{today}"

def get_seconds_until_midnight() -> int:
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())

def check_and_increment_call_count(user_id: str) -> bool:
    try:
        if not redis_client:
            return True  # Redis 미연결 시 제한 없음

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
        return True  # Redis 오류 시 제한 없이 허용 (fallback)


def analyze_emotion(message: str) -> dict:
    prompt = generate_prompt(message)

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "감정 분석 전문가로 행동하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(content)
        emotions = parsed.get("emotions", [])
        reason = parsed.get("reason", "")

        return {
            "emotion": emotions,
            "insight": reason,
            "tone": "해석 중",
            "summary": content
        }

    except json.JSONDecodeError as e:
        print("[JSON PARSE ERROR]", str(e))
        print("[GPT RESPONSE RAW]", content)
        return {
            "emotion": [],
            "insight": "GPT 응답을 파싱하는 데 실패했습니다.",
            "tone": "unknown",
            "summary": content
        }

    except Exception as e:
        print("[UNEXPECTED ERROR]", str(e))
        return {
            "emotion": [],
            "insight": "서버 오류 발생",
            "tone": "unknown",
            "summary": "분석에 실패했습니다."
        }
