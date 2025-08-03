from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    message: str

class AnalyzeResponse(BaseModel):
    result: str
