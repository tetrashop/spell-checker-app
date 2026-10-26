from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ایمپورت کتابخانه‌ها با مدیریت خطای کامل (Anti-Crash) ---
try:
    from spellchecker import SpellChecker
    PYSPELL_AVAILABLE = True
except ImportError:
    PYSPELL_AVAILABLE = False
    logger.warning("pyspellchecker not available.")

try:
    from pyarabic import araby
    PYARABIC_AVAILABLE = True
except ImportError:
    PYARABIC_AVAILABLE = False
    logger.warning("PyArabic not available.")

try:
    from hazm_normalizer import Normalizer as HazmNormalizer
    hazm_normalizer = HazmNormalizer()
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False
    logger.warning("hazm-normalizer not available.")

try:
    from zemberek import TurkishSpellChecker, TurkishMorphology
    morphology = TurkishMorphology.create_with_defaults()
    turkish_checker = TurkishSpellChecker(morphology)
    ZEMBEREK_AVAILABLE = True
except Exception as e:
    ZEMBEREK_AVAILABLE = False
    logger.warning(f"Zemberek not available: {e}")

# --- تعریف دیکشنری‌های غلط‌یاب ---
# ما فقط دیکشنری‌هایی را می‌سازیم که کتابخانه‌شان موجود است تا از کرش جلوگیری شود
ar_checker = SpellChecker(language='ar') if PYSPELL_AVAILABLE else None
en_checker = SpellChecker(language='en') if PYSPELL_AVAILABLE else None

app = FastAPI()

class TextInput(BaseModel):
    text: str
    language: str = "auto"

