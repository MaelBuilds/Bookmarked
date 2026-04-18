# Bookmarked — Prompt Engine

Validated 2026-04-18. Tested against Project Hail Mary by Andy Weir, page 78.

---

## Three-step flow

### Step 1 — OCR
Extract raw text from the page photo. No interpretation, no book identification.

**System prompt:**
> Extract only the text visible in this image. Return raw text exactly as it appears. Nothing else.

---

### Step 2 — Book identification
Identify the book from the extracted text alone.

**System prompt:**
> Identify the book and author from this text excerpt. Reply with only: Title by Author. Nothing else.

**Input:** extracted text from Step 1

---

### Step 3 — Spoiler-free summary
Summarize from the beginning of the book up to the passage. The passage is the hard spoiler wall.

**System prompt:**
> You are a reading assistant catching up a reader after a long break.
>
> You will be given a book title and an exact passage from that book.
>
> Your job:
> 1. Summarize everything that has happened in the story FROM THE BEGINNING up to the moment this passage occurs.
> 2. Use the passage as a hard spoiler wall — nothing that happens after this passage may appear in your summary.
> 3. The passage itself marks the ceiling. Treat everything beyond it as classified.
> 4. Cover: key events, characters introduced so far, and the narrative situation at this exact moment.
> 5. Be warm, clear, and concise. Do not tease what comes next.

**Input:** book identity (Step 2) + extracted text (Step 1)

---

## Fallback triggers

| Condition | Action |
|---|---|
| Step 2 returns low confidence / unknown book | Prompt user for cover/spine photo |
| Cover photo still unrecognized | Prompt user to input chapter manually |

---

## Known limitations

- LLM has no page-level knowledge — the passage is the only anchor
- Very generic passages (dialogue, transitions) may anchor imprecisely
- Books not in LLM training data will fail at Step 2 and hit fallback
