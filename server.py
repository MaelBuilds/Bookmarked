import base64
import json
import re
import time
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(ROOT_DIR, 'frontend', 'dist')
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB upload cap

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

DEBUG_LOG_PATH = os.path.join(ROOT_DIR, 'debug-476059.log')


def _agent_log(location, message, data=None, hypothesis_id=None, run_id='pre-fix'):
    # #region agent log
    try:
        entry = {
            'sessionId': '476059',
            'timestamp': int(time.time() * 1000),
            'location': location,
            'message': message,
            'data': data or {},
            'runId': run_id,
        }
        if hypothesis_id:
            entry['hypothesisId'] = hypothesis_id
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass
    # #endregion


def _token_meta(token, source):
    if not token:
        return {'source': source, 'len': 0, 'format': 'empty'}
    return {
        'source': source,
        'len': len(token),
        'format': (
            'ghp' if token.startswith('ghp_')
            else 'github_pat' if token.startswith('github_pat_')
            else 'other'
        ),
        'has_outer_quotes': (
            (token.startswith('"') and token.endswith('"'))
            or (token.startswith("'") and token.endswith("'"))
        ),
        'has_edge_whitespace': token != token.strip(),
    }


def _load_token():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token, 'env'
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        for line in open(env_path).read().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                if key.strip() == 'GITHUB_TOKEN':
                    return val.strip(), 'file'
    raise RuntimeError("GITHUB_TOKEN not set -- add it to your environment or .env file")


_ENV_TOKEN, _TOKEN_SOURCE = _load_token()
_agent_log('server.py:startup', 'token loaded', _token_meta(_ENV_TOKEN, _TOKEN_SOURCE), 'A')
API_URL = "https://models.inference.ai.azure.com/chat/completions"
API_VERSION = "multilingual-2"

class GPTError(Exception):
    """Raised when the LLM call fails for any reason."""
    def __init__(self, message, status_code=502, code='gpt_unavailable'):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def api_error(code, message=None, status=400):
    body = {'code': code}
    if message:
        body['error'] = message
    return jsonify(body), status

