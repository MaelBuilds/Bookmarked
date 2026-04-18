# Bookmarked

Take a photo of the page you're on. Get a spoiler-free catch-up summary — no backtracking, no accidental reveals.

---

## The problem

You put a book down for three weeks. Google tells you what happens in chapter 40. Re-reading feels like homework. Bookmarked anchors to exactly where you are and tells you only what you've already read.

## How it works

1. Upload or drag a photo of your current page
2. The app reads the text, identifies the book, and generates a summary
3. You get: who the character is, the stakes of their situation, and what just happened — nothing beyond your page

## Stack

- **Backend:** Python / Flask — three endpoints: `/ocr`, `/identify`, `/summarize`
- **Model:** GPT-4o-mini via [GitHub Models](https://github.com/marketplace/models)
- **Frontend:** Vanilla HTML/CSS/JS — no framework, no build step
- **Design:** Libby-inspired warm gradient (`#F14D3A → #FFE7DD`)

## Running locally

**Prerequisites:** Python 3, Flask, a GitHub personal access token with Models access.

```bash
git clone https://github.com/MaelBuilds/Bookmarked.git
cd Bookmarked
pip3 install flask flask-cors requests python-dotenv
```

Create a `.env` file with your GitHub token:

```
YOUR_GITHUB_TOKEN_HERE
```

Start the server:

```bash
nohup python3 server.py > server.log 2>&1 &
```

Open [http://localhost:3000](http://localhost:3000).

## Status

Working MVP — tested on *Project Hail Mary* by Andy Weir. Local only. Cloud deployment not yet set up.

**Known limitations:**
- Very obscure or self-published books may not be identified reliably
- Dialogue-heavy or very short passages may not anchor precisely
- GitHub Models free tier has rate limits — occasional 429s on heavy use
