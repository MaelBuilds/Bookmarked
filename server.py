import base64
import hashlib
import json
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
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


API_URL = "https://models.inference.ai.azure.com/chat/completions"
API_VERSION = "multilingual-2"
DEFAULT_MODEL = "gpt-4o-mini"
SUMMARIZE_FULL_MODEL = os.environ.get('SUMMARIZE_FULL_MODEL', 'gpt-4.1').strip()
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'github').strip().lower()
GPT_RESPONSE_CACHE = {}
FAKE_OCR_TEXT = (
    "Paul Atreides studies the desert of Arrakis. "
    "The spice is valuable, the Harkonnens remain a threat, and his family is trying to understand the planet."
)
FAKE_BOOK = "Dune by Frank Herbert"
FAKE_SUMMARY_EN = (
    "Paul Atreides and his family have arrived on Arrakis, where control of the spice has placed them in danger. "
    "House Atreides is learning the politics and hazards of the desert while old enemies continue to threaten them. "
    "At this passage, Paul is still near the beginning of that conflict, with the planet's risks becoming clearer."
)
FAKE_SUMMARY_FR = (
    "Paul Atréides et sa famille sont arrivés sur Arrakis, où le contrôle de l'épice les met en danger. "
    "La maison Atréides découvre les risques politiques et physiques du désert pendant que ses ennemis restent menaçants. "
    "Dans ce passage, Paul se trouve encore au début de ce conflit, alors que les dangers de la planète deviennent plus nets."
)

if AI_PROVIDER not in {'github', 'fake'}:
    raise RuntimeError("AI_PROVIDER must be either 'github' or 'fake'")

if AI_PROVIDER == 'fake' and os.environ.get('RAILWAY_ENVIRONMENT'):
    raise RuntimeError("Refusing to start Railway with AI_PROVIDER=fake")

_ENV_TOKEN, _TOKEN_SOURCE = _load_token() if AI_PROVIDER == 'github' else (None, 'fake')

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


def _bookmarked_debug():
    return os.environ.get('BOOKMARKED_DEBUG', '').lower() in ('1', 'true', 'yes')


def _text_preview(text, limit=200):
    collapsed = ' '.join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit] + '…'


def _debug_log(message):
    if _bookmarked_debug():
        print(f'[bookmarked] {message}', file=sys.stderr, flush=True)


_OCR_PREAMBLE_PATTERNS = (
    re.compile(r'^\s*voici\s+le\s+texte\s+extrait\s*:\s*', re.I),
    re.compile(r'^\s*here\s+is\s+the\s+extracted\s+text\s*:\s*', re.I),
    re.compile(r'^\s*here\s+is\s+the\s+text\s*:\s*', re.I),
)

IDENTIFY_SYSTEM = (
    "You identify the published book that a text excerpt is taken from. "
    "The excerpt may be narration, dialogue, or an in-book song or poem. "
    "Reply with the title and author of the real, published work — never a character name, "
    "a chapter or poem title, or a word lifted from the passage. "
    "Use the book's title in the SAME LANGUAGE as the excerpt — for a French passage give the "
    "French title (e.g. 'Charlie et la Chocolaterie par Roald Dahl'), for an English passage the English title. "
    "Reply with ONLY the book in the form: Title by Author. "
    "If you are not confident which published work this excerpt comes from, reply with only: UNKNOWN"
)


class _CatalogUnavailable(Exception):
    """Raised when the bibliographic catalog cannot be reached (vs. a clean no-match)."""


def _clean_passage_text(text):
    cleaned = text.strip()
    for pattern in _OCR_PREAMBLE_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    return cleaned.strip()


def _parse_title_author(book):
    """Split a 'Title by Author' / 'Titre par Auteur' string into (title, author)."""
    book = book.strip()
    lowered = book.lower()
    for sep in (' by ', ' par '):
        idx = lowered.find(sep)
        if idx != -1:
            return book[:idx].strip(' .'), book[idx + len(sep):].strip(' .')
    return book.strip(' .'), ''


