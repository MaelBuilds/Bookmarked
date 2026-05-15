# Multilingual support — FE architecture & backend contract

**Purpose:** Bootstrap a future conversation about internationalization (i18n) for Bookmarked after the planned frontend migration to **React + Panda CSS (likely Vite)**. Backend remains **Flask** (`/ocr`, `/identify`, `/summarize`) with **GitHub Models** for the LLM. Product: spoiler-free book catch-up; **librarian** voice in copy.

---

## 1. Goal & scope

| Area | In scope | Out of scope / later |
|------|----------|----------------------|
| **UI strings** | All user-visible labels, buttons, errors, empty states, onboarding | Marketing site (if split later) |
| **Date / number formatting** | `Intl.DateTimeFormat`, `Intl.NumberFormat` (or library wrappers) | Heavy locale-specific business rules |
| **Layout direction** | Design tokens that tolerate RTL (logical properties in Panda where possible) | Full RTL QA and mirrored layouts (optional phase) |
| **LLM prompts & responses** | User-chosen **output language** for summaries and assistant-facing copy | — |
| **OCR / grounding text** | Treat page text as **source language** from the book | Auto-translating photographed text for grounding **unless** product explicitly adds that feature |

**Principle:** The model answers *about* the book in the user’s language; it does not silently “normalize” the user’s page image text into another language for identification or summarization unless that is an explicit, tested product decision.

---

## 2. Architecture options (2–3) & tradeoffs

| Dimension | **(A) react-i18next + JSON namespaces** | **(B) Lingui (compile-time)** | **(C) Minimal JSON + React context** |
|-----------|----------------------------------------|-------------------------------|----------------------------------------|
| **DX** | Mature ecosystem, docs, DevTools patterns | Excellent for static strings; macros/CLI | Fastest to spike; you own edge cases |
| **Bundle / lazy load** | Good with `import()` per namespace/locale | Excellent tree-shaking after compile | Manual chunking per locale file |
| **Interpolation / plurals** | Built-in (`t('key', { count })`) | Strong ICU message format | DIY or small helper |
| **Type safety** | Optional plugins / codegen | Strong with compile step | Weak unless you add codegen |
| **Solo MVP overhead** | Medium (one dependency, clear patterns) | Medium–high (build pipeline, extraction) | Low upfront, refactor cost if scope grows |
| **Panda CSS** | No conflict; wrap app in `I18nextProvider` | No conflict | No conflict |

**Default recommendation (solo MVP): (A) react-i18next + JSON namespaces**

- **Why:** Balances speed with a path to lazy-loaded locales, pluralization, and future translators/PM edits without inventing a framework.
- **When to prefer (B):** If copy churn is high and you want enforced extraction + minimal runtime. Worth revisiting post–MVP if localization becomes a release gate.
- **When to prefer (C):** Only for a very short prototype; risk of outgrowing it when flows multiply.

---

## 3. Locale model

### Sources of truth (pick one primary; others as fallbacks)

| Approach | Pros | Cons |
|----------|------|------|
| **`Accept-Language` (browser)** | Zero UI; good first visit | Wrong for expats; changes with browser |
| **Explicit user setting** | Clear intent; stable | Needs UI + persistence |
| **URL prefix (`/en`, `/fr`)** | Shareable links; SEO if public | Router + static hosting story; more moving parts |

**Practical default for Bookmarked MVP:** **explicit user setting** stored in **`localStorage`** (key e.g. `bookmarked.locale`), initialized once from `navigator.language` / `Accept-Language` if unset. Optionally mirror locale in a **query param** on first load for support links (`?lang=fr`) without committing to full URL-prefix routing.

**Later (account):** Persist locale server-side when auth exists; treat `localStorage` as cache until then.

### Interaction with Flask

- Browser → Flask: optional header **`X-Locale: fr-FR`** or query **`?locale=fr`** on API calls (pick one convention and document it).
- **Vite dev proxy:** Ensure forwarded headers or query params reach Flask unchanged.
- **Summarize:** FE must send the effective locale (or BCP-47 language tag) so the server can set `output_language` / prompt instructions consistently.

---

## 4. Backend contract

### Request shape

