from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from mangum import Mangum
import re, logging, os, requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ایمپورت‌های ضد‌باگ
try:
    import symspellpy
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    SYMSPELL_AVAILABLE = False

try:
    from hazm import Normalizer, word_tokenize
    hazm_norm = Normalizer()
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False

try:
    import akana
    akana_spell = akana.SpellChecker()
    AKANA_AVAILABLE = True
except ImportError:
    AKANA_AVAILABLE = False

app = FastAPI()

class TextInput(BaseModel):
    text: str
    language: str = "auto"

# --- مدیریت دیکشنری‌ها ---
def load_symspell_dict(dict_path, max_edit_distance=2):
    if not SYMSPELL_AVAILABLE: return None
    sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)
    if not os.path.exists(dict_path):
        url = "https://raw.githubusercontent.com/mammothb/symspellpy/master/symspellpy/frequency_dictionary_en_82_765.txt"
        if "fa" in dict_path:
            url = "https://raw.githubusercontent.com/pooya-mohammadi/persian-spell-checker-kenlm/master/frequency_dictionary_fa_100k.txt"
        try:
            r = requests.get(url, timeout=10)
            with open(dict_path, 'wb') as f: f.write(r.content)
        except Exception as e:
            logger.error(f"Could not download dictionary: {e}")
            return sym_spell
    sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
    return sym_spell

en_sym = load_symspell_dict("/tmp/en_dict.txt")
fa_sym = load_symspell_dict("/tmp/fa_dict.txt")
ar_checker = None # در صورت نیاز به دیکشنری عربی می‌توانید مشابه بالا اضافه کنید

# --- توابع کمکی ---
def detect_language(line: str) -> str:
    if re.search(r'[پچژگ]', line): return 'fa'
    if re.search(r'[\u0600-\u06FF]', line): return 'ar'
    if re.search(r'[çğıöşüÇĞİÖŞÜ]', line): return 'tr'
    if re.search(r'[a-zA-Z]', line): return 'en'
    return 'unknown'

def correct_with_symspell(text: str, sym_spell) -> str:
    if not sym_spell: return text
    words = text.split()
    corrected = []
    for word in words:
        match = re.match(r'^([^\w]*)([\w\u0600-\u06FF]+)([^\w]*)$', word)
        if not match: corrected.append(word); continue
        prefix, clean, suffix = match.groups()
        suggestions = sym_spell.lookup(clean, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected.append(f"{prefix}{suggestions[0].term}{suffix}")
        else:
            corrected.append(word)
    return ' '.join(corrected)

def correct_with_akana(text: str) -> str:
    if not AKANA_AVAILABLE: return text
    words = text.split()
    corrected = []
    for word in words:
        match = re.match(r'^([^\w]*)([a-zA-ZçğıöşüÇĞİÖŞÜ]+)([^\w]*)$', word)
        if not match: corrected.append(word); continue
        prefix, clean, suffix = match.groups()
        if akana_spell.is_correct(clean): corrected.append(word)
        else:
            suggestions = akana_spell.suggest(clean)
            if suggestions: corrected.append(f"{prefix}{suggestions[0]}{suffix}")
            else: corrected.append(word)
    return ' '.join(corrected)

def process_text_pipeline(text: str) -> str:
    lines = text.split('\n')
    processed = []
    for line in lines:
        if not line.strip(): processed.append(line); continue
        lang = detect_language(line)
        if lang == 'fa':
            if HAZM_AVAILABLE: line = hazm_norm.normalize(line)
            line = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', line)
            line = correct_with_symspell(line, fa_sym)
        elif lang == 'ar':
            line = re.sub(r'([\u0600-\u06FF])\1{2,}', r'\1', line)
            line = correct_with_symspell(line, ar_checker)
        elif lang == 'tr':
            line = re.sub(r'([a-zA-ZçğıöşüÇĞİÖŞÜ])\1{2,}', r'\1', line)
            line = correct_with_akana(line)
        elif lang == 'en':
            line = re.sub(r'([a-zA-Z])\1{2,}', r'\1', line)
            line = correct_with_symspell(line, en_sym)
        processed.append(line)
    return '\n'.join(processed)

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

@app.post("/api/process")
async def process_text(input: TextInput):
    try:
        text = input.text
        if not text.strip(): return {"success": False, "error": "متن خالی است."}
        corrected = process_text_pipeline(text)
        return {"success": True, "text": corrected, "detected_language": "ترکیبی"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

handler = Mangum(app)
