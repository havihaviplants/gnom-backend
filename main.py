# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import share, iap
from routers import analyze, license as license_router  # 프로젝트에 맞게 포함

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(share.router)
app.include_router(iap.router)
app.include_router(license_router.router)
app.include_router(analyze.router)

@app.get("/health")
def health():
    return {"ok": True}