# --- صفحه HTML با طراحی ریسپانسیو ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>غلط‌یاب و نرمال‌ساز هوشمند</title>
<style>
    body { font-family: Tahoma, Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 15px; background: #f0f2f5; color: #333; }
    .container { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 25px; }
    h2 { text-align: center; color: #1a73e8; margin-bottom: 20px; }
    label { display: block; margin-bottom: 8px; font-weight: bold; }
    select, textarea, button { width: 100%; box-sizing: border-box; }
    select, textarea { padding: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 15px; margin-bottom: 15px; font-family: inherit; }
    textarea { height: 250px; resize: vertical; direction: auto; }
    button { padding: 14px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background 0.3s; font-weight: bold; }
    button:hover { background: #1557b0; }
    button:disabled { background: #a0c3ff; cursor: not-allowed; }
    .output-header { display: flex; justify-content: space-between; align-items: center; margin-top: 25px; margin-bottom: 10px; }
    .output-header h3 { margin: 0; }
    .badge { background: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; }
    #output { background: #fafafa; border: 1px solid #ddd; border-radius: 8px; padding: 15px; min-height: 150px; white-space: pre-wrap; direction: auto; font-size: 15px; line-height: 1.8; }
    .status { margin-top: 10px; font-size: 14px; color: #666; text-align: center; }
</style>
</head>
<body>
<div class="container">
    <h2>غلط‌یاب و نرمال‌ساز هوشمند</h2>
    <label for="languageSelect">حالت پردازش:</label>
    <select id="languageSelect">
        <option value="auto" selected>تشخیص خودکار (مناسب متن‌های ترکیبی)</option>
        <option value="fa">فقط فارسی</option>
        <option value="en">فقط انگلیسی</option>
        <option value="ar">فقط عربی</option>
        <option value="tr">فقط ترکی استانبولی</option>
    </select>
    <label for="inputText">متن خود را وارد کنید:</label>
    <textarea id="inputText" placeholder="متن فارسی، انگلیسی، عربی یا ترکی را اینجا بنویسید..."></textarea>
    <button id="processBtn" onclick="sendText()">پردازش و اصلاح متن</button>
    
    <div class="output-header">
        <h3>خروجی اصلاح‌شده:</h3>
        <span id="langBadge" class="badge" style="display:none;"></span>
    </div>
    <div id="output"></div>
    <div id="status" class="status"></div>
</div>
<script>
    async function sendText() {
        const text = document.getElementById('inputText').value;
        const lang = document.getElementById('languageSelect').value;
        const outputDiv = document.getElementById('output');
        const statusDiv = document.getElementById('status');
        const btn = document.getElementById('processBtn');
        const langBadge = document.getElementById('langBadge');

        if (!text.trim()) {
            alert('لطفاً متنی وارد کنید.');
            return;
        }

        outputDiv.textContent = '';
        langBadge.style.display = 'none';
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
            } else {
                outputDiv.textContent = 'خطا: ' + (data.error || 'ناشناخته');
                statusDiv.textContent = '';
            }
        } catch (err) {
            outputDiv.textContent = 'خطای شبکه: ' + err.message;
            statusDiv.textContent = '';
        } finally {
            btn.disabled = false;
        }
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

@app.post("/api/process")
async def process_text(input: TextInput):
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

        # تمیزکاری نهایی: حذف فاصله‌های اضافی اما حفظ خطوط جدید (Enter)
        corrected_text = re.sub(r'[ \t]+', ' ', corrected_text)

        return {
            "success": True,
            "text": corrected_text,
            "detected_language": detected
        }
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return {"success": False, "error": str(e)}

# --- منطق پردازش ترکیبی (خط به خط) ---
def process_mixed_text(text: str) -> str:
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
        
        # نرمال‌سازی اولیه (اعمال روی کل خط)
        if HAZM_AVAILABLE:
            line = hazm_normalizer.normalize(line)
        if PYARABIC_AVAILABLE:
            line = araby.normalize_hamza(line)
            line = araby.strip_tashkeel(line)

        # تشخیص زبان خط بر اساس اسکریپت (Script)
        if re.search(r'[\u0600-\u06FF]', line):
            # دارای کاراکترهای فارسی/عربی
            if re.search(r'[پچژگ]', line):
                # خط فارسی است (نرمال‌سازی hazm کافی است)
                pass 
            else:
                # خط عربی است
                if PYSPELL_AVAILABLE:
                    line = correct_with_pyspell(line, ar_checker)
        elif re.search(r'[a-zA-Z]', line):
            # دارای کاراکترهای لاتین
            if re.search(r'[çğıöşüÇĞİÖŞÜ]', line):
                # خط ترکی است
                if ZEMBEREK_AVAILABLE:
                    line = correct_with_zemberek(line)
            else:
                # خط انگلیسی است
                if PYSPELL_AVAILABLE:
                    line = correct_with_pyspell(line, en_checker)
                    
        processed_lines.append(line)
        
    return '\n'.join(processed_lines)

# --- منطق پردازش تک‌زبانه (وقتی کاربر زبان را دستی انتخاب می‌کند) ---
def process_single_language(text: str, lang: str) -> str:
    if lang == 'fa' and HAZM_AVAILABLE:
        return hazm_normalizer.normalize(text)
    elif lang == 'ar':
        if PYARABIC_AVAILABLE:
            text = araby.normalize_hamza(text)
            text = araby.strip_tashkeel(text)
        if PYSPELL_AVAILABLE:
            return correct_with_pyspell(text, ar_checker)
    elif lang == 'tr' and ZEMBEREK_AVAILABLE:
        return correct_with_zemberek(text)
    elif lang == 'en' and PYSPELL_AVAILABLE:
        return correct_with_pyspell(text, en_checker)
    return text

def correct_with_pyspell(text: str, checker) -> str:
    if not checker:
        return text
    words = text.split()
    corrected_words = []
    for word in words:
        clean_word = re.sub(r'[^\w\s\u0600-\u06FF]', '', word)
        if clean_word and clean_word.lower() in checker:
            corrected_words.append(word)
        elif clean_word:
            correction = checker.correction(clean_word)
            if correction:
                if clean_word[0].isupper():
                    correction = correction.capitalize()
                corrected_words.append(word.replace(clean_word, correction))
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)
    return ' '.join(corrected_words)

def correct_with_zemberek(text: str) -> str:
    if not ZEMBEREK_AVAILABLE:
        return text
    try:
        words = text.split()
        corrected_words = []
        for word in words:
            clean_word = re.sub(r'[^\w\sçğıöşüÇĞİÖŞÜ]', '', word)
            if not clean_word:
                corrected_words.append(word)
                continue
            if turkish_checker.check(clean_word):
                corrected_words.append(word)
            else:
                suggestions = turkish_checker.suggestions(clean_word)
                if suggestions:
                    corrected_words.append(word.replace(clean_word, suggestions[0]))
                else:
                    corrected_words.append(word)
        return ' '.join(corrected_words)
    except Exception as e:
        logger.error(f"Zemberek error: {e}")
        return text

# --- هندلر Vercel ---
handler = Mangum(app)
