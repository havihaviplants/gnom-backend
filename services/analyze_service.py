# services/analyze_service.py
from __future__ import annotations

import os
import json
import time
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta, timezone

# ---- 타임존 & 토글 -----------------------------------------------------------
KST = timezone(timedelta(hours=9))  # Asia/Seoul (DST 없음)
LIMIT_ENABLED = os.getenv("ANALYZE_LIMIT_ENABLED", "false").lower() == "true"

# ---- Redis(선택) -------------------------------------------------------------
# Render에 Redis 애드온/외부 Redis를 붙였다면 REDIS_URL 환경변수를 설정하세요.
_redis = None
_redis_err = None
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    try:
        import redis
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
        # 간단 헬스 체크
        _redis.ping()
    except Exception as e:
        _redis = None
        _redis_err = e  # 참고용

# ---- OpenAI SDK 어댑터 -------------------------------------------------------
# v1 SDK (openai>=1.0.0): from openai import OpenAI
# v0 SDK (openai<1.0.0): import openai; openai.ChatCompletion.create(...)
_OPENAI_CLIENT_V1 = None
_OPENAI_LEGACY = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 필요 시 바꾸세요

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

try:
    # v1
    from openai import OpenAI  # type: ignore

    _OPENAI_CLIENT_V1 = OpenAI()
except Exception:
    # v0
    try:
        import openai  # type: ignore
        _OPENAI_LEGACY = openai
        if OPENAI_API_KEY:
            _OPENAI_LEGACY.api_key = OPENAI_API_KEY
    except Exception:
        _OPENAI_LEGACY = None


# =============================================================================
# 유틸
# =============================================================================
def get_seconds_until_midnight(tz: timezone = KST) -> int:
    """
    tz(기본 KST) 기준 '다음 자정'까지 남은 초.
    일일 리셋 TTL 등에 사용.
    """
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).date()
    next_midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    delta = next_midnight - now
    return max(0, int(delta.total_seconds()))


def _limit_key(user_id: Optional[str], scope: str = "analyze") -> str:
    """
    레이트리밋 키 생성. user_id 없으면 IP 등 상위 레벨에서 다루되,
    여기서는 안전하게 anonymous로 폴백.
    """
    uid = user_id or "anonymous"
    today = datetime.now(KST).strftime("%Y%m%d")
    return f"limit:{scope}:{today}:{uid}"


def _redis_incr_with_ttl(key: str, ttl_seconds: int) -> int:
    """
    Redis 카운터 증가 + 첫 증가 시 TTL 설정. Redis 없으면 메모리 대체(임시).
    """
    if _redis is not None:
        # 원자적 증가
        count = _redis.incr(key)
        # 새 키면 TTL 설정
        if count == 1:
            _redis.expire(key, ttl_seconds)
        return int(count)

    # Redis가 없으면 프로세스 단 메모리로 폴백 (재시작 시 초기화됨)
    # -> 운영용이 아니라 '부팅 안정성'을 위한 임시 대안
    if not hasattr(_redis_incr_with_ttl, "_mem"):
        setattr(_redis_incr_with_ttl, "_mem", {})
        setattr(_redis_incr_with_ttl, "_exp", {})
    mem = getattr(_redis_incr_with_ttl, "_mem")
    exp = getattr(_redis_incr_with_ttl, "_exp")
    now = time.time()

    # 만료 처리
    if key in exp and now >= exp[key]:
        mem.pop(key, None)
        exp.pop(key, None)

    # 증가
    mem[key] = mem.get(key, 0) + 1
    if key not in exp:
        exp[key] = now + ttl_seconds
    return mem[key]


# =============================================================================
# 레이트 리밋
# =============================================================================
def _check_and_increment_call_count_real(user_id: Optional[str]) -> Tuple[bool, int]:
    """
    실제 카운팅 로직. 일일 리셋(KST 자정).
    기본 한도: 하루 30회 (환경변수로 조절 가능).
    """
    try:
        daily_limit = int(os.getenv("DAILY_ANALYZE_LIMIT", "30"))
    except Exception:
        daily_limit = 30

    ttl = get_seconds_until_midnight()
    key = _limit_key(user_id, scope="analyze")
    current = _redis_incr_with_ttl(key, ttl)

    return (current <= daily_limit, current)


def check_and_increment_call_count(user_id: Optional[str]) -> Tuple[bool, int]:
    """
    라우터에서 항상 import 가능한 퍼블릭 API.
    LIMIT_ENABLED=False면 무조건 허용 (안정적 부팅 우선).
    """
    if not LIMIT_ENABLED:
        return True, 0
    return _check_and_increment_call_count_real(user_id)