def _normalize_for_match(text):
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def _title_overlap(candidate_title, catalog_title):
    """True when two normalized titles share enough word tokens to be the same work."""
    a = set(_normalize_for_match(candidate_title).split())
    b = set(_normalize_for_match(catalog_title).split())
    if not a or not b:
        return False
    common = a & b
    return len(common) >= max(1, min(len(a), len(b)) // 2)


def _catalog_enabled():
    """Catalog grounding runs against the real model; skipped in fake/test contexts."""
    return AI_PROVIDER == 'github' and not app.config.get('TESTING', False)


def _catalog_lookup(title, author, lang=None):
    """Verify a candidate against Google Books.

    When `lang` is given, results are restricted to that language so the
    matching-language edition title is returned (e.g. the French title for a
    French passage). Returns the canonical 'Title by Author' on a confident
    match, None on a clean no-match, raises _CatalogUnavailable if unreachable.
    """
    q_parts = []
    if title:
        q_parts.append('intitle:' + urllib.parse.quote(title))
    if author:
        q_parts.append('inauthor:' + urllib.parse.quote(author))
    if not q_parts:
        return None
    url = (
        'https://www.googleapis.com/books/v1/volumes?q='
        + '+'.join(q_parts)
        + '&maxResults=5&printType=books'
    )
    if lang:
        url += '&langRestrict=' + urllib.parse.quote(lang)
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise _CatalogUnavailable()
    for item in data.get('items') or []:
        info = item.get('volumeInfo', {})
        cat_title = info.get('title', '')
        if not cat_title or not _title_overlap(title, cat_title):
            continue
        authors = info.get('authors') or []
        author_str = authors[0] if authors else author
        return f"{cat_title} by {author_str}" if author_str else cat_title
    return None


def _resolve_identification(candidate, lang=None):
    """Ground an LLM book guess against the catalog.

    Prefers the edition in the passage's language; falls back to an unrestricted
    lookup if that yields nothing. Returns a canonical 'Title by Author' when
    verified, the original candidate when the catalog is unreachable (graceful
    degrade), or None when the catalog has no matching work.
    """
    title, author = _parse_title_author(candidate)
    try:
        match = _catalog_lookup(title, author, lang)
        if not match and lang:
            match = _catalog_lookup(title, author, None)
        return match
    except _CatalogUnavailable:
        return candidate


def _fake_gpt_response(messages):
    endpoint = request.endpoint if request else None
    if endpoint == 'ocr':
        return FAKE_OCR_TEXT
    if endpoint == 'identify':
        text = str(messages[-1].get('content', '') if messages else '')
        if 'unknown' in text.lower() or 'needs_cover' in text.lower():
            return "UNKNOWN"
        return FAKE_BOOK
    if endpoint == 'summarize':
        joined = "\n".join(str(msg.get('content', '')) for msg in messages)
        return FAKE_SUMMARY_FR if "OUTPUT LANGUAGE: French only" in joined else FAKE_SUMMARY_EN

    joined = "\n".join(str(msg.get('content', '')) for msg in messages)
    if "Reply with exactly one token: en OR fr" in joined:
        return "en"
    return "mocked response"


def _call_github_models(messages, meta=None, model=None):
    model = model or DEFAULT_MODEL
    cache_key = hashlib.sha256(
        json.dumps([model, messages], sort_keys=True).encode()
    ).hexdigest()
    if cache_key in GPT_RESPONSE_CACHE:
        if meta is not None:
            meta['gpt_cache_hit'] = True
        return GPT_RESPONSE_CACHE[cache_key]
    payload = json.dumps({"model": model, "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=payload,
        headers={"Authorization": f"Bearer {_ENV_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
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
        content = body["choices"][0]["message"]["content"]
        GPT_RESPONSE_CACHE[cache_key] = content
        if meta is not None:
            meta['gpt_cache_hit'] = False
        return content
    except (KeyError, IndexError, TypeError):
        raise GPTError("AI service returned an unexpected response", 502, "gpt_error")


def call_gpt(messages, meta=None, model=None):
    if AI_PROVIDER == 'fake':
        if meta is not None:
            meta['gpt_cache_hit'] = False
        return _fake_gpt_response(messages)
    return _call_github_models(messages, meta=meta, model=model)

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
        "ai_provider": AI_PROVIDER,
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
        f'<p><strong>AI provider:</strong> {AI_PROVIDER}</p>'
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
    gpt_meta = {}
    extracted = call_gpt([
        {"role": "system", "content": (
            "Extract only the text visible in this image. Return raw text exactly as it appears. "
            "No commentary, labels, or preamble (do not write e.g. 'Here is the text'). Nothing else."
        )},
        {"role": "user", "content": [
            {"type": "text", "text": "Extract the text from this page."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]}
    ], meta=gpt_meta)
    extracted = _clean_passage_text(extracted)
    payload = {"text": extracted}
    if _bookmarked_debug():
        preview = _text_preview(extracted)
        _debug_log(
            f'ocr text_len={len(extracted)} cache_hit={gpt_meta.get("gpt_cache_hit")} '
            f'preview={preview!r}'
        )
        payload['debug'] = {
            'text_len': len(extracted),
            'text_preview': preview,
            'gpt_cache_hit': gpt_meta.get('gpt_cache_hit', False),
        }
    return jsonify(payload)

@app.route('/identify', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def identify():
    text = request.json.get('text') if request.json else None
    if not text or not text.strip():
        return api_error('no_text', 'No text provided', 400)
    text = _clean_passage_text(text)
    gpt_meta = {}
    candidate = call_gpt([
        {"role": "system", "content": IDENTIFY_SYSTEM},
        {"role": "user", "content": text},
    ], meta=gpt_meta).strip()
    identify_raw = candidate
    book = candidate
    # Ground the guess against a real catalog: an unverifiable title is treated as
    # unidentified so the user is asked for the book rather than shown a hallucination.
    # The passage language steers grounding toward the matching-language edition.
    if candidate.upper() != "UNKNOWN" and _catalog_enabled():
        lang = detect_passage_language_local(text)
        resolved = _resolve_identification(candidate, lang)
        book = resolved if resolved else "UNKNOWN"

    if book.upper() == "UNKNOWN":
        payload = {"status": "needs_cover"}
        if _bookmarked_debug():
            preview = _text_preview(text)
            _debug_log(
                f'identify UNKNOWN text_len={len(text)} raw={identify_raw!r} preview={preview!r}'
            )
            payload['debug'] = {
                'text_len': len(text),
                'text_preview': preview,
                'identify_raw': identify_raw,
                'gpt_cache_hit': gpt_meta.get('gpt_cache_hit', False),
            }
        return jsonify(payload)
    payload = {"status": "ok", "book": book}
    if _bookmarked_debug():
        preview = _text_preview(text)
        _debug_log(
            f'identify ok book={book!r} raw={identify_raw!r} text_len={len(text)} '
            f'cache_hit={gpt_meta.get("gpt_cache_hit")} preview={preview!r}'
        )
        payload['debug'] = {
            'text_len': len(text),
            'text_preview': preview,
            'identify_raw': identify_raw,
            'book': book,
            'gpt_cache_hit': gpt_meta.get('gpt_cache_hit', False),
        }
    return jsonify(payload)

PROMPT_LIGHT = """You are a knowledgeable librarian giving a reader a "Previously on…" recap — like the cold open of a TV episode — for the book they are returning to. You speak with warmth, quiet authority, and a genuine love of books.

You are given the book's title and author and the passage where the reader stopped. Use your knowledge of this specific book to recap the story that leads up to that passage.

Answer one question for the returning reader: how did the story arrive at this moment? Write 4-6 sentences that trace how the story got here — not a flat list of events, but how one thing leads to the next.
- Name the novel's protagonist (who the book is chiefly about) and follow the people, places, and turning points that carry the story to this passage.
- End where the reader is now: what is happening at this point and who is present.

Tell the STORY, not the page:
- Don't describe the text as text — no "this passage", "this page", and don't say "the poem", "the song", or "the scene" "describes", "features", "presents", or "depicts" anything.
- But DO include what is actually happening at this point and who is present. If characters are singing, name them and what the song is about, told as a story event — not as a description of the writing. Never call a side character the protagonist or "personnage principal".

Rules:
- Use only what actually happens in the book up to this passage. Invent nothing — no events, names, or details you are not sure are in the book.
- If you are unsure where this passage falls, recap only what is firmly established before it rather than guessing.
- The passage is a hard spoiler wall: nothing that happens after it.
- Concrete events only. Cut vague qualifiers and hedging ("playful", "vivid", "whimsical", "light-hearted", "surreal", "festive", "humorously", "hinting at", "ensuring a fun scene"). No emotional interpretation ("he feels"), no dramatic framing ("this marks a significant moment").
- No greetings, no filler. Plain present tense."""

PROMPT_FULL = """You are a knowledgeable librarian giving a reader a full catch-up on a book they have been away from for a long time — a detailed "Previously on…" recap. You speak with warmth and a genuine love of books.

You are given the book's title and author and the passage where the reader stopped. Use your knowledge of this specific book to retell the story so far.

Answer one question for a reader returning to this book after a long time: how did the story arrive at this moment? Write a flowing recap of two to three short paragraphs (about 8-12 sentences) that traces the chain of cause and effect from the beginning of the book to this passage — each major event leading to the next, not a neutral list. Name the protagonist early, carry the reader through the decisions, conflicts, and turning points that lead here, and finish at the moment the reader has just reached. Introduce the other characters as they enter the story, through what they do.

Rules:
- Tell the STORY, not the page. Don't describe the text as text — no "this passage", "this page", and don't say "the poem", "the song", or "the scene" "describes", "features", or "presents" anything. But DO include what is actually happening in the story at this point and who is present: if characters are singing, name them and what the song is about, told as a story event.
- Never write roster sentences. Do not say a character "is also an important character", "is a significant character", "plays a role", "represents a trait", or "is very different" — just show what they do in the story. Introduce people by what happens to them.
- Never promote a side character who only appears here to protagonist.
- Open straight into the first events of the story. No scene-setting preamble and no abstract characterisation before the action begins.
- Your final sentence must state a concrete action or fact at the moment the reader has just reached, then stop. Do not end with a sentence about mood, atmosphere, or what is coming ("aventures à venir", "ambiance pétillante", "la tension monte", "on se demande…", "surprise éclatante"). The recap simply ends where the reader is.
- Introduce the other characters in one running sentence of plain facts, not with "nous découvrons" / "we meet" framing — name them and what they do.
- Use only events that occur up to this passage; invent nothing. If you are unsure where the passage falls, recap only what is firmly established before it.
- The passage is the hard spoiler wall. Nothing beyond it.
- Concrete events only. Cut vague qualifiers and hedging ("playful", "vivid", "whimsical", "festive", "humorously", "hinting at", "probably", "uncertain outcome"). No emotional interpretation, no dramatic framing ("a key moment", "a turning point in the story").
- No greetings, no filler, no headers or section labels. Plain present tense."""

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
    text = _clean_passage_text(text)
    gpt_meta = {}
    messages = build_summarize_messages(book, text, mode, lang_code, lang_name)
    model = SUMMARIZE_FULL_MODEL if mode == 'full' else DEFAULT_MODEL
    summary = call_gpt(messages, meta=gpt_meta, model=model)
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
