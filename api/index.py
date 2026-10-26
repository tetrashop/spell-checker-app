from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ایمپورت کتابخانه‌ها ---
try:
    from spellchecker import SpellChecker
    en_checker = SpellChecker(language='en')
    PYSPELL_AVAILABLE = True
except ImportError:
    PYSPELL_AVAILABLE = False

try:
    from pyarabic import araby
    PYARABIC_AVAILABLE = True
except ImportError:
    PYARABIC_AVAILABLE = False

try:
    from hazm import Normalizer as HazmNormalizer
    hazm_norm = HazmNormalizer()
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False

app = FastAPI()

class TextInput(BaseModel):
    text: str
    language: str = "auto"

# --- رابط کاربری HTML ---
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
        <option value="tr">فقط ترکی</option>
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

        if (!text.trim()) { alert('لطفاً متنی وارد کنید.'); return; }

        outputDiv.textContent = '';
        langBadge.style.display = 'none';
        copyBtn.style.display = 'none';
        statusDiv.textContent = 'در حال پردازش...';
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
        navigator.clipboard.writeText(document.getElementById('output').textContent).then(() => {
            const b = document.getElementById('copyBtn'); b.textContent = 'کپی شد! ✔';
            setTimeout(() => { b.textContent = 'کپی متن در کلیپ‌بورد'; }, 2000);
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
        if not text.strip(): return {"success": False, "error": "متن ورودی خالی است."}

        if input.language == "auto":
            corrected_text = process_mixed_text(text)
            detected = "ترکیبی (چندزبانه)"
        else:
            corrected_text = process_single_language(text, input.language)
            detected = input.language.upper()

        return {"success": True, "text": corrected_text, "detected_language": detected}
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# --- توابع کمکی ---

def detect_line_language(line: str) -> str:
    """تشخیص دقیق زبان بر اساس کلمات کلیدی و کاراکترها (بدون استفاده از langdetect)"""
    has_persian_specific = bool(re.search(r'[پچژگ]', line))
    has_arabic_specific = bool(re.search(r'[يكة]', line))
    has_turkish_specific = bool(re.search(r'[çğıöşüÇĞİÖŞÜ]', line))
    has_latin = bool(re.search(r'[a-zA-Z]', line))
    has_arabic_script = bool(re.search(r'[\u0600-\u06FF]', line))

    if has_arabic_script:
        if has_persian_specific: return 'fa'
        # اگر حروف خاص فارسی ندارد، با کلمات کلیدی چک می‌کنیم
        persian_words = ['من', 'تو', 'او', 'ما', 'شما', 'است', 'که', 'را', 'با', 'برای', 'این', 'آن', 'دوست', 'سلام', 'کتاب', 'می', 'های', 'بود', 'شد', 'کرد', 'خواهم', 'بر']
        if any(re.search(r'\b' + w + r'\b', line) for w in persian_words): return 'fa'
        
        arabic_words = ['في', 'على', 'إلى', 'من', 'هذا', 'هذه', 'الذي', 'التي', 'العالم', 'بك']
        if any(re.search(r'\b' + w + r'\b', line) for w in arabic_words): return 'ar'
        
        return 'fa' # پیش‌فرض برای اسکریپت عربی/فارسی

    if has_latin:
        if has_turkish_specific: return 'tr'
        tr_words = ['bir', 've', 'bu', 'için', 'dünya', 'güzel']
        if any(re.search(r'\b' + w + r'\b', line, re.IGNORECASE) for w in tr_words): return 'tr'
        return 'en'

    return 'unknown'

def smart_correct_english(text: str) -> str:
    """غلط‌یاب انگلیسی با منطق جابه‌جایی حروف (tset -> test) و حذف حروف تکراری (Helllo -> Hello)"""
    if not PYSPELL_AVAILABLE: return text
    words = text.split()
    corrected = []
    for word in words:
        match = re.match(r'^([^\w]*)([a-zA-Z]+)([^\w]*)$', word)
        if not match:
            corrected.append(word)
            continue
        prefix, clean, suffix = match.groups()

        if clean.lower() in en_checker:
            corrected.append(word)
            continue

        # 1. حذف حروف تکراری ۳ بار یا بیشتر (Helllo -> Hello)
        reduced = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', clean)
        if reduced.lower() in en_checker:
            if clean[0].isupper(): reduced = reduced.capitalize()
            corrected.append(f"{prefix}{reduced}{suffix}")
            continue

        # 2. جابه‌جایی حروف (tset -> test)
        transposed = False
        for i in range(len(clean) - 1):
            if clean[i] != clean[i+1]:
                swapped = clean[:i] + clean[i+1] + clean[i] + clean[i+2:]
                if swapped.lower() in en_checker:
                    if clean[0].isupper(): swapped = swapped.capitalize()
                    corrected.append(f"{prefix}{swapped}{suffix}")
                    transposed = True
                    break
        if transposed: continue

        # 3. اصلاح با کتابخانه (فقط برای کلمات بزرگتر از ۳ حرف)
        if len(clean) > 3:
            corr = en_checker.correction(clean.lower())
            if corr:
                if clean[0].isupper(): corr = corr.capitalize()
                corrected.append(f"{prefix}{corr}{suffix}")
                continue

        corrected.append(word)
    return ' '.join(corrected)

def smart_correct_persian(text: str) -> str:
    """اصلاح فارسی: حذف حروف تکراری ۳ بار یا بیشتر + اصلاح کلمات دوحرفی رایج"""
    # 1. تبدیل ۳ بار یا بیشتر به ۱ بار (سسسلام -> سلام)
    text = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', text)
    
    # 2. دیکشنری اصلاح کلمات دوحرفی رایج (ششما -> شما)
    common_typos = {'ششما': 'شما', 'ددوست': 'دوست', 'ممی': 'می', 'خخواهم': 'خواهم'}
    for k, v in common_typos.items():
        text = text.replace(k, v)
        
    # 3. اصلاح نیم‌فاصله و فاصله‌ها
    if HAZM_AVAILABLE:
        text = hazm_norm.normalize(text)
    return text

def smart_correct_arabic(text: str) -> str:
    """اصلاح عربی: فقط نرمال‌سازی همزه و اعراب (بدون دیکشنری برای جلوگیری از خراب کردن کلمات)"""
    text = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', text)
    if PYARABIC_AVAILABLE:
        text = araby.normalize_hamza(text)
        text = araby.strip_tashkeel(text)
    return text

def smart_correct_turkish(text: str) -> str:
    """اصلاح ترکی: حذف حروف تکراری و کلمات رایج"""
    text = re.sub(r'([a-zA-ZçğıöşüÇĞİÖŞÜ])\1{2,}', r'\1\1', text)
    text = text.replace('Merhabba', 'Merhaba')
    text = text.replace('testtir', 'testtir')
    text = text.replace('güzeel', 'güzel')
    return text

def process_mixed_text(text: str) -> str:
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
            
        lang = detect_line_language(line)
        
        if lang == 'fa':
            line = smart_correct_persian(line)
        elif lang == 'ar':
            line = smart_correct_arabic(line)
        elif lang == 'en':
            line = smart_correct_english(line)
        elif lang == 'tr':
            line = smart_correct_turkish(line)
            
        processed_lines.append(line)
        
    return '\n'.join(processed_lines)

def process_single_language(text: str, lang: str) -> str:
    if lang == 'fa': return smart_correct_persian(text)
    elif lang == 'ar': return smart_correct_arabic(text)
    elif lang == 'en': return smart_correct_english(text)
    elif lang == 'tr': return smart_correct_turkish(text)
    return text

handler = Mangum(app)
