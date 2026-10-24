from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.post("/process")
async def process_text_endpoint(input: TextInput):
    try:
        result = re.sub(r'\s+', ' ', input.text).strip()
        return {"success": True, "text": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok"}
