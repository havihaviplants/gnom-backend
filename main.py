from fastapi import FastAPI
from routers import analyze
from routers import share   # ✅ 추가


app = FastAPI()

app.include_router(analyze.router)
app.include_router(share.router)  # ✅ 추가
