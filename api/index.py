from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re

# --- ایمپورت کتابخانه‌های غلط‌یاب (با مدیریت خطا برای جلوگیری از کرش) ---
try:
    from shekar import SpellChecker as ShekarSpellChecker
    shekar_checker = ShekarSpellChecker()
    SHEKAR_AVAILABLE = True
except ImportError:
    SHEKAR_AVAILABLE = False

try:
    from spellchecker import SpellChecker as PySpellChecker
    arabic_checker = PySpellChecker(language='ar')
    english_checker = PySpellChecker(language='en')
    PYSPELL_AVAILABLE = True
except ImportError:
    PYSPELL_AVAILABLE = False

try:
    from zemberek import TurkishSpellChecker, TurkishMorphology
    morphology = TurkishMorphology.create_with_defaults()
    turkish_checker = TurkishSpellChecker(morphology)
    ZEMBEREK_AVAILABLE = True
except Exception:
    ZEMBEREK_AVAILABLE = False

app = FastAPI()

class TextInput(BaseModel):
    text: str

HTML_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>غلط‌یاب هوشمند چندزبانه</title>
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
<h2>متن خود را وارد کنید (فارسی، انگلیسی، عربی یا ترکی)</h2>
<textarea id="inputText" placeholder="متن خود را اینجا بنویسید..."></textarea>
<br>
<button onclick="sendText()">پردازش و اصلاح متن</button>
<h3>خروجی اصلاح‌شده:</h3>
<div id="output"></div>
<script>
async function sendText(){
  var t=document.getElementById('inputText').value;
  var o=document.getElementById('output');
  o.textContent='در حال پردازش و اصلاح...';
  try{
    var r=await fetch('/api/process',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
    var d=await r.json();
    o.textContent=d.success?d.text:'خطا: '+(d.error||'ناشناخته');
  }catch(e){o.textContent='خطای شبکه: '+e.message}
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

@app.post("/api/process")
async def process_text(input: TextInput):
    try:
        text = input.text
        # تشخیص زبان ساده بر اساس کاراکترهای یونیکد
        lang = detect_language(text)
        corrected_text = text

        if lang == 'fa' and SHEKAR_AVAILABLE:
            corrected_text = shekar_checker(text)
        elif lang == 'ar' and PYSPELL_AVAILABLE:
            corrected_text = correct_with_pyspell(text, arabic_checker)
        elif lang == 'tr' and ZEMBEREK_AVAILABLE:
            corrected_text = correct_with_zemberek(text, turkish_checker)
        elif lang == 'en' and PYSPELL_AVAILABLE:
            corrected_text = correct_with_pyspell(text, english_checker)

        # نرمال‌سازی نهایی فاصله‌ها
        corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()
        return {"success": True, "text": corrected_text, "lang": lang}
    except Exception as e:
        return {"success": False, "error": str(e)}

def detect_language(text: str) -> str:
    """تشخیص زبان بر اساس محدوده‌های یونیکد"""
    if re.search(r'[\u0600-\u06FF]', text):  # محدوده فارسی/عربی
        if re.search(r'[پچژگ]', text) or re.search(r'[ک]', text):  # کاراکترهای خاص فارسی
            return 'fa'
        return 'ar'
    if re.search(r'[çğıöşüÇĞİÖŞÜ]', text):  # کاراکترهای خاص ترکی
        return 'tr'
    return 'en'

def correct_with_pyspell(text: str, checker) -> str:
    """اصلاح کلمه‌به‌کلمه با pyspellchecker"""
    words = text.split()
    corrected = []
    for word in words:
        # فقط کلمات الفبایی را بررسی کن
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word and clean_word in checker:
            corrected.append(word)
        elif clean_word:
            correction = checker.correction(clean_word)
            if correction:
                corrected.append(word.replace(clean_word, correction))
            else:
                corrected.append(word)
        else:
            corrected.append(word)
    return ' '.join(corrected)

def correct_with_zemberek(text: str, checker) -> str:
    """اصلاح با zemberek (اگر پیاده‌سازی پایتون از این متد پشتیبانی کند)"""
    # بسته به API کتابخانه، ممکن است نیاز به تغییر داشته باشد
    try:
        words = text.split()
        corrected = [checker.normalize(word) if checker.check(word) else word for word in words]
        return ' '.join(corrected)
    except Exception:
        return text

handler = Mangum(app)
