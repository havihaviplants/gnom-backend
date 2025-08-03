# main.py

from fastapi import FastAPI
from routers import analyze
from routers import share  # ✅ 추가된 라우터

app = FastAPI()

# 라우터 등록
app.include_router(analyze.router)
app.include_router(share.router)
