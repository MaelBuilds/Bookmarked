# Bookmarked 📔

---

Baby's crying, something on the stove, your stop on the subway — there are a thousand reasons to drop your book right where you are. And a thousand more not to pick it back up for three weeks. Until you do, and you're back staring at the page with no idea who this person is or why you should care.

So you Google it. And now you know how it ends.

**There's a better way.**

Photo your page. Bookmarked reads where you stopped and catches you up — who's there, what's at stake, what just happened. Nothing beyond your page. No spoilers, no re-reading, no ruined endings.

---

## How it works

1. Take a photo of your current page
2. The app identifies the book and reads the passage
3. You get a spoiler-free catch-up, anchored to exactly where you stopped

---

## Stack

- **Backend:** Python / Flask — `/ocr`, `/identify`, `/summarize`
- **Model:** GPT-4o-mini via [GitHub Models](https://github.com/marketplace/models)
- **Frontend:** Vanilla HTML/CSS/JS — no framework, no build step

---

## Running locally

**Prerequisites:** Python 3 and a GitHub personal access token with Models access.

```bash
git clone https://github.com/MaelBuilds/Bookmarked.git
cd Bookmarked
pip3 install flask flask-cors requests python-dotenv
cp .env.example .env
# Edit .env and add your GitHub token
python3 server.py
```

Open [http://localhost:3000](http://localhost:3000).

---

## Status

Working MVP — tested on *Project Hail Mary* by Andy Weir. Local only.

**Known limitations:**
- Very obscure or self-published books may not identify reliably
- Very short or dialogue-only passages may not anchor precisely
- GitHub Models free tier has rate limits — occasional slowdowns on heavy use
