from fastapi import FastAPI
from routers import analyze
from routers import share   # ✅ 추가
from services.analyze_service import analyze_emotion_logic as analyze_emotion



app = FastAPI()

app.include_router(analyze.router)
app.include_router(share.router)  # ✅ 추가
