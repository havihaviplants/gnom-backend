# routers/analyze.py
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.prompt_loader import load_prompt
from services.license_service import LicenseStore

# OpenAI SDK v1
from openai import OpenAI

router = APIRouter(prefix="", tags=["analyze"])
S = LicenseStore()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 필요 모델로 교체 가능
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AnalyzeBody(BaseModel):
    message: str
    # 필요시 옵션 확장
    lang: Optional[str] = "ko"

class AnalyzeResp(BaseModel):
    interpretation: str
    insight: str
    tags: list[str]
    emojis: list[str]

def _build_system_prompt(lang: str = "ko") -> str:
    """
    prompts 폴더에서 'system'과 'schema' 두 파일을 합쳐 시스템 메시지로 사용.
    - 없으면 안전한 기본값 사용
    """
    try:
        system_core = load_prompt("system")
    except FileNotFoundError:
        system_core = (
            "You are Gnom AI, an emotion analysis assistant. "
            "Return short, structured emotional insights in Korean."
        )
    try:
        schema = load_prompt("schema")  # 예: 출력 형식 안내
    except FileNotFoundError:
        schema = (
            "Output keys (Korean labels):\n"
            "- 감정해석\n- 한 줄 통찰\n- 감정 분류(콤마 구분)\n- 이모지(공백 구분)\n"
        )
    return f"{system_core}\n\n[LANG={lang}]\n\n{schema}"

def _parse_to_struct(raw_text: str) -> AnalyzeResp:
    """
    모델 출력이 포맷이 조금 달라도 최대한 구조화.
    간단한 파서(규칙 기반) — 필요시 JSON 모드로 바꿔도 됨.
    """
    text = raw_text.strip()
    # 아주 단순 파싱
    def _find(label: str) -> str:
        import re
        pat = rf"{label}\s*[:：]\s*(.+)"
        m = re.search(pat, text)
        return m.group(1).strip() if m else ""

    interp = _find("감정해석") or _find("해석")
    insight = _find("한 줄 통찰") or _find("통찰")
    tags = (_find("감정 분류") or _find("분류")).replace("·", ",").replace(" ", "")
    emojis = _find("이모지")

    out = AnalyzeResp(
        interpretation=interp or text[:150],
        insight=insight or "",
        tags=[t for t in tags.split(",") if t] if tags else [],
        emojis=[e for e in emojis.split() if e] if emojis else []
    )
    return out

@router.post("/analyze", response_model=AnalyzeResp)
def analyze(b: AnalyzeBody):
    # 사용권 확인(권장: 라우터 앞단에서 consumeOne을 호출했다면 여기선 상태만 확인)
    st = S.status(b.message[:16])  # 예: 내부 추적 id 대체 — 실제로는 사용자 ID로 확인
    # (여기선 단순화 — 실제 서비스는 user_id 기반 권한 확인 사용 권장)

    if not os.getenv("OPENAI_API_KEY"):
        # 키 없을 때 예시 응답(네가 보던 문구)을 여전히 유지하되, 200으로 내려주지 말고 400~401로 명확화해도 됨.
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY_NOT_SET")

    system_prompt = _build_system_prompt(b.lang or "ko")
    user_prompt = load_prompt("user") if "user" in set() else ""  # 필요 시 user 템플릿 사용
    content = f"{user_prompt}\n\n[INPUT]\n{b.message}".strip()

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.3,
        )
        txt = resp.choices[0].message.content or ""
        return _parse_to_struct(txt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MODEL_ERROR: {e}")
