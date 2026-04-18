# TODO — Prior to deploying

## Security

- [ ] **Rate limiting** — Add `flask-limiter` to cap requests per IP (e.g. 20/day on `/ocr`). Without this, anyone can drain the GitHub Models quota.
- [ ] **Auth** — Decide on access model: invite-only beta (token-gated), or open with per-user GitHub token (BYOT). Currently no auth at all.
- [ ] **HTTPS** — Mandatory before sharing any public URL. Railway/Render handle this automatically.
- [ ] **CORS** — Lock down `Access-Control-Allow-Origin` to your domain once deployed. Currently unrestricted.

## Infra

- [ ] **Choose hosting** — Railway or Render both work with Flask out of the box. Railway has a free tier.
- [ ] **Set env vars on host** — `GITHUB_TOKEN` and `FLASK_DEBUG=false` in the platform's env var UI. No `.env` file on the server.
- [ ] **Procfile or start command** — Add `web: python server.py` or configure the platform's start command. Railway auto-detects Flask.

## Product

- [ ] **Prompt last-sentence editorializing** — Still occasionally adds dramatic framing on the last sentence. Needs one more tightening pass before public.
- [ ] **Book not found UX** — Currently shows a bare error message. Should guide the user to try the cover/spine photo fallback more clearly.
- [ ] **Mobile test** — Test camera capture end-to-end on a real phone before launch.
- [ ] **Error messages** — Replace "Something went wrong. Please try again." with specific, actionable messages (rate limit vs. server error vs. bad image).

## Nice to have (not blocking)

- [ ] Demo GIF or screenshot in README
- [ ] `requirements.txt` — currently undocumented; add so others can `pip install -r requirements.txt`
