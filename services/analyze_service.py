
import os
import openai
from prompts.analyze_prompt import generate_prompt
from dotenv import load_dotenv
import redis
from datetime import datetime, timedelta

# 하루 호출 제한 수
MAX_CALLS_PER_DAY = 3

# .env 파일 로드
load_dotenv()

# Redis 환경변수 가져오기
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")

# Redis 클라이언트 설정
if redis_host and redis_port and redis_db:
    redis_client = redis.Redis(
        host=redis_host,
        port=int(redis_port),
        db=int(redis_db),
        decode_responses=True
    )
else:
    redis_client = None  # 환경변수 없을 경우 None 처리

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_today_key(user_id: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"call_count:{user_id}:{today}"


def get_seconds_until_midnight() -> int:
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())


def check_and_increment_call_count(user_id: str) -> bool:
    if not redis_client:
        return True  # Redis 미연결 시 제한 없이 허용 (또는 False 처리 가능)

    unlock_key = f"call_unlocked:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
    if redis_client.get(unlock_key):
        return True

    key = get_today_key(user_id)
    count = redis_client.get(key)

    if count is None:
        redis_client.set(key, 1, ex=get_seconds_until_midnight())
        return True
    else:
        count = int(count)
        if count >= MAX_CALLS_PER_DAY:
            return False
        else:
            redis_client.incr(key)
            return True


def analyze_emotion(message: str) -> dict:
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

    # 결과 응답 구조화
    content = response.choices[0].message.content

    return {
        "emotion": "추출 필요",
        "insight": "추출 필요",
        "tone": "추출 필요",
        "summary": content
    }
