from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="gnom-backend")

# CORS (필요시 도메인 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def health():
    return {"status": "ok", "service": "gnom-backend"}

# --- 라우터 장착 ---
from routers import license as license_router
from routers import iap as iap_router
# from routers import analyze as analyze_router  # 있으면 주석 해제

app.include_router(license_router.router)
app.include_router(iap_router.router)
# app.include_router(analyze_router.router)
