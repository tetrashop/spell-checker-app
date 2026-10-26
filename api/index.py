from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ایمپورت کتابخانه‌ها با مدیریت خطا ---
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # برای نتایج پایدار
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available.")

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

app = FastAPI()

# --- مدل داده ورودی ---
class TextInput(BaseModel):
    text: str
    language: str = "auto"  # "auto", "fa", "en", "ar", "tr"

# --- صفحه HTML ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>غلط‌یاب هوشمند چندزبانه</title>
<style>
    body { font-family: Tahoma, Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: #f0f2f5; color: #333; }
    .container { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 30px; }
    h2 { text-align: center; color: #1a73e8; margin-bottom: 20px; }
    label { display: block; margin-bottom: 8px; font-weight: bold; }
    select, textarea, button { width: 100%; box-sizing: border-box; }
    select, textarea { padding: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 15px; margin-bottom: 15px; font-family: inherit; }
    textarea { height: 250px; resize: vertical; direction: auto; }
    button { padding: 14px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
    button:hover { background: #1557b0; }
    button:disabled { background: #a0c3ff; cursor: not-allowed; }
    .output-header { display: flex; justify-content: space-between; align-items: center; margin-top: 25px; margin-bottom: 10px; }
    .output-header h3 { margin: 0; }
    .badge { background: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; }
    #output { background: #fafafa; border: 1px solid #ddd; border-radius: 8px; padding: 15px; min-height: 150px; white-space: pre-wrap; direction: auto; font-size: 15px; line-height: 1.6; }
    .status { margin-top: 10px; font-size: 14px; color: #666; text-align: center; }
</style>
</head>
<body>
<div class="container">
    <h2>غلط‌یاب و نرمال‌ساز هوشمند</h2>
    <label for="languageSelect">زبان متن:</label>
    <select id="languageSelect">
        <option value="auto" selected>تشخیص خودکار</option>
        <option value="fa">فارسی</option>
        <option value="en">انگلیسی</option>
        <option value="ar">عربی</option>
        <option value="tr">ترکی استانبولی</option>
    </select>
    <label for="inputText">متن خود را وارد کنید:</label>
    <textarea id="inputText" placeholder="متن خود را اینجا بنویسید..."></textarea>
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
        const text = document.getElementById('inputText').value.trim();
        const lang = document.getElementById('languageSelect').value;
        const outputDiv = document.getElementById('output');
        const statusDiv = document.getElementById('status');
        const btn = document.getElementById('processBtn');
        const langBadge = document.getElementById('langBadge');

        if (!text) {
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
                    langBadge.textContent = 'زبان: ' + data.detected_language.toUpperCase();
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
        original_text = input.text
        if not original_text.strip():
            return {"success": False, "error": "متن ورودی خالی است."}

        # 1. تشخیص زبان
        detected_lang = input.language
        if detected_lang == "auto" and LANGDETECT_AVAILABLE:
            try:
                detected_lang = detect(original_text)
                # نگاشت زبان‌های تشخیص داده شده به کدهای استاندارد
                lang_map = {'fa': 'fa', 'en': 'en', 'ar': 'ar', 'tr': 'tr'}
                detected_lang = lang_map.get(detected_lang, 'en')
            except Exception:
                detected_lang = 'en'  # پیش‌فرض

        # 2. نرمال‌سازی و اصلاح بر اساس زبان
        corrected_text = original_text

        if detected_lang == 'fa':
            if HAZM_AVAILABLE:
                corrected_text = hazm_normalizer.normalize(corrected_text)
            if PYSPELL_AVAILABLE:
                corrected_text = correct_with_pyspell(corrected_text, 'fa')
        elif detected_lang == 'ar':
            if PYARABIC_AVAILABLE:
                # نرمال‌سازی همزه و حذف اعراب
                corrected_text = araby.normalize_hamza(corrected_text)
                corrected_text = araby.strip_tashkeel(corrected_text)
            if PYSPELL_AVAILABLE:
                corrected_text = correct_with_pyspell(corrected_text, 'ar')
        elif detected_lang == 'tr':
            if ZEMBEREK_AVAILABLE:
                corrected_text = correct_with_zemberek(corrected_text)
        else:  # en
            if PYSPELL_AVAILABLE:
                corrected_text = correct_with_pyspell(corrected_text, 'en')

        # 3. نرمال‌سازی نهایی فاصله‌ها
        corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()

        return {
            "success": True,
            "text": corrected_text,
            "detected_language": detected_lang if input.language == "auto" else input.language
        }
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return {"success": False, "error": str(e)}

def correct_with_pyspell(text: str, lang_code: str) -> str:
    """اصلاح کلمه‌به‌کلمه با pyspellchecker"""
    try:
        checker = SpellChecker(language=lang_code)
    except ValueError:
        return text  # اگر زبان پشتیبانی نشود، متن بدون تغییر برگردانده می‌شود

    words = text.split()
    corrected_words = []
    for word in words:
        # فقط کلمات الفبایی را بررسی کن (حذف علائم نگارشی)
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word and clean_word.lower() in checker:
            corrected_words.append(word)
        elif clean_word:
            correction = checker.correction(clean_word)
            if correction:
                # حفظ حروف بزرگ/کوچک اولیه در انگلیسی
                if lang_code == 'en' and clean_word[0].isupper():
                    correction = correction.capitalize()
                corrected_words.append(word.replace(clean_word, correction))
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)
    return ' '.join(corrected_words)

def correct_with_zemberek(text: str) -> str:
    """اصلاح با zemberek-python"""
    if not ZEMBEREK_AVAILABLE:
        return text
    try:
        words = text.split()
        corrected_words = []
        for word in words:
            clean_word = re.sub(r'[^\w\s]', '', word)
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