# =============================================================================
# 프롬프트 & 파서
# =============================================================================
def _build_prompt(message: str, relationship: str) -> str:
    """
    너가 지향한다고 한 '프롬프트 엔지니어링 업데이트' 방향을 반영:
    - 출력 스키마 고정
    - 한국어/간결/유용
    - 지나친 조언 금지, 감정·맥락 분리
    """
    return f"""
당신은 '관계 기반 감정 해석' 전문 AI입니다. 
입력 메시지를 읽고, 발신자의 감정/의도/맥락을 과도한 추측 없이 해석하세요.
출력은 반드시 JSON 스키마로만 응답합니다(설명, 주석, 추가 문장 금지).

[입력]
- 관계: {relationship}
- 메시지: {message}

[지침]
- 해석 문장은 3~5문장, 한국어, 과장/단정 금지.
- 한 줄 통찰은 함축적으로, "핵심 신호"를 요약.
- tags: 감정/상태를 1~3개. (예: "서운함","혼란","거리두기","방어")
- emojis: 메시지 정서와 맞는 이모지 3개.
- 절대 개인정보, 의료/법률/투자 조언 금지.
- 반드시 아래 JSON 스키마만 출력:

{{"interpretation": "...", "insight": "...", "tags": ["..."], "emojis": ["...","...","..."]}}
""".strip()


def _safe_parse_json(text: str) -> Dict[str, Any]:
    """
    모델 응답에서 JSON 추출/검증.
    """
    # 가장 바깥 { ... } 덩어리만 파싱 시도
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("모델 응답에서 JSON 블록을 찾지 못했습니다.")
    raw = text[start : end + 1]
    data = json.loads(raw)

    # 필드 보정
    interp = str(data.get("interpretation", "")).strip()
    insight = str(data.get("insight", "")).strip()
    tags = data.get("tags", [])
    emojis = data.get("emojis", [])

    if not isinstance(tags, list):
        tags = []
    if not isinstance(emojis, list):
        emojis = []

    # 이모지 3개 보정
    if len(emojis) < 3:
        emojis = (emojis + ["🙂", "🤔", "🧩"])[:3]

    return {
        "interpretation": interp or "메시지의 정서가 불분명합니다. 추가 문맥이 필요할 수 있어요.",
        "insight": insight or "표면 감정과 숨은 목적을 섣불리 혼동하지 마세요.",
        "tags": [str(t) for t in tags][:3],
        "emojis": [str(e) for e in emojis][:3],
    }


# =============================================================================
# OpenAI 호출
# =============================================================================
def _call_openai(prompt: str) -> Dict[str, Any]:
    """
    v1, v0 SDK 모두 지원. 실패 시 예외 발생.
    """
    if not OPENAI_API_KEY:
        # 키가 없으면 더미 응답 (부팅/개발 안정성)
        return {
            "interpretation": "API 키 미설정 상태입니다. 예시 응답입니다.",
            "insight": "환경변수 OPENAI_API_KEY를 설정하세요.",
            "tags": ["시스템"],
            "emojis": ["⚙️", "🧪", "🧩"],
        }

    # v1 SDK 우선
    if _OPENAI_CLIENT_V1 is not None:
        resp = _OPENAI_CLIENT_V1.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a structured, safe Korean assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        text = resp.choices[0].message.content or ""
        return _safe_parse_json(text)

    # v0 레거시
    if _OPENAI_LEGACY is not None:
        resp = _OPENAI_LEGACY.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a structured, safe Korean assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        text = resp["choices"][0]["message"]["content"] or ""
        return _safe_parse_json(text)

    raise RuntimeError("OpenAI SDK 초기화 실패: 라이브러리 로딩 불가")


# =============================================================================
# 퍼블릭 서비스 API (라우터에서 import)
# =============================================================================
def analyze_emotion(message: str, relationship: str) -> Dict[str, Any]:
    """
    프론트에서 기대하는 결과 형태(dict):
    {
      "interpretation": str,
      "insight": str,
      "tags": List[str],
      "emojis": List[str]
    }
    """
    if not isinstance(message, str) or not message.strip():
        return {
            "interpretation": "해석할 메시지가 비어 있습니다.",
            "insight": "상대가 보낸 실제 문장을 입력해 주세요.",
            "tags": ["입력오류"],
            "emojis": ["⚠️", "✍️", "📩"],
        }

    prompt = _build_prompt(message=message.strip(), relationship=relationship.strip())
    try:
        result = _call_openai(prompt)
        # 방어적 스키마 보정
        return {
            "interpretation": str(result.get("interpretation", "")),
            "insight": str(result.get("insight", "")),
            "tags": list(result.get("tags", []))[:3],
            "emojis": list(result.get("emojis", []))[:3],
        }
    except Exception as e:
        # 모델/네트워크 오류 시 안전한 폴백
        return {
            "interpretation": "해석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "insight": f"원인: {type(e).__name__}",
            "tags": ["시스템오류"],
            "emojis": ["🛠️", "⏳", "🔁"],
        }
