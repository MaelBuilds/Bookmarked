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

**Prerequisites:** Python 3, **Node.js 20+** (for the UI), and a GitHub personal access token with Models access.

```bash
git clone https://github.com/MaelBuilds/Bookmarked.git
cd Bookmarked
pip install -r requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env
# Edit .env and add your GitHub token
```

`AI_PROVIDER=github` uses GitHub Models. Use `AI_PROVIDER=fake` only for local automation and tests.

### Frontend development (hot reload — use this while editing React)

**Editing React? Open [http://localhost:5173](http://localhost:5173), not :3000.** Port 3000 serves the last `npm run build`; changes in `frontend/src` will not appear there until you build again.

**Terminal 1** — API (repo root):

```bash
python server.py
```

**Terminal 2** — UI with hot reload:

```bash
cd frontend && npm run dev
```

Vite proxies `/ocr`, `/identify`, `/summarize`, and `/assets` to Flask on port 3000. Override the Flask origin if needed: `VITE_FLASK_ORIGIN=http://127.0.0.1:3000`.

**Windows one-launcher** (optional): from the repo root, `.\scripts\dev.ps1` starts Flask in a new window and Vite in the current terminal.

First `npm install` in `frontend/` runs Panda codegen (`frontend/styled-system/`, gitignored). You do **not** need `npm run build` for everyday UI tweaks.

### Production-style (single server)

Build the SPA once, then run Flask (serves the API and static UI on the same port). Use this to smoke-test the deploy bundle or when you only want one process:

```bash
cd frontend && npm run build && cd ..
python server.py
```

Open [http://localhost:3000](http://localhost:3000). If `frontend/dist` is missing, `/` returns instructions to run the build.

### Deploying (Railway, Fly, etc.)

Before deploying, run the deterministic pre-deploy gate from the repo root:

```bash
./scripts/predeploy.ps1
```

This runs backend tests with `AI_PROVIDER=fake`, then builds the frontend.

The host **build** step must compile the SPA before `python server.py` starts, for example:

`cd frontend && npm ci && npm run build`

Then run the Procfile / start command from the **repo root** so `frontend/dist` exists. Same-origin `/ocr`, `/identify`, `/summarize` require no CORS changes.

Railway should run with `AI_PROVIDER=github` and `GITHUB_TOKEN` stored as platform secrets. The app refuses to start on Railway with `AI_PROVIDER=fake`.

### Testing AI paths

Default tests should avoid live AI calls:

```bash
AI_PROVIDER=fake pytest
```

Fake mode returns deterministic OCR, identify, and summarize responses so automation can verify the app flow without spending quota.

Live model checks are explicit and narrow:

```bash
AI_PROVIDER=github RUN_LIVE_AI_TESTS=true pytest -m live_ai
```

Use live smoke tests before important releases only. They verify token/API availability, not full summary quality.

---

## Status

Working MVP — tested on *Project Hail Mary* by Andy Weir. Local only.

**Known limitations:**
- Very obscure or self-published books may not identify reliably
- Very short or dialogue-only passages may not anchor precisely
- GitHub Models free tier has rate limits — occasional slowdowns on heavy use