| Endpoint | Suggested parameter | Notes |
|----------|---------------------|--------|
| **`POST /summarize`** | `locale` or `output_language` (string, BCP-47 preferred: `en`, `fr`, `en-US`) | System / developer message: “Respond in {language}.” Librarian tone preserved *in that language*. |
| **`POST /identify`** (if user-facing explanations/errors) | Same optional field | Only if responses include natural language beyond structured IDs. |
| **`POST /ocr`** | Usually **omit** locale for model behavior | OCR output = text as on page; locale irrelevant unless post-processing. |

### Prompt engineering notes

- **System instruction language:** Either keep English for maintainability and add *“Always respond to the user in {output_language}”* or author system prompts bilingually—team preference; the critical part is the **user-visible** reply language.
- **Grounding:** Pass photographed / OCR text **verbatim** (source script/language). Do not translate for matching unless product adds “translate page for identify” as a separate, labeled mode.
- **Errors:** Return a stable `code` (machine) + optional `message` in requested locale, or return English `message` + let FE map `code` → localized string (often simpler for MVP).

---

## 5. FE implementation sketch (React + Panda + i18next)

### Provider placement

- **`I18nextProvider`** (or `initReactI18next` at module level) at app root in `main.tsx` / `App.tsx`, **above** Panda’s `styled`/`Recipe` tree so hooks work everywhere.
- Initialize `i18next` with `fallbackLng: 'en'`, `supportedLngs` explicit list.

### Namespace layout

| File | Contents |
|------|----------|
| `locales/en/common.json` | Buttons, nav, generic errors |
| `locales/en/flows.json` | Capture → identify → summarize steps |
| (future) `locales/en/legal.json` | Privacy, terms |

Use **`import()`** per language pack: `i18next.addResourceBundle(lng, ns, await import(\`./locales/${lng}/common.json\`))` pattern or dynamic `import()` in a small loader.

### Panda CSS

- Prefer **logical properties** (`marginInlineStart`, `paddingInline`, `textAlign: 'start'`) in recipes and styles to reduce RTL pain later.
- No Panda-specific i18n requirement; keep styling and copy separate.

### Lazy-loading locales

- On app boot: load `common` for `fallbackLng` + user’s `lng`.
- On route or flow change: `loadNamespaces(['flows'])` before first paint of that flow if bundle size matters.

---

## 6. Validation checklist

| # | Test | Pass criteria |
|---|------|----------------|
| 1 | Switch locale in settings | UI updates without full reload; persists after refresh |
| 2 | First visit, browser `fr-FR` | Sensible default; can override |
| 3 | `/summarize` with `output_language=fr` | Summary body in French; tone still “librarian” |
| 4 | Mixed-language book (e.g. quoted Latin) | Summary language stable; quotes not “helpfully” translated away unless specified |
| 5 | API error (`500`, rate limit) | User sees localized **or** code-mapped message, not raw stack |
| 6 | Unsupported locale (`zz`) | Falls back to `en`; no crash |
| 7 | OCR payload | Still original script; identify still works |

**Edge cases:** RTL with camera UI; long German strings breaking layouts; locale while offline (cached bundles).

---

## 7. Open decisions (PM / next conversation)

- **Primary locale mechanism:** `localStorage` only vs URL prefix vs hybrid for MVP.
- **Exact API field name:** `locale` vs `output_language`; required vs optional default.
- **Identify endpoint:** Does any natural-language field need localization, or FE-only?
- **Tone / copy:** Who owns translated “librarian” strings—human review per language vs ship with model-assisted draft?
- **OCR / identify:** Any future feature to **translate** page text for users (explicit toggle)?
- **Supported language list:** Ship with `en` + ? ; regional variants (`pt` vs `pt-BR`).
- **Error strategy:** Localized server messages vs `code` + FE mapping only.
- **RTL:** In scope for v1 or explicitly deferred; any camera/mirror UX research needed.

---

## Next steps (for a new agent)

1. Align on **default recommendation (A)** or document a switch to Lingui.
2. Add **`output_language` (or `locale`)** to OpenAPI / README and Flask handlers for `/summarize` (+ `/identify` if applicable).
3. Wire Vite + React root with **i18next** + lazy `common` / `flows` bundles.
4. Run through **validation checklist** before calling multilingual support “done” for MVP.
