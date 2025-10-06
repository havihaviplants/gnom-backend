from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analyze, share

app = FastAPI(
    title="Gnom Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: Dev Client/웹 프론트 실험을 위해 허용 폭 넓게
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요 시 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 장착
app.include_router(analyze.router)
app.include_router(share.router)

@app.get("/")
def health():
    return {"status": "ok", "service": "gnom-backend"}
