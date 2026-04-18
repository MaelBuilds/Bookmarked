import base64
import json
import urllib.request
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='.')
TOKEN = open(os.path.join(os.path.dirname(__file__), '.env')).read().strip()
API_URL = "https://models.inference.ai.azure.com/chat/completions"

def call_gpt(messages):
    payload = json.dumps({"model": "gpt-4o-mini", "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=payload,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/ocr', methods=['POST'])
def ocr():
    image_data = request.json.get('image')
    extracted = call_gpt([
        {"role": "system", "content": "Extract only the text visible in this image. Return raw text exactly as it appears. Nothing else."},
        {"role": "user", "content": [
            {"type": "text", "text": "Extract the text from this page."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]}
    ])
    return jsonify({"text": extracted})

@app.route('/identify', methods=['POST'])
def identify():
    text = request.json.get('text')
    book = call_gpt([
        {"role": "system", "content": "Identify the book and author from this text excerpt. Reply with only: Title by Author. If you cannot identify it, reply with only: UNKNOWN"},
        {"role": "user", "content": text}
    ])
    if book.strip().upper() == "UNKNOWN":
        return jsonify({"status": "needs_cover"})
    return jsonify({"status": "ok", "book": book})

@app.route('/summarize', methods=['POST'])
def summarize():
    text = request.json.get('text')
    book = request.json.get('book')
    summary = call_gpt([
        {"role": "system", "content": """You are a knowledgeable librarian helping a reader pick up where they left off. You speak with warmth, quiet authority, and a genuine love of books — like someone who has read everything and remembers all of it.

Write 4-6 sentences:
- 1-2 sentences: orient the reader — who the character is, their background, and the stakes of their situation (mission, circumstances, what brought them here)
- 2-3 sentences: what has been happening recently and what is concretely occurring at this passage

Rules:
- Stick to facts and events. No emotional interpretation ("he feels", "his mind races"), no dramatic framing ("the tension lies in", "this marks a significant moment").
- No spoilers beyond this passage.
- No greetings, no filler.
- Plain present tense."""},
        {"role": "user", "content": f"Book: {book}\n\nPassage where I stopped:\n\n{text}\n\nWhere am I in the story?"}
    ])
    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=3000)
