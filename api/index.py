from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str

HTML_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>پردازش متن</title>
<style>
body{font-family:Tahoma,Arial,sans-serif;max-width:800px;margin:40px auto;padding:20px;background:#f9f9f9}
h2{color:#333}
textarea{width:100%;height:300px;padding:12px;font-size:14px;border:1px solid #ccc;border-radius:8px;resize:vertical;overflow-y:auto;direction:auto;box-sizing:border-box}
button{margin-top:12px;padding:10px 24px;font-size:16px;background:#0070f3;color:white;border:none;border-radius:6px;cursor:pointer}
button:hover{background:#005bb5}
#output{margin-top:20px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;min-height:100px;white-space:pre-wrap;direction:auto}
</style>
</head>
<body>
<h2>متن خود را وارد کنید</h2>
<textarea id="inputText" placeholder="متن فارسی، انگلیسی، عربی یا ترکی را اینجا بنویسید..."></textarea>
<br>
<button onclick="sendText()">پردازش متن</button>
<h3>خروجی:</h3>
<div id="output"></div>
<script>
async function sendText(){
  const t=document.getElementById('inputText').value;
  const o=document.getElementById('output');
  o.textContent='در حال پردازش...';
  try{
    const r=await fetch('/api/process',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
    const d=await r.json();
    o.textContent=d.success?d.text:'خطا: '+(d.error||'ناشناخته');
  }catch(e){o.textContent='خطای شبکه: '+e.message}
}
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(HTML_PAGE)

@app.post("/api/process")
async def process_text_endpoint(input: TextInput):
    try:
        result = re.sub(r'\s+', ' ', input.text).strip()
        return {"success": True, "text": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/api/health")
async def health():
    return {"status": "ok"}
