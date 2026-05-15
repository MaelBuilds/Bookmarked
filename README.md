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
- **Frontend:** React + TypeScript + [Panda CSS](https://panda-css.com/) (Vite build in `frontend/`; Flask serves `frontend/dist`). All UI lives in `frontend/` — there is no separate root HTML app.

---

## Running locally

**Prerequisites:** Python 3, **Node.js 20+** (for the UI build), and a GitHub personal access token with Models access.

### Production-style (single server)

Build the SPA once, then run Flask (serves the API and static UI on the same port):

```bash
git clone https://github.com/MaelBuilds/Bookmarked.git
cd Bookmarked
pip3 install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
cp .env.example .env
# Edit .env and add your GitHub token
python3 server.py
```

Open [http://localhost:3000](http://localhost:3000). If `frontend/dist` is missing, `/` returns instructions to run the build.

### Frontend development (hot reload + API proxy)

Terminal 1 — Flask on port 3000:

```bash
python3 server.py
```

Terminal 2 — Vite on port 5173 (proxies `/ocr`, `/identify`, `/summarize`, `/assets` to Flask):

```bash
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Override the Flask origin if needed: `VITE_FLASK_ORIGIN=http://127.0.0.1:3000`.

### Deploying (Railway, Fly, etc.)

The host **build** step must compile the SPA before `python server.py` starts, for example:

`cd frontend && npm ci && npm run build`

Then run the Procfile / start command from the **repo root** so `frontend/dist` exists. Same-origin `/ocr`, `/identify`, `/summarize` require no CORS changes.

---

## Status

Working MVP — tested on *Project Hail Mary* by Andy Weir. Local only.

**Known limitations:**
- Very obscure or self-published books may not identify reliably
- Very short or dialogue-only passages may not anchor precisely
- GitHub Models free tier has rate limits — occasional slowdowns on heavy use
