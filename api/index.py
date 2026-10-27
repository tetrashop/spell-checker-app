from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ایمپورت کتابخانه‌ها با مدیریت خطا ---
try:
    from spellchecker import SpellChecker
    en_checker = SpellChecker(language='en')
    ar_checker = SpellChecker(language='ar')
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

# --- صفحه HTML ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>غلط‌یاب جامع و پیشرفته</title>
<style>
    :root { --primary: #1a73e8; --primary-hover: #1557b0; --bg: #f0f2f5; --text: #333; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 900px; margin: 20px auto; padding: 15px; background: var(--bg); color: var(--text); }
    .container { background: #fff; border-radius: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); padding: 30px; }
    h2 { text-align: center; color: var(--primary); margin-bottom: 25px; }
    label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 15px; }
    select, textarea { width: 100%; box-sizing: border-box; padding: 14px; border: 1px solid #dadce0; border-radius: 10px; font-size: 15px; margin-bottom: 20px; font-family: inherit; }
    textarea { height: 220px; resize: vertical; direction: auto; line-height: 1.8; background-color: #fafafa; }
    .btn-group { display: flex; gap: 12px; margin-bottom: 20px; }
    button { padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; transition: all 0.3s; font-weight: bold; flex: 1; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-primary:disabled { background: #a0c3ff; cursor: not-allowed; }
    .btn-danger { background: #ea4335; color: white; }
    .btn-success { background: #34a853; color: white; display: none; }
    .output-container { background: #f8f9fa; border: 1px solid #e8eaed; border-radius: 10px; padding: 20px; min-height: 150px; white-space: pre-wrap; direction: auto; font-size: 16px; line-height: 1.8; }
    .header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .badge { background: #e8f0fe; color: var(--primary); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; display: none; }
    .status { margin-top: 15px; font-size: 14px; color: #5f6368; text-align: center; }
</style>
</head>
<body>
<div class="container">
    <h2>غلط‌یاب جامع و پیشرفته</h2>
    <label for="languageSelect">حالت پردازش:</label>
    <select id="languageSelect">
        <option value="auto" selected>تشخیص خودکار (پیشنهادی)</option>
        <option value="fa">فقط فارسی</option>
        <option value="en">فقط انگلیسی</option>
        <option value="ar">فقط عربی</option>
        <option value="tr">فقط ترکی</option>
    </select>
    <label for="inputText">متن ورودی:</label>
    <textarea id="inputText" placeholder="متن خود را اینجا بنویسید..."></textarea>
    
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
                copyBtn.style.display = 'block';
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

# --- توابع تشخیص زبان ---
def detect_line_language(line: str) -> str:
    if re.search(r'[\u0600-\u06FF]', line):
        if re.search(r'[پچژگ]', line): return 'fa'
        persian_words = ['من', 'تو', 'او', 'ما', 'شما', 'است', 'که', 'را', 'با', 'برای', 'این', 'آن', 'دوست', 'سلام', 'کتاب', 'می', 'های', 'بود', 'شد', 'کرد', 'خواهم', 'بر', 'در', 'از', 'اما']
        arabic_words = ['في', 'على', 'إلى', 'من', 'هذا', 'هذه', 'الذي', 'التي', 'العالم', 'بك', 'عن', 'مع', 'لا', 'ما', 'هو', 'هي', 'انا', 'انت', 'يجب', 'أن', 'غدا']
        p_matches = sum(1 for w in persian_words if w in line.split())
        a_matches = sum(1 for w in arabic_words if w in line.split())
        if p_matches >= a_matches: return 'fa'
        else: return 'ar'
    if re.search(r'[a-zA-Z]', line):
        if re.search(r'[çğıöşüÇĞİÖŞÜ]', line): return 'tr'
        tr_words = ['bir', 've', 'bu', 'için', 'dünya', 'güzel', 'merhaba', 'test', 'evet', 'hayır', 'değil', 'ama', 'ben', 'çok', 'gün']
        en_words = ['the', 'is', 'this', 'that', 'world', 'hello', 'test', 'of', 'and', 'in', 'to', 'it', 'you', 'for', 'with', 'have', 'a', 'i', 'he']
        t_matches = sum(1 for w in tr_words if w in line.lower().split())
        e_matches = sum(1 for w in en_words if w in line.lower().split())
        if t_matches > e_matches: return 'tr'
        else: return 'en'
    return 'en'

# --- توابع اصلاح‌گر ---
def smart_correct_english(text: str) -> str:
    if not PYSPELL_AVAILABLE: return text
    words = text.split()
    corrected = []
    for word in words:
        match = re.match(r'^([^\w]*)([a-zA-Z]+)([^\w]*)$', word)
        if not match:
            corrected.append(word)
            continue
        prefix, clean, suffix = match.groups()
        clean_lower = clean.lower()

        if clean_lower in en_checker:
            corrected.append(word)
            continue

        reduced = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', clean)
        if reduced.lower() in en_checker:
            if clean[0].isupper(): reduced = reduced.capitalize()
            corrected.append(f"{prefix}{reduced}{suffix}")
            continue

        best_word = None
        max_freq = 0
        for i in range(len(clean_lower) - 1):
            if clean_lower[i] != clean_lower[i+1]:
                swapped = clean_lower[:i] + clean_lower[i+1] + clean_lower[i] + clean_lower[i+2:]
                if swapped in en_checker:
                    freq = en_checker.word_frequency[swapped]
                    if freq > max_freq:
                        max_freq = freq
                        best_word = swapped
        
        if best_word:
            if clean[0].isupper(): best_word = best_word.capitalize()
            corrected.append(f"{prefix}{best_word}{suffix}")
            continue

        if len(clean_lower) > 3:
            corr = en_checker.correction(clean_lower)
            if corr:
                if clean[0].isupper(): corr = corr.capitalize()
                corrected.append(f"{prefix}{corr}{suffix}")
                continue

        corrected.append(word)
    return ' '.join(corrected)

def smart_correct_arabic(text: str) -> str:
    if PYARABIC_AVAILABLE:
        text = araby.normalize_hamza(text)
        text = araby.strip_tashkeel(text)
        
    text = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', text)
    
    if PYSPELL_AVAILABLE:
        words = text.split()
        corrected = []
        for word in words:
            match = re.match(r'^([^\w\u0600-\u06FF]*)([\w\u0600-\u06FF]+)([^\w\u0600-\u06FF]*)$', word)
            if match:
                prefix, clean, suffix = match.groups()
                # باگ‌گیری: کلمات کوتاه‌تر از ۴ حرف را دست نزن (مثل من، أن، إلى، على)
                if clean in ar_checker or len(clean) <= 3:
                    corrected.append(word)
                else:
                    corr = ar_checker.correction(clean)
                    if corr:
                        corrected.append(f"{prefix}{corr}{suffix}")
                    else:
                        corrected.append(word)
            else:
                corrected.append(word)
        return ' '.join(corrected)
    return text

def smart_correct_persian(text: str) -> str:
    text = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', text)
    
    common_typos = {
        'ششما': 'شما', 'ددوست': 'دوست', 'ممی': 'می', 'خخواهم': 'خواهم',
        'کتایب': 'کتاب', 'کتااب': 'کتاب', 'سسلاام': 'سلام', 'سسسلام': 'سلام',
        'ببا': 'با', 'ککه': 'که', 'اینن': 'این', 'آنن': 'آن', 'استت': 'است',
        'برر': 'بر', 'راا': 'را', 'ازز': 'از', 'درر': 'در', 'چچ': 'چ',
        'ههر': 'هر', 'ییک': 'یک', 'دده': 'ده', 'ددر': 'در',
        'میخواهم': 'می‌خواهم', 'کتابخوان': 'کتاب‌خوان', 'کتابها': 'کتاب‌ها',
        'میشود': 'می‌شود', 'نمیشود': 'نمی‌شود', 'نمیتوانم': 'نمی‌توانم'
    }
    
    for k, v in common_typos.items():
        text = text.replace(k, v)
        
    if HAZM_AVAILABLE:
        text = hazm_norm.normalize(text)
        
    return text

def smart_correct_turkish(text: str) -> str:
    text = re.sub(r'([a-zA-ZçğıöşüÇĞİÖŞÜ])\1{2,}', r'\1\1', text)
    
    common_typos = {
        'Merhabba': 'Merhaba', 'güzeel': 'güzel', 'dünyaa': 'dünya',
        'birr': 'bir', 'vee': 've', 'buu': 'bu', 'içinn': 'için',
        'değill': 'değil', 'evett': 'evet', 'hayırr': 'hayır',
        'guzel': 'güzel', 'dun': 'dün', 'uyuyamadim': 'uyuyamadım', 
        'bugun': 'bugün', 'yaptim': 'yaptım', 'gelicem': 'geleceğim'
    }
    
    # استفاده از regex برای جایگزینی دقیق کلمات
    for k, v in common_typos.items():
        text = re.sub(r'\b' + k + r'\b', v, text, flags=re.IGNORECASE)
        
    return text

def process_mixed_text(text: str) -> str:
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
        lang = detect_line_language(line)
        if lang == 'fa': line = smart_correct_persian(line)
        elif lang == 'ar': line = smart_correct_arabic(line)
        elif lang == 'en': line = smart_correct_english(line)
        elif lang == 'tr': line = smart_correct_turkish(line)
        processed_lines.append(line)
    return '\n'.join(processed_lines)

def process_single_language(text: str, lang: str) -> str:
    if lang == 'fa': return smart_correct_persian(text)
    elif lang == 'ar': return smart_correct_arabic(text)
    elif lang == 'en': return smart_correct_english(text)
    elif lang == 'tr': return smart_correct_turkish(text)
    return text

handler = Mangum(app)
