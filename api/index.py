from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

# --- ایمپورت کتابخانه‌ها ---
from spellchecker import SpellChecker
from pyarabic import araby
from hazm_normalizer import Normalizer as HazmNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- مقداردهی اولیه ---
hazm_norm = HazmNormalizer()
en_checker = SpellChecker(language='en')
ar_checker = SpellChecker(language='ar')

app = FastAPI()

class TextInput(BaseModel):
    text: str
    language: str = "auto"

# --- رابط کاربری HTML (مدرن و حرفه‌ای) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>سیستم جامع غلط‌یاب و نرمال‌ساز</title>
<style>
    :root { --primary: #1a73e8; --primary-hover: #1557b0; --bg: #f0f2f5; --text: #333; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 20px auto; padding: 15px; background: var(--bg); color: var(--text); }
    .container { background: #fff; border-radius: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); padding: 30px; }
    h2 { text-align: center; color: var(--primary); margin-bottom: 25px; font-weight: 600; }
    label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 15px; }
    select, textarea { width: 100%; box-sizing: border-box; padding: 14px; border: 1px solid #dadce0; border-radius: 10px; font-size: 15px; margin-bottom: 20px; font-family: inherit; transition: border 0.3s; }
    select:focus, textarea:focus { border-color: var(--primary); outline: none; }
    textarea { height: 220px; resize: vertical; direction: auto; line-height: 1.8; background-color: #fafafa; }
    .btn-group { display: flex; gap: 12px; margin-bottom: 20px; }
    button { padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; transition: all 0.3s; font-weight: bold; flex: 1; display: flex; justify-content: center; align-items: center; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-primary:disabled { background: #a0c3ff; cursor: not-allowed; transform: none; }
    .btn-danger { background: #ea4335; color: white; }
    .btn-danger:hover { background: #c5221f; }
    .btn-success { background: #34a853; color: white; display: none; }
    .btn-success:hover { background: #2b8a44; }
    .output-container { background: #f8f9fa; border: 1px solid #e8eaed; border-radius: 10px; padding: 20px; min-height: 150px; white-space: pre-wrap; direction: auto; font-size: 16px; line-height: 1.8; color: #202124; }
    .header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .badge { background: #e8f0fe; color: var(--primary); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; display: none; }
    .status { margin-top: 15px; font-size: 14px; color: #5f6368; text-align: center; font-weight: 500; }
</style>
</head>
<body>
<div class="container">
    <h2>سیستم جامع غلط‌یاب و نرمال‌ساز</h2>
    
    <label for="languageSelect">حالت پردازش:</label>
    <select id="languageSelect">
        <option value="auto" selected>تشخیص خودکار (پیشنهادی)</option>
        <option value="fa">فقط فارسی</option>
        <option value="en">فقط انگلیسی</option>
        <option value="ar">فقط عربی</option>
    </select>
    
    <label for="inputText">متن ورودی:</label>
    <textarea id="inputText" placeholder="متن خود را اینجا بنویسید یا جای‌گذاری کنید..."></textarea>
    
    <div class="btn-group">
        <button id="processBtn" class="btn-primary" onclick="processText()">پردازش و اصلاح</button>
        <button class="btn-danger" onclick="clearAll()">پاک کردن</button>
    </div>
    
    <div class="header-flex">
        <label style="margin:0;">خروجی اصلاح‌شده:</label>
        <span id="langBadge" class="badge"></span>
    </div>
    
    <div id="output" class="output-container"></div>
    
    <div class="btn-group" style="margin-top: 20px;">
        <button id="copyBtn" class="btn-success" onclick="copyOutput()">کپی متن در کلیپ‌بورد</button>
    </div>
    
    <div id="status" class="status"></div>
</div>

<script>
    async function processText() {
        const text = document.getElementById('inputText').value;
        const lang = document.getElementById('languageSelect').value;
        const outputDiv = document.getElementById('output');
        const statusDiv = document.getElementById('status');
        const btn = document.getElementById('processBtn');
        const copyBtn = document.getElementById('copyBtn');
        const langBadge = document.getElementById('langBadge');

        if (!text.trim()) {
            alert('لطفاً متنی وارد کنید.');
            return;
        }

        outputDiv.textContent = '';
        langBadge.style.display = 'none';
        copyBtn.style.display = 'none';
        statusDiv.textContent = 'در حال پردازش و اعمال قوانین زبانی...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, language: lang })
            });
            const data = await response.json();

            if (data.success) {
                outputDiv.textContent = data.text;
                if (data.detected_language) {
                    langBadge.textContent = 'حالت: ' + data.detected_language;
                    langBadge.style.display = 'inline-block';
                }
                statusDiv.textContent = 'پردازش با موفقیت انجام شد.';
                copyBtn.style.display = 'flex';
            } else {
                outputDiv.textContent = 'خطا در پردازش: ' + (data.error || 'ناشناخته');
                statusDiv.textContent = '';
            }
        } catch (err) {
            outputDiv.textContent = 'خطای شبکه: ' + err.message;
            statusDiv.textContent = '';
        } finally {
            btn.disabled = false;
        }
    }

    function copyOutput() {
        const outputText = document.getElementById('output').textContent;
        navigator.clipboard.writeText(outputText).then(() => {
            const copyBtn = document.getElementById('copyBtn');
            copyBtn.textContent = 'کپی شد! ✔';
            setTimeout(() => { copyBtn.textContent = 'کپی متن در کلیپ‌بورد'; }, 2000);
        });
    }

    function clearAll() {
        document.getElementById('inputText').value = '';
        document.getElementById('output').textContent = '';
        document.getElementById('status').textContent = '';
        document.getElementById('langBadge').style.display = 'none';
        document.getElementById('copyBtn').style.display = 'none';
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

@app.post("/api/process")
async def process_text_endpoint(input: TextInput):
    try:
        text = input.text
        if not text.strip():
            return {"success": False, "error": "متن ورودی خالی است."}

        if input.language == "auto":
            corrected_text = process_mixed_text(text)
            detected = "ترکیبی (چندزبانه)"
        else:
            corrected_text = process_single_language(text, input.language)
            detected = input.language.upper()

        return {
            "success": True,
            "text": corrected_text,
            "detected_language": detected
        }
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# --- توابع کمکی هوشمند ---

def fix_repeated_chars(text: str, is_persian_arabic: bool) -> str:
    """
    حذف هوشمند حروف تکراری. 
    اگر ۳ بار یا بیشتر تکرار شده باشد (مثل سسسلام) آن را به ۱ حرف کاهش می‌دهد.
    """
    if is_persian_arabic:
        # محدوده یونیکد فارسی و عربی
        return re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', text)
    else:
        # حروف انگلیسی و ترکی
        return re.sub(r'([a-zA-ZçğıöşüÇĞİÖŞÜ])\1{2,}', r'\1', text)

def correct_with_pyspell(text: str, checker) -> str:
    """غلط‌یابی کلمه به کلمه با حفظ علائم نگارشی و حروف بزرگ"""
    words = text.split()
    corrected_words = []
    for word in words:
        # جداسازی علائم نگارشی از ابتدا و انتهای کلمه
        match = re.match(r'^([^\w\u0600-\u06FF]*)([\w\u0600-\u06FF]+)([^\w\u0600-\u06FF]*)$', word)
        if match:
            prefix, clean_word, suffix = match.groups()
            # اگر کلمه در دیکشنری بود، دست نزن
            if clean_word.lower() in checker:
                corrected_words.append(word)
            else:
                correction = checker.correction(clean_word.lower())
                if correction:
                    # حفظ حرف بزرگ اول در انگلیسی
                    if clean_word[0].isupper():
                        correction = correction.capitalize()
                    corrected_words.append(f"{prefix}{correction}{suffix}")
                else:
                    corrected_words.append(word)
        else:
            corrected_words.append(word)
    return ' '.join(corrected_words)

def process_mixed_text(text: str) -> str:
    """پردازش خط به خط متن‌های ترکیبی با تشخیص دقیق زبان"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
            
        # تشخیص زبان بر اساس اسکریپت (Script Analysis)
        has_persian = bool(re.search(r'[پچژگ]', line))
        has_arabic = bool(re.search(r'[\u0600-\u06FF]', line))
        has_turkish = bool(re.search(r'[çğıöşüÇĞİÖŞÜ]', line))
        has_english = bool(re.search(r'[a-zA-Z]', line))

        if has_persian or (has_arabic and not has_persian and not has_english):
            # خط فارسی است (وجود حروف خاص فارسی، یا فقط حروف مشترک با عربی بدون حروف لاتین)
            if has_persian:
                line = fix_repeated_chars(line, is_persian_arabic=True)
                line = hazm_norm.normalize(line) # اصلاح نیم‌فاصله
            else:
                # ممکن است عربی باشد
                line = fix_repeated_chars(line, is_persian_arabic=True)
                line = araby.normalize_hamza(line)
                line = araby.strip_tashkeel(line)
                line = correct_with_pyspell(line, ar_checker)
                
        elif has_english and not has_turkish:
            # خط انگلیسی است
            line = fix_repeated_chars(line, is_persian_arabic=False)
            line = correct_with_pyspell(line, en_checker)
            
        elif has_turkish:
            # خط ترکی است
            line = fix_repeated_chars(line, is_persian_arabic=False)
            # برای ترکی فعلاً فقط حروف تکراری را اصلاح می‌کنیم چون Zemberek روی Vercel سنگین است
            
        processed_lines.append(line)
        
    return '\n'.join(processed_lines)

def process_single_language(text: str, lang: str) -> str:
    """پردازش متن وقتی کاربر زبان را دستی انتخاب می‌کند"""
    if lang == 'fa':
        text = fix_repeated_chars(text, is_persian_arabic=True)
        text = hazm_norm.normalize(text)
    elif lang == 'ar':
        text = fix_repeated_chars(text, is_persian_arabic=True)
        text = araby.normalize_hamza(text)
        text = araby.strip_tashkeel(text)
        text = correct_with_pyspell(text, ar_checker)
    elif lang == 'en':
        text = fix_repeated_chars(text, is_persian_arabic=False)
        text = correct_with_pyspell(text, en_checker)
    return text

# --- هندلر Vercel ---
handler = Mangum(app)
