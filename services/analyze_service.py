import os
import openai
from prompts.analyze_prompt import generate_prompt
from dotenv import load_dotenv
import redis
from datetime import datetime, timedelta

MAX_CALLS_PER_DAY = 3

def get_today_key(user_id: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"call_count:{user_id}:{today}"

def get_seconds_until_midnight() -> int:
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())

def check_and_increment_call_count(user_id: str) -> bool:
     # 🔓 광고 해제 플래그 먼저 확인
    unlock_key = f"call_unlocked:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
    if redis_client.get(unlock_key):
        return True
    key = get_today_key(user_id)
    count = redis_client.get(key)

    if count is None:
        # 첫 호출: 1로 설정하고 자정까지 TTL 지정
        redis_client.set(key, 1, ex=get_seconds_until_midnight())
        return True
    else:
        count = int(count)
        if count >= MAX_CALLS_PER_DAY:
            return False
        else:
            redis_client.incr(key)
            return True



load_dotenv()

# Redis 연결
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    db=int(os.getenv("REDIS_DB"))
)

api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")  # 또는 .env에서 가져오기

def analyze_emotion_logic(message: str) -> str:
    prompt = generate_prompt(message)

    response = openai.chatcompletions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "감정 분석 전문가로 행동하세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=300
    )

    return response.choices[0].message.content
