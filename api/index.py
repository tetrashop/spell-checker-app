from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re

app = FastAPI()

# --- صفحه HTML ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>پردازش متن</title>
<style>
body{font-family:Tahoma;max-width:800px;margin:40px auto;padding:20px;background:#f9f9f9}
textarea{width:100%;height:300px;padding:12px;border:1px solid #ccc;border-radius:8px}
button{margin-top:12px;padding:10px 24px;background:#0070f3;color:white;border:none;border-radius:6px;cursor:pointer}
#output{margin-top:20px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;min-height:100px}
</style>
</head>
<body>
<h2>متن خود را وارد کنید</h2>
<textarea id="inputText"></textarea><br>
<button onclick="sendText()">پردازش</button>
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
</html>
"""

# --- مسیرها ---
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

class TextInput(BaseModel):
    text: str

@app.post("/api/process")
async def process_text(input: TextInput):
    result = re.sub(r'\s+', ' ', input.text).strip()
    return {"success": True, "text": result}

# --- هندلر Vercel ---
handler = Mangum(app)
