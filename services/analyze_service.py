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

# 🧠 Redis 클라이언트 설정 (URL → 분리형 순)
try:
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    else:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
except Exception as e:
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
    if not redis_client:
        return True  # Redis 미연결 시 제한 없이 허용

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


def analyze_emotion(message: str) -> dict:
    prompt = generate_prompt(message)

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

    # 혹시 모를 마크다운 제거 (예방용)
    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(content)
        emotions = parsed.get("emotions", [])
        reason = parsed.get("reason", "")
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT 응답 JSON 파싱 실패: {e}\n내용:\n{content}")

    return {
        "emotion": emotions,
        "insight": reason,
        "tone": "해석 중",  # 필요 시 추가 분석
        "summary": content
    }
