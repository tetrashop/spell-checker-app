from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str

def process_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text

@app.post("/api/process")
async def process_text_endpoint(input: TextInput):
    try:
        result = process_text(input.text)
        return {"success": True, "text": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/api/health")
async def health():
    return {"status": "ok"}
