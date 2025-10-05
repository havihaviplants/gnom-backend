# === 상단 import/설정 인근에 추가 ===
import re
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from prompts.analyze_prompt import generate_prompt
import openai

# 권장: 가성비+퀄
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 필요 시 env로 바꿔치기
FALLBACK_MODEL = "gpt-3.5-turbo"  # 폴백

# --- 섹션 포맷 파서 ---
SECTION_RE = {
    "interpretation": r"\[감정 해석\]\s*(.+?)(?=\n\[|$)",
    "insight":        r"\[한 줄 통찰\]\s*(.+?)(?=\n\[|$)",
    "tags":           r"\[감정 분류\]\s*(.+?)(?=\n\[|$)",
    "emojis":         r"\[이모지\]\s*(.+?)(?=\n\[|$)",
}

def _clean_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*", "", s).strip()
        s = re.sub(r"```$", "", s).strip()
    return s

def _parse_sections(text: str) -> dict:
    def pick(pat):
        m = re.search(pat, text, re.S)
        return (m.group(1).strip() if m else "")

    interpretation = pick(SECTION_RE["interpretation"])
    insight        = pick(SECTION_RE["insight"])
    raw_tags       = pick(SECTION_RE["tags"])
    raw_emojis     = pick(SECTION_RE["emojis"])

    # 태그: 쉼표/공백 구분 → 최대 3개
    tags = [t.strip() for t in re.split(r"[,\s]+", raw_tags) if t.strip()][:3]
    # 이모지: 문자 단위 추출(간단형)
    emojis = [e for e in list(raw_emojis) if e.strip()][:3]

    if len(emojis) < 3:
        emojis += ["💬"] * (3 - len(emojis))

    return {
        "interpretation": interpretation or "감정 해석을 생성하지 못했습니다.",
        "insight": insight or "추가 인사이트 없음.",
        "tags": tags or ["중립"],
        "emojis": emojis
    }

def _parse_jsonish(content: str) -> dict | None:
    """```json fenced / 느슨한 JSON도 최대한 파싱"""
    s = _clean_fence(content)
    try:
        obj = json.loads(s)
    except Exception:
        return None

    # 허용 키: 신(새)스키마 우선
    if all(k in obj for k in ("interpretation","insight","tags","emojis")):
        return {
            "interpretation": str(obj.get("interpretation") or "").strip(),
            "insight": str(obj.get("insight") or "").strip(),
            "tags": list(obj.get("tags") or [])[:3],
            "emojis": list(obj.get("emojis") or [])[:3] or ["💬","💬","💬"],
        }

    # 구(옛)스키마(emotions/reason)도 수용
    if "emotions" in obj or "reason" in obj:
        tags = list(obj.get("emotions") or [])[:3]
        reason = str(obj.get("reason") or "").strip()
        emojis = ["💬","💬","💬"]
        return {
            "interpretation": reason or "감정 해석을 생성하지 못했습니다.",
            "insight": (reason[:60] + "...") if reason else "추가 인사이트 없음.",
            "tags": tags or ["중립"],
            "emojis": emojis
        }

    return None


def analyze_emotion(message: str, relationship: str) -> dict:
    """
    반환 스키마(프론트 최종 기대치):
    {
      "interpretation": str,
      "insight": str,
      "tags": List[str](<=3),
      "emojis": List[str](==3)
    }
    """
    prompt = generate_prompt(message, relationship)
    print("🧪 [PROMPT]\n", prompt)

    def _call(model_name: str):
        return openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "감정 분석 전문가로 행동하세요. "
                        "반드시 아래 섹션 형식 혹은 JSON으로만 응답하세요:\n"
                        "1) 섹션 형식:\n"
                        "[감정 해석]\\n...\\n[한 줄 통찰]\\n...\\n[감정 분류]\\nA, B, C\\n[이모지]\\n🧩🧩🧩\n"
                        "2) JSON 형식:\n"
                        '{"interpretation":"...","insight":"...","tags":["A","B"],"emojis":["😀","...","..."]}'
                    ),
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=400,
        )

    try:
        # 1차: 업그레이드 모델
        try:
            response = _call(OPENAI_MODEL)
        except Exception as e1:
            print("[GPT REQUEST ERROR - primary]", str(e1))
            # 2차: 폴백
            response = _call(FALLBACK_MODEL)

        content = response["choices"][0]["message"]["content"].strip()
        print("🧪 [GPT 응답]\n", content)

        # 우선 JSON 파싱 시도 → 실패하면 섹션 파싱
        parsed = _parse_jsonish(content)
        if not parsed:
            parsed = _parse_sections(content)

        # 결과 정규화(보호막)
        interpretation = (parsed.get("interpretation") or "").strip() or "감정 해석을 생성하지 못했습니다."
        insight = (parsed.get("insight") or "").strip() or "추가 인사이트 없음."
        tags = list(parsed.get("tags") or [])[:3]
        emojis = list(parsed.get("emojis") or [])[:3]
        if len(emojis) < 3: emojis += ["💬"] * (3 - len(emojis))
        if not tags: tags = ["중립"]

        return {
            "interpretation": interpretation,
            "insight": insight,
            "tags": tags,
            "emojis": emojis
        }

    except Exception as e:
        print("[GPT REQUEST ERROR - fatal]", str(e))
        # 백엔드 예외 시에도 프론트 스키마 유지
        return {
            "interpretation": "서버 내부 오류로 해석을 제공하지 못했습니다.",
            "insight": "잠시 후 다시 시도해주세요.",
            "tags": ["중립"],
            "emojis": ["💬","💬","💬"]
        }
