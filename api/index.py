from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re

app = FastAPI()

# ... (کدهای HTML) ...

@app.get("", response_class=HTMLResponse)  # مسیر ریشه بدون اسلش
async def root():
    return HTML_PAGE

@app.post("/process")  # مسیر API بدون اسلش انتهایی
async def process_text(input: TextInput):
    result = re.sub(r'\s+', ' ', input.text).strip()
    return {"success": True, "text": result}

handler = Mangum(app)
