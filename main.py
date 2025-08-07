from fastapi import FastAPI
from routers import analyze, share

app = FastAPI()

# 라우터 등록
app.include_router(analyze.router)
app.include_router(share.router)
