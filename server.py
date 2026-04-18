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
        {"role": "system", "content": """You are a reading assistant catching up a reader after a long break.
You will be given a book title and an exact passage from that book.
Your job:
1. Summarize everything that has happened FROM THE BEGINNING up to the moment this passage occurs.
2. Use the passage as a hard spoiler wall — nothing after it may appear.
3. Cover: key events, characters introduced, and the narrative situation at this exact moment.
4. Be warm, clear, and concise. Do not tease or foreshadow what comes next."""},
        {"role": "user", "content": f"Book: {book}\n\nPassage where I stopped:\n\n{extracted}\n\nCatch me up from the beginning to exactly this point."}
    ])

    return jsonify({"status": "ok", "book": book, "summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=3000)
