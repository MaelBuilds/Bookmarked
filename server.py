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

@app.route('/summarize', methods=['POST'])
def summarize():
    image_data = request.json.get('image')  # base64 string

    # Step 1: OCR
    extracted = call_gpt([
        {"role": "system", "content": "Extract only the text visible in this image. Return raw text exactly as it appears. Nothing else."},
        {"role": "user", "content": [
            {"type": "text", "text": "Extract the text from this page."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]}
    ])

    # Step 2: Identify book
    book = call_gpt([
        {"role": "system", "content": "Identify the book and author from this text excerpt. Reply with only: Title by Author. If you cannot identify it, reply with only: UNKNOWN"},
        {"role": "user", "content": extracted}
    ])

    if book.strip().upper() == "UNKNOWN":
        return jsonify({"status": "needs_cover"})

    # Step 3: Spoiler-free summary
    summary = call_gpt([
        {"role": "system", "content": """You are a reading assistant. A reader is returning to a book after a long break and needs to remember where they are in the story — not what the book is about.

Rules:
- 3-5 sentences maximum.
- No greetings, no filler, no book premise recap.
- Assume the reader knows the book. Skip the setup they already know.
- Focus on: what was happening recently in the story, what problem or tension is active, and where the character's head is at this exact passage.
- Hard spoiler wall: nothing beyond this passage.
- Plain present tense. Specific and direct."""},
        {"role": "user", "content": f"Book: {book}\n\nPassage where I stopped:\n\n{extracted}\n\nWhere am I in the story?"}
    ])

    return jsonify({"status": "ok", "book": book, "summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=3000)
