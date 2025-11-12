# services/prompt_loader.py
import os
from pathlib import Path
from functools import lru_cache

# 기본 폴더: 프로젝트 루트의 /prompts
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", Path(__file__).resolve().parent.parent / "prompts"))

def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@lru_cache(maxsize=64)
def load_prompt(name: str) -> str:
    """
    prompts/<name>.(md|txt) 를 찾아서 로드.
    동일 이름을 자주 읽으면 캐시가 붙음(배포/재기동 시 캐시 리셋).
    """
    candidates = [PROMPTS_DIR / f"{name}.md", PROMPTS_DIR / f"{name}.txt"]
    for p in candidates:
        if p.exists():
            return _read_text(p)
    raise FileNotFoundError(f"prompt not found: {name} in {PROMPTS_DIR}")

def list_prompts() -> list[str]:
    if not PROMPTS_DIR.exists():
        return []
    out = []
    for p in PROMPTS_DIR.glob("*"):
        if p.suffix in {".md", ".txt"}:
            out.append(p.stem)
    return sorted(out)
