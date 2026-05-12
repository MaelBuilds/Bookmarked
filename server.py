import base64
import json
import urllib.request
from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

app = Flask(__name__, static_folder='.')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB upload cap

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

def _load_token():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        for line in open(env_path).read().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                if key.strip() == 'GITHUB_TOKEN':
                    return val.strip()
    raise RuntimeError("GITHUB_TOKEN not set -- add it to your environment or .env file")
_ENV_TOKEN = _load_token()
API_URL = "https://models.inference.ai.azure.com/chat/completions"

def call_gpt(messages):
    payload = json.dumps({"model": "gpt-4o-mini", "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=payload,
        headers={"Authorization": f"Bearer {_ENV_TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/ocr', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def ocr():
    image_data = request.json.get('image')
    if not image_data:
        return jsonify({"error": "No image provided"}), 400
    # Basic validation: base64-encoded images start with expected prefixes
    try:
        header = image_data[:16].encode() if isinstance(image_data, str) else image_data[:16]
        import base64 as _b64
        decoded_start = _b64.b64decode(image_data[:20] + '==')[:4]
        # JPEG: FF D8, PNG: 89 50, GIF: 47 49, WEBP: 52 49
        valid_sigs = [b'\xff\xd8', b'\x89P', b'GI', b'RI']
        if not any(decoded_start[:2] == sig for sig in valid_sigs):
            return jsonify({"error": "Invalid image format"}), 400
    except Exception:
        return jsonify({"error": "Invalid image data"}), 400
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
    text = request.json.get('text')
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

@app.route('/summarize', methods=['POST'])
@limiter.limit("20 per day; 5 per minute")
def summarize():
    text = request.json.get('text')
    book = request.json.get('book')
    mode = request.json.get('mode', 'light')
    prompt = PROMPT_FULL if mode == 'full' else PROMPT_LIGHT
    summary = call_gpt([
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Book: {book}\n\nPassage where I stopped:\n\n{text}\n\nWhere am I in the story?"}
    ])
    return jsonify({"summary": summary})

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', '3000'))
    app.run(debug=debug, host='0.0.0.0', port=port)