def call_gpt(messages):
    payload = json.dumps({"model": "gpt-4o-mini", "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=payload,
        headers={"Authorization": f"Bearer {_ENV_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            meta = _token_meta(_ENV_TOKEN, _TOKEN_SOURCE)
            _agent_log('server.py:call_gpt', 'GitHub Models returned 401', meta, 'B')
        code_map = {
            401: (401, "Invalid API token", "invalid_token"),
            429: (429, "AI service rate limit reached — try again in a minute", "gpt_rate_limit"),
            500: (502, "AI service is temporarily down", "gpt_unavailable"),
            503: (502, "AI service is temporarily unavailable", "gpt_unavailable"),
        }
        sc, msg, code = code_map.get(e.code, (502, f"AI service error (HTTP {e.code})", "gpt_error"))
        raise GPTError(msg, sc, code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise GPTError("Could not reach AI service — check your connection", 502, "gpt_unavailable")
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise GPTError("AI service returned an unexpected response", 502, "gpt_error")

@app.errorhandler(GPTError)
def handle_gpt_error(e):
    body = {"code": e.code, "error": str(e)}
    if e.status_code == 401 and os.environ.get('TOKEN_DEBUG', '').lower() == 'true':
        body['token_debug'] = _token_meta(_ENV_TOKEN, _TOKEN_SOURCE)
    return jsonify(body), e.status_code

@app.route('/')
def index():
    index_path = os.path.join(FRONTEND_DIST, 'index.html')
    if not os.path.isfile(index_path):
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Bookmarked</title></head>'
            '<body style="font-family:Georgia,serif;padding:2rem;max-width:36rem;line-height:1.5">'
            '<p><strong>Frontend not built.</strong> The React app must be compiled first.</p>'
            '<p>From the repo root:</p>'
            '<pre style="background:#f5f5f5;padding:0.75rem">cd frontend\nnpm install\nnpm run build</pre>'
            '<p>Then start the server again.</p>'
            '</body></html>',
            503,
            {'Content-Type': 'text/html; charset=utf-8'},
        )
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/dist-assets/<path:filename>')
def vite_dist_assets(filename):
    return send_from_directory(os.path.join(FRONTEND_DIST, 'dist-assets'), filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route('/health')
def health():
    payload = {
        "ok": True,
        "api_version": API_VERSION,
        "summarize_response_fields": ["summary", "output_language", "api_version"],
    }
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>Bookmarked API</title></head>'
        '<body style="font-family:Georgia,serif;max-width:32rem;margin:2rem auto;line-height:1.6">'
        '<h1>Bookmarked API</h1>'
        f'<p><strong>Status:</strong> OK</p>'
        f'<p><strong>Version:</strong> {API_VERSION}</p>'
        '<p><strong>Summarize response includes:</strong> '
        'summary, output_language, api_version</p>'
        '<p>If this page is blank or you only see an empty JSON tree, '
        'you are not on the current API build.</p>'
        '<p><a href="/">Open app</a> · '
        '<a href="/health?format=json">JSON</a></p>'
        '</body></html>'
    ), 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/ocr', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def ocr():
    if not request.json:
        return api_error('no_image', 'No image provided', 400)
    image_data = request.json.get('image')
    if not image_data:
        return api_error('no_image', 'No image provided', 400)
    # Basic validation: base64-encoded images start with expected prefixes
    try:
        decoded_start = base64.b64decode(image_data[:20] + '==')[:4]
        # JPEG: FF D8, PNG: 89 50, GIF: 47 49, WEBP: 52 49
        valid_sigs = [b'\xff\xd8', b'\x89P', b'GI', b'RI']
        if not any(decoded_start[:2] == sig for sig in valid_sigs):
            return api_error('invalid_image', 'Invalid image format', 400)
    except Exception:
        return api_error('invalid_image', 'Invalid image data', 400)
    extracted = call_gpt([
        {"role": "system", "content": "Extract only the text visible in this image. Return raw text exactly as it appears. Nothing else."},
        {"role": "user", "content": [
            {"type": "text", "text": "Extract the text from this page."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]}
    ])
    return jsonify({"text": extracted})

@app.route('/identify', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def identify():
    text = request.json.get('text') if request.json else None
    if not text or not text.strip():
        return api_error('no_text', 'No text provided', 400)
    book = call_gpt([
        {"role": "system", "content": "Identify the book and author from this text excerpt. Reply with only: Title by Author. If you cannot identify it, reply with only: UNKNOWN"},
        {"role": "user", "content": text}
    ])
    if book.strip().upper() == "UNKNOWN":
        return jsonify({"status": "needs_cover"})
    return jsonify({"status": "ok", "book": book})

PROMPT_LIGHT = """You are a knowledgeable librarian helping a reader pick up where they left off. You speak with warmth, quiet authority, and a genuine love of books — like someone who has read everything and remembers all of it.

Write 4-6 sentences:
- 1-2 sentences: orient the reader — who the character is, their background, and the stakes of their situation (mission, circumstances, what brought them here)
- 2-3 sentences: what has been happening recently and what is concretely occurring at this passage

Rules:
- Stick to facts and events. No emotional interpretation ("he feels", "his mind races"), no dramatic framing ("the tension lies in", "this marks a significant moment").
- No spoilers beyond this passage.
- No greetings, no filler.
- Plain present tense."""

PROMPT_FULL = """You are a knowledgeable librarian helping a reader who has been away from a book for a long time and needs a full catch-up. You speak with warmth and a genuine love of books.

Write three sections — no headers, just flowing prose separated by a blank line:

1. The main characters: who they are, their role in the story, and where they stand as of this passage. Cover every significant character the reader has met so far.

2. The key events: what has happened from the beginning of the book up to this passage, in order. Hit the major plot points — decisions made, conflicts introduced, turning points reached.

3. Right now: what is concretely happening at this exact passage.

Rules:
- The passage is the hard spoiler wall. Nothing beyond it.
- Stick to facts and events. No emotional interpretation, no dramatic framing.
- No greetings, no filler, no section labels.
- Plain present tense."""

SUPPORTED_OUTPUT_LANGS = {'en', 'fr'}
LANG_NAMES = {'en': 'English', 'fr': 'French'}
LANG_ALIASES = {
    'en': 'en', 'english': 'en', 'anglais': 'en',
    'fr': 'fr', 'french': 'fr', 'francais': 'fr', 'français': 'fr',
}
USER_QUESTION = {
    'en': 'Where am I in the story?',
    'fr': 'Où en suis-je dans l\'histoire ?',
}
FR_ACCENTS = set('àâäæçéèêëïîôùûüœ')
FR_WORDS_RE = re.compile(
    r'\b(le|la|les|des|de|du|un|une|et|est|dans|que|qui|pour|pas|plus|avec|sur|son|sa|ses|'
    r'ce|cette|était|été|avoir|être|comme|tout|très|mais|ou|où|donc|car|ni|ne|il|elle|nous|vous)\b',
    re.I,
)
EN_WORDS_RE = re.compile(
    r'\b(the|and|was|were|had|have|has|been|that|with|for|not|but|his|her|their|this|from|'
    r'they|would|could|she|he|it|you|we|my|me|him|her|as|at|by|an|or|if|when|what)\b',
    re.I,
)


def parse_lang_code(raw):
    """Normalize model or heuristic output to en/fr or None."""
    if not raw:
        return None
    cleaned = re.sub(r'[^a-zàâäæçéèêëïîôùûüœ\- ]', ' ', raw.strip().lower())
    for token in cleaned.split():
        key = token.split('-')[0]
        if key in LANG_ALIASES:
            return LANG_ALIASES[key]
    return None


def detect_passage_language_local(text):
    """Fast en/fr guess from OCR text — avoids an extra model call when clear."""
    sample = text[:4000]
    if len(sample.strip()) < 15:
        return None
    lower = sample.lower()
    accent_count = sum(1 for c in lower if c in FR_ACCENTS)
    fr_hits = len(FR_WORDS_RE.findall(lower))
    en_hits = len(EN_WORDS_RE.findall(lower))
    score_fr = accent_count * 3 + fr_hits
    score_en = en_hits
    if score_fr >= 3 and score_fr > score_en:
        return 'fr'
    if score_en >= 3 and score_en > score_fr:
        return 'en'
    return None


def infer_passage_language(text):
    """LLM fallback when local detection is ambiguous."""
    raw = call_gpt([
        {
            "role": "system",
            "content": (
                "What language is this book passage written in? "
                "Reply with exactly one token: en OR fr. No other words."
            ),
        },
        {"role": "user", "content": text[:2000]},
    ])
    return parse_lang_code(raw)


def detect_passage_language(text):
    return detect_passage_language_local(text) or infer_passage_language(text)


def resolve_output_language(text, ui_locale):
    """Summary language follows the UI picker; passage detection if ui_locale is missing."""
    if ui_locale in SUPPORTED_OUTPUT_LANGS:
        return ui_locale, LANG_NAMES[ui_locale]
    detected = detect_passage_language(text)
    if detected in SUPPORTED_OUTPUT_LANGS:
        return detected, LANG_NAMES[detected]
    return 'en', LANG_NAMES['en']


def language_instruction(lang_name):
    return (
        f"OUTPUT LANGUAGE: {lang_name} only. "
        f"Write every sentence of your summary in {lang_name}. "
        f"Do not use any other language."
    )


def build_summarize_messages(book, text, mode, lang_code, lang_name):
    base = PROMPT_FULL if mode == 'full' else PROMPT_LIGHT
    instruction = language_instruction(lang_name)
    system = f"{base}\n\n{instruction}"
    question = USER_QUESTION.get(lang_code, USER_QUESTION['en'])
    user = (
        f"{instruction}\n\n"
        f"Book: {book}\n\n"
        f"Passage where I stopped:\n\n{text}\n\n"
        f"{question}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

@app.route('/summarize', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def summarize():
    text = request.json.get('text') if request.json else None
    book = request.json.get('book') if request.json else None
    if not text or not text.strip():
        return api_error('no_text', 'No text provided', 400)
    if not book or not book.strip():
        return api_error('no_book', 'No book provided', 400)
    mode = request.json.get('mode', 'light')
    ui_locale = (request.json.get('ui_locale') or 'en').strip().lower()
    lang_code, lang_name = resolve_output_language(text, ui_locale)
    messages = build_summarize_messages(book, text, mode, lang_code, lang_name)
    summary = call_gpt(messages)
    return jsonify({
        "summary": summary,
        "output_language": lang_code,
        "api_version": API_VERSION,
    })

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', '3000'))
    print(f"Bookmarked API {API_VERSION} — http://0.0.0.0:{port} (GET /health to verify)")
    app.run(debug=debug, host='0.0.0.0', port=port)
