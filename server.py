import base64
import json
import urllib.request
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='.')
TOKEN = open(os.path.join(os.path.dirname(__file__), '.env')).read().strip()
API_URL = "https://models.inference.ai.azure.com/chat/completions"

def call_gpt(messages):
    payload = json.dumps({"model": "gpt-4o", "messages": messages}).encode()
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
        {"role": "system", "content": """You are a reading assistant. A reader is returning to a book after a break and needs a quick catch-up.

Write 4-6 sentences structured as:
- 1-2 sentences: recent events that led to this moment
- 2-3 sentences: what is concretely happening at this passage

Rules:
- Only report actions and events that explicitly appear in the text or directly precede it.
- Never infer, interpret, or editorialize. No "he feels", "he realizes", "his mind races", "the tension lies in", "a breakthrough seems possible", "this shifts his focus", "he begins to grasp".
- If it didn't happen on the page, don't write it.
- No book premise recap. No greetings. No filler.
- Hard spoiler wall: nothing beyond this passage.
- Plain present tense. Factual and direct."""},
        {"role": "user", "content": f"Book: {book}\n\nPassage where I stopped:\n\n{text}\n\nWhere am I in the story?"}
    ])
    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=3000)
