from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mangum import Mangum
import re
import logging

from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # برای پایداری تشخیص زبان

from spellchecker import SpellChecker
from pyarabic import araby
from hazm_normalizer import Normalizer as HazmNormalizer

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- مقداردهی اولیه ابزارها ---
hazm_norm = HazmNormalizer()
en_checker = SpellChecker(language='en')
ar_checker = SpellChecker(language='ar')

app = FastAPI()

class TextInput(BaseModel):
    text: str
    language: str = "auto"

# --- صفحه HTML با دکمه کپی ---
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
    textarea { height: 250px; resize: vertical; direction: auto; line-height: 1.6; }
    button { padding: 14px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background 0.3s; font-weight: bold; }
    button:hover { background: #1557b0; }
    button:disabled { background: #a0c3ff; cursor: not-allowed; }
    .output-header { display: flex; justify-content: space-between; align-items: center; margin-top: 25px; margin-bottom: 10px; }
    .output-header h3 { margin: 0; }
    .badge { background: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; }
    #output { background: #fafafa; border: 1px solid #ddd; border-radius: 8px; padding: 15px; min-height: 150px; white-space: pre-wrap; direction: auto; font-size: 15px; line-height: 1.8; }
    .copy-btn { margin-top: 10px; background: #34a853; display: none; }
    .copy-btn:hover { background: #2b8a44; }
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
    </select>
    <label for="inputText">متن خود را وارد کنید:</label>
    <textarea id="inputText" placeholder="متن فارسی، انگلیسی، عربی را اینجا بنویسید..."></textarea>
    <button id="processBtn" onclick="sendText()">پردازش و اصلاح متن</button>
    
    <div class="output-header">
        <h3>خروجی اصلاح‌شده:</h3>
        <span id="langBadge" class="badge" style="display:none;"></span>
    </div>
    <div id="output"></div>
    <button id="copyBtn" class="copy-btn" onclick="copyText()">کپی متن</button>
    <div id="status" class="status"></div>
</div>
<script>
    async function sendText() {
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

    function copyText() {
        const outputText = document.getElementById('output').textContent;
        navigator.clipboard.writeText(outputText).then(() => {
            const copyBtn = document.getElementById('copyBtn');
            copyBtn.textContent = 'کپی شد! ✔';
            setTimeout(() => { copyBtn.textContent = 'کپی متن'; }, 2000);
        });
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

        return {
            "success": True,
            "text": corrected_text,
            "detected_language": detected
        }
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return {"success": False, "error": str(e)}

def remove_duplicate_chars(text: str) -> str:
    """حذف حروف تکراری ۳ بار یا بیشتر (مثل سسسسلام -> سلام یا Helllo -> Hello)"""
    return re.sub(r'([a-zA-Z\u0600-\u06FF])\1{2,}', r'\1', text)

def process_mixed_text(text: str) -> str:
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
        
        # 1. حذف حروف تکراری در کل خط
        line = remove_duplicate_chars(line)

        # 2. تشخیص زبان خط
        try:
            lang = detect(line)
        except:
            lang = 'unknown'

        # 3. اعمال قوانین بر اساس زبان
        if lang == 'fa' or re.search(r'[پچژگ]', line):
            # فارسی: اصلاح فاصله‌ها و نویسه‌ها با hazm
            line = hazm_norm.normalize(line)
        elif lang == 'ar':
            # عربی: نرمال‌سازی و غلط‌یابی
            line = araby.normalize_hamza(line)
            line = araby.strip_tashkeel(line)
            line = correct_with_pyspell(line, ar_checker)
        elif lang == 'en' or (re.search(r'[a-zA-Z]', line) and not re.search(r'[çğıöşüÇĞİÖŞÜ]', line)):
            # انگلیسی: غلط‌یابی
            line = correct_with_pyspell(line, en_checker)
        elif lang == 'tr' or re.search(r'[çğıöşüÇĞİÖŞÜ]', line):
            # ترکی: فعلاً فقط حروف تکراری حذف شده‌اند (برای جلوگیری از خطای حجم در ورسل)
            pass
                    
        processed_lines.append(line)
        
    return '\n'.join(processed_lines)

def process_single_language(text: str, lang: str) -> str:
    text = remove_duplicate_chars(text)
    if lang == 'fa':
        return hazm_norm.normalize(text)
    elif lang == 'ar':
        text = araby.normalize_hamza(text)
        text = araby.strip_tashkeel(text)
        return correct_with_pyspell(text, ar_checker)
    elif lang == 'en':
        return correct_with_pyspell(text, en_checker)
    return text

def correct_with_pyspell(text: str, checker) -> str:
    words = text.split()
    corrected_words = []
    for word in words:
        clean_word = re.sub(r'[^\w\s\u0600-\u06FF]', '', word)
        if clean_word and clean_word.lower() in checker:
            corrected_words.append(word)
        elif clean_word:
            correction = checker.correction(clean_word)
            if correction:
                # حفظ حروف بزرگ در انگلیسی
                if clean_word[0].isupper() and correction:
                    correction = correction.capitalize()
                corrected_words.append(word.replace(clean_word, correction))
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)
    return ' '.join(corrected_words)

handler = Mangum(app)
