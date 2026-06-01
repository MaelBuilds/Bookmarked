import base64
import io
import json
import os
import struct
import urllib.error
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_token(monkeypatch):
    """Ensure GITHUB_TOKEN is always available so the app can import."""
    if os.environ.get("RUN_LIVE_AI_TESTS", "").lower() == "true":
        return
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-fake")


@pytest.fixture()
def app():
    import importlib
    import server as srv
    importlib.reload(srv)
    srv.app.config["TESTING"] = True
    return srv.app


@pytest.fixture()
def client(app):
    return app.test_client()


def _mock_gpt(return_value="mocked response"):
    return patch("server.call_gpt", return_value=return_value)


def _reload_server(monkeypatch, provider="github", token="test-token-fake"):
    monkeypatch.setenv("AI_PROVIDER", provider)
    if token is None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    else:
        monkeypatch.setenv("GITHUB_TOKEN", token)
    import importlib
    import server as srv
    importlib.reload(srv)
    srv.app.config["TESTING"] = True
    return srv


# ---------------------------------------------------------------------------
# Helpers: minimal valid base64 for each image format
# ---------------------------------------------------------------------------

def _b64(raw_bytes: bytes) -> str:
    return base64.b64encode(raw_bytes).decode()


JPEG_BYTES = b'\xff\xd8\xff\xe0' + b'\x00' * 20
PNG_BYTES  = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
GIF_BYTES  = b'GIF89a' + b'\x00' * 20
WEBP_BYTES = b'RIFF' + struct.pack('<I', 0) + b'WEBP' + b'\x00' * 20
PDF_BYTES  = b'%PDF-1.4' + b'\x00' * 20
TEXT_BYTES = b'Hello, this is plain text, not an image at all'

FIXTURES_IDENTIFY = os.path.join(os.path.dirname(__file__), "fixtures", "identify")


def load_identify_fixture(name):
    path = os.path.join(FIXTURES_IDENTIFY, f"{name}.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def assert_valid_charlie_dahl_identify(book):
    """Published Charlie work by Dahl — not a character name as title."""
    book_lower = book.lower()
    assert "dahl" in book_lower, f"expected Dahl as author, got: {book!r}"
    title = book_lower.split(" by ")[0] if " by " in book_lower else book_lower
    if " par " in book_lower:
        title = book_lower.split(" par ")[0]
    assert "gloop" not in title, f"character name used as title: {book!r}"
    assert "august" not in title, f"character name used as title: {book!r}"
    assert "bouillon" not in title, f"OCR-adjacent word used as title: {book!r}"
    assert "charlie" in title or "chocolat" in title, (
        f"expected Charlie or chocolat in title, got: {book!r}"
    )


# ===========================================================================
# Identify hygiene (OCR preamble, suspect-title retry)
# ===========================================================================

class TestIdentifyHygiene:
    def test_clean_passage_strips_french_ocr_preamble(self):
        import server as srv
        raw = "Voici le texte extrait : Joufflu, bouffi, gourmand"
        assert srv._clean_passage_text(raw) == "Joufflu, bouffi, gourmand"


class TestCatalogGrounding:
    """Identify grounds the LLM guess against a real bibliographic catalog."""

    def test_parse_title_author_handles_by_and_par(self):
        import server as srv
        assert srv._parse_title_author("Dune by Frank Herbert") == (
            "Dune",
            "Frank Herbert",
        )
        assert srv._parse_title_author(
            "Charlie et la Chocolaterie par Roald Dahl"
        ) == ("Charlie et la Chocolaterie", "Roald Dahl")

    def test_title_overlap_matches_editions_but_not_unrelated(self):
        import server as srv
        assert srv._title_overlap(
            "Charlie and the Chocolate Factory",
            "Charlie and the Chocolate Factory: A Play",
        )
        assert not srv._title_overlap("Le Bouillon", "Charlie et la Chocolaterie")

    def test_identify_returns_canonical_title_from_catalog(self, client):
        with patch("server.call_gpt", return_value="charlie and the chocolate factory by r dahl"), \
             patch("server._catalog_enabled", return_value=True), \
             patch(
                 "server._catalog_lookup",
                 return_value="Charlie and the Chocolate Factory by Roald Dahl",
             ):
            r = client.post("/identify", json={"text": "...Augustus Gloop song..."})
        data = r.get_json()
        assert data["status"] == "ok"
        assert data["book"] == "Charlie and the Chocolate Factory by Roald Dahl"

    def test_identify_unverifiable_candidate_falls_back_to_needs_cover(self, client):
        with patch("server.call_gpt", return_value="Le Bouillon by Roald Dahl"), \
             patch("server._catalog_enabled", return_value=True), \
             patch("server._catalog_lookup", return_value=None):
            r = client.post("/identify", json={"text": "Joufflu, bouffi, gourmand"})
        assert r.get_json()["status"] == "needs_cover"

    def test_identify_forwards_passage_language_to_grounding(self, client):
        passage = load_identify_fixture("charlie-fr-gloop")  # French text
        with patch("server.call_gpt", return_value="Charlie et la Chocolaterie par Roald Dahl"), \
             patch("server._catalog_enabled", return_value=True), \
             patch(
                 "server._resolve_identification",
                 return_value="Charlie et la Chocolaterie by Roald Dahl",
             ) as resolve:
            r = client.post("/identify", json={"text": passage})
        assert r.get_json()["book"] == "Charlie et la Chocolaterie by Roald Dahl"
        assert resolve.call_args.args[1] == "fr"

    def test_identify_degrades_to_model_guess_when_catalog_unreachable(self, client):
        import server as srv
        with patch("server.call_gpt", return_value="Dune by Frank Herbert"), \
             patch("server._catalog_enabled", return_value=True), \
             patch("server._catalog_lookup", side_effect=srv._CatalogUnavailable()):
            r = client.post("/identify", json={"text": "The spice must flow"})
        data = r.get_json()
        assert data["status"] == "ok"
        assert data["book"] == "Dune by Frank Herbert"


class TestRecapPrompts:
    """Summarize prompts produce a chronological 'Previously on' recap, not a page description."""

    def test_light_prompt_is_chronological_recap(self):
        from server import PROMPT_LIGHT
        lower = PROMPT_LIGHT.lower()
        assert "previously on" in lower
        assert "protagonist" in lower
        assert "personnage principal" in lower or "main character" in lower
        assert "invent" in lower  # explicit no-invented-plot guard

    def test_full_prompt_is_chronological_recap(self):
        from server import PROMPT_FULL
        lower = PROMPT_FULL.lower()
        assert "how did the story arrive at this moment" in lower
        assert "spoiler wall" in lower
        assert "invent" in lower

    def test_build_summarize_includes_book_and_passage(self):
        import server as srv
        messages = srv.build_summarize_messages(
            "Charlie et la Chocolaterie by Roald Dahl",
            "Augustus song passage",
            "light",
            "fr",
            "French",
        )
        user = messages[1]["content"]
        assert "Charlie et la Chocolaterie by Roald Dahl" in user
        assert "Augustus song passage" in user


# ===========================================================================
# MUST-HAVE: Input validation
# ===========================================================================

class TestOCRValidation:
    def test_missing_image(self, client):
        r = client.post("/ocr", json={})
        assert r.status_code == 400
        data = r.get_json()
        assert data["code"] == "no_image"
        assert "No image" in data["error"]

    def test_empty_image(self, client):
        r = client.post("/ocr", json={"image": ""})
        assert r.status_code == 400

    def test_no_json_body(self, client):
        r = client.post("/ocr", content_type="application/json", data="{}")
        assert r.status_code == 400


class TestIdentifyValidation:
    def test_missing_text(self, client):
        r = client.post("/identify", json={})
        assert r.status_code == 400
        data = r.get_json()
        assert data["code"] == "no_text"
        assert "No text" in data["error"]

    def test_empty_text(self, client):
        r = client.post("/identify", json={"text": ""})
        assert r.status_code == 400

    def test_whitespace_only(self, client):
        r = client.post("/identify", json={"text": "   "})
        assert r.status_code == 400


class TestSummarizeValidation:
    def test_missing_text(self, client):
        r = client.post("/summarize", json={"book": "Dune by Frank Herbert"})
        assert r.status_code == 400
        assert "No text" in r.get_json()["error"]

    def test_missing_book(self, client):
        r = client.post("/summarize", json={"text": "some passage"})
        assert r.status_code == 400
        assert "No book" in r.get_json()["error"]

    def test_empty_book(self, client):
        r = client.post("/summarize", json={"text": "passage", "book": ""})
        assert r.status_code == 400

    def test_empty_text(self, client):
        r = client.post("/summarize", json={"text": "", "book": "Dune"})
        assert r.status_code == 400


# ===========================================================================
# MUST-HAVE: LLM error handling
# ===========================================================================

class TestLLMErrors:
    """call_gpt failures should return structured JSON errors, not stack traces."""

    @pytest.fixture()
    def github_client(self, monkeypatch):
        srv = _reload_server(monkeypatch, provider="github")
        return srv.app.test_client()

    def _make_http_error(self, code):
        return urllib.error.HTTPError(
            url="https://example.com", code=code, msg="",
            hdrs=MagicMock(), fp=io.BytesIO(b"{}"),
        )

    def test_401_invalid_token(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(401)):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 401
        assert "token" in r.get_json()["error"].lower()

    def test_429_rate_limited(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(429)):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 429
        assert "rate limit" in r.get_json()["error"].lower()

    def test_500_api_down(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(500)):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502
        assert "down" in r.get_json()["error"].lower()

    def test_503_unavailable(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(503)):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502

    def test_network_unreachable(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502
        assert "reach" in r.get_json()["error"].lower()

    def test_timeout(self, github_client):
        with patch("server.urllib.request.urlopen", side_effect=TimeoutError()):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502

    def test_malformed_json_response(self, github_client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"unexpected": "shape"}'

        with patch("server.urllib.request.urlopen", return_value=mock_resp), \
             patch("server.json.load", return_value={"unexpected": "shape"}):
            r = github_client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502
        assert "unexpected" in r.get_json()["error"].lower()


# ===========================================================================
# MUST-HAVE: Image format validation
# ===========================================================================

class TestImageFormats:
    """OCR route should accept JPEG/PNG/GIF/WEBP and reject everything else."""

    def test_accepts_jpeg(self, client):
        with _mock_gpt("extracted text"):
            r = client.post("/ocr", json={"image": _b64(JPEG_BYTES)})
        assert r.status_code == 200

    def test_accepts_png(self, client):
        with _mock_gpt("extracted text"):
            r = client.post("/ocr", json={"image": _b64(PNG_BYTES)})
        assert r.status_code == 200

    def test_accepts_gif(self, client):
        with _mock_gpt("extracted text"):
            r = client.post("/ocr", json={"image": _b64(GIF_BYTES)})
        assert r.status_code == 200

    def test_accepts_webp(self, client):
        with _mock_gpt("extracted text"):
            r = client.post("/ocr", json={"image": _b64(WEBP_BYTES)})
        assert r.status_code == 200

    def test_rejects_pdf(self, client):
        r = client.post("/ocr", json={"image": _b64(PDF_BYTES)})
        assert r.status_code == 400
        assert "format" in r.get_json()["error"].lower()

    def test_rejects_plain_text(self, client):
        r = client.post("/ocr", json={"image": _b64(TEXT_BYTES)})
        assert r.status_code == 400

    def test_rejects_garbage_base64(self, client):
        r = client.post("/ocr", json={"image": "!!!not-base64!!!"})
        assert r.status_code == 400
        assert "data" in r.get_json()["error"].lower()

    def test_rejects_truncated_base64(self, client):
        r = client.post("/ocr", json={"image": "AAAA"}),
        resp = client.post("/ocr", json={"image": "AA"})
        assert resp.status_code == 400


# ===========================================================================
# SHOULD-HAVE: Prompt construction
# ===========================================================================

class TestPromptConstruction:
    """Verify the correct system prompt is sent for each summary mode."""

    def test_light_mode_uses_light_prompt(self, client):
        with patch("server.detect_passage_language", return_value="en"):
            with _mock_gpt("summary") as mock:
                client.post("/summarize", json={
                    "text": "passage", "book": "Dune by Frank Herbert", "mode": "light"
                })
            messages = mock.call_args[0][0]
            system = messages[0]["content"]
            assert "4-6 sentences" in system
            assert "three sections" not in system
            assert "OUTPUT LANGUAGE: English only" in system

    def test_full_mode_uses_full_prompt(self, client):
        with patch("server.detect_passage_language", return_value="en"):
            with _mock_gpt("summary") as mock:
                client.post("/summarize", json={
                    "text": "passage", "book": "Dune by Frank Herbert", "mode": "full"
                })
            messages = mock.call_args[0][0]
            system = messages[0]["content"]
            assert "8-12 sentences" in system
            assert "4-6 sentences" not in system

    def test_default_mode_is_light(self, client):
        with patch("server.detect_passage_language", return_value="en"):
            with _mock_gpt("summary") as mock:
                client.post("/summarize", json={
                    "text": "passage", "book": "Dune by Frank Herbert"
                })
            messages = mock.call_args[0][0]
            assert "4-6 sentences" in messages[0]["content"]

    def test_user_message_includes_book_and_passage(self, client):
        with patch("server.detect_passage_language", return_value="en"):
            with _mock_gpt("summary") as mock:
                client.post("/summarize", json={
                    "text": "the passage text", "book": "Dune by Frank Herbert"
                })
            user_msg = mock.call_args[0][0][1]["content"]
            assert "Dune by Frank Herbert" in user_msg
            assert "the passage text" in user_msg

    def test_ui_locale_fallback_when_language_unknown(self, client):
        with patch("server.detect_passage_language", return_value=None):
            with _mock_gpt("summary") as mock:
                client.post("/summarize", json={
                    "text": "passage", "book": "Dune", "ui_locale": "fr"
                })
            system = mock.call_args[0][0][0]["content"]
            user = mock.call_args[0][0][1]["content"]
            assert "OUTPUT LANGUAGE: French only" in system
            assert "Où en suis-je" in user

    def test_ui_locale_fr_forces_french_even_for_english_passage(self, client):
        english = (
            "Jean Valjean knelt in the shadows. He wept for what he had done. "
            "The bishop had shown him mercy, and he could not forget it."
        )
        with _mock_gpt("Résumé.") as mock:
            client.post("/summarize", json={
                "text": english, "book": "Les Misérables", "ui_locale": "fr"
            })
        system = mock.call_args[0][0][0]["content"]
        user = mock.call_args[0][0][1]["content"]
        assert "OUTPUT LANGUAGE: French only" in system
        assert "Où en suis-je" in user

    def test_summarize_response_includes_output_language_and_version(self, client):
        with patch("server.detect_passage_language", return_value="en"):
            with _mock_gpt("summary"):
                r = client.post("/summarize", json={
                    "text": "passage", "book": "Dune", "ui_locale": "fr"
                })
        data = r.get_json()
        assert data["output_language"] == "fr"
        assert data["api_version"] == "multilingual-2"

    def test_parse_lang_code_handles_verbose_model_reply(self):
        from server import parse_lang_code
        assert parse_lang_code("The language is French (fr)") == "fr"
        assert parse_lang_code("english") == "en"

    def test_spoiler_wall_in_both_prompts(self):
        from server import PROMPT_LIGHT, PROMPT_FULL
        assert "spoiler wall" in PROMPT_LIGHT
        assert "spoiler wall" in PROMPT_FULL


# ===========================================================================
# SHOULD-HAVE: Rate limiter
# ===========================================================================

class TestRateLimiter:
    def test_ocr_rate_limit_per_minute(self, app):
        app.config["TESTING"] = False  # rate limiter is disabled in TESTING mode
        c = app.test_client()

        with _mock_gpt("text"):
            for i in range(5):
                r = c.post("/ocr", json={"image": _b64(JPEG_BYTES)})
                assert r.status_code == 200, f"Request {i+1} failed unexpectedly"

            r = c.post("/ocr", json={"image": _b64(JPEG_BYTES)})
            assert r.status_code == 429


# ===========================================================================
# SHOULD-HAVE: Token loading
# ===========================================================================

class TestLoadToken:
    def test_loads_from_env_var(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "github")
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-123")
        import importlib, server
        importlib.reload(server)
        assert server._ENV_TOKEN == "env-token-123"

    def test_loads_from_dotenv_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AI_PROVIDER", "github")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("GITHUB_TOKEN=file-token-456\n")
        monkeypatch.setattr("server.os.path.dirname", lambda _: str(tmp_path))
        monkeypatch.setattr("server.__file__", str(tmp_path / "server.py"))
        import importlib, server
        importlib.reload(server)
        assert server._ENV_TOKEN == "file-token-456"

    def test_raises_when_no_token(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AI_PROVIDER", "github")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr("server.os.path.dirname", lambda _: str(tmp_path))
        monkeypatch.setattr("server.__file__", str(tmp_path / "server.py"))
        import importlib, server
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN not set"):
            importlib.reload(server)


# ===========================================================================
# SHOULD-HAVE: Happy paths (routes return expected shapes)
# ===========================================================================

class TestHealth:
    def test_health_html_for_browsers(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert b"multilingual-2" in r.data
        assert b"text/html" in r.content_type.encode()

    def test_health_json_with_format_param(self, client):
        r = client.get("/health?format=json")
        assert r.status_code == 200
        data = r.get_json()
        assert data["api_version"] == "multilingual-2"
        assert data["ai_provider"] in {"github", "fake"}
        assert "output_language" in data["summarize_response_fields"]


class TestHappyPaths:
    def test_identify_found(self, client):
        with _mock_gpt("Dune by Frank Herbert"):
            r = client.post("/identify", json={"text": "He is the Kwisatz Haderach"})
        data = r.get_json()
        assert data["status"] == "ok"
        assert data["book"] == "Dune by Frank Herbert"

    def test_identify_unknown(self, client):
        with _mock_gpt("UNKNOWN"):
            r = client.post("/identify", json={"text": "random text"})
        data = r.get_json()
        assert data["status"] == "needs_cover"

    def test_identify_debug_payload(self, client, monkeypatch):
        import server as srv
        monkeypatch.setenv("BOOKMARKED_DEBUG", "1")
        passage = load_identify_fixture("charlie-fr-gloop")
        cleaned_len = len(srv._clean_passage_text(passage))
        with _mock_gpt("Charlie et la Chocolaterie by Roald Dahl"):
            r = client.post("/identify", json={"text": passage})
        data = r.get_json()
        assert data["status"] == "ok"
        assert data["debug"]["text_len"] == cleaned_len
        assert "Auguste" in data["debug"]["text_preview"]
        assert data["debug"]["identify_raw"] == "Charlie et la Chocolaterie by Roald Dahl"
        assert data["debug"]["gpt_cache_hit"] is False

    def test_identify_debug_omitted_by_default(self, client, monkeypatch):
        monkeypatch.delenv("BOOKMARKED_DEBUG", raising=False)
        with _mock_gpt("Dune by Frank Herbert"):
            r = client.post("/identify", json={"text": "sample"})
        assert "debug" not in r.get_json()

    def test_summarize_returns_summary(self, client):
        with _mock_gpt("Paul Atreides arrives on Arrakis..."):
            r = client.post("/summarize", json={
                "text": "passage", "book": "Dune", "mode": "light"
            })
        assert "summary" in r.get_json()

    def test_ocr_returns_text(self, client):
        with _mock_gpt("The spice must flow"):
            r = client.post("/ocr", json={"image": _b64(JPEG_BYTES)})
        assert r.get_json()["text"] == "The spice must flow"


# ===========================================================================
# SHOULD-HAVE: Fake AI provider for automation
# ===========================================================================

class TestFakeAIProvider:
    def test_fake_provider_routes_keep_shapes_and_skip_network(self, monkeypatch):
        srv = _reload_server(monkeypatch, provider="fake", token=None)
        c = srv.app.test_client()

        with patch("server.urllib.request.urlopen") as urlopen:
            ocr = c.post("/ocr", json={"image": _b64(JPEG_BYTES)})
            assert ocr.status_code == 200
            assert "text" in ocr.get_json()

            identify = c.post("/identify", json={"text": ocr.get_json()["text"]})
            assert identify.status_code == 200
            assert identify.get_json() == {
                "status": "ok",
                "book": "Dune by Frank Herbert",
            }

            summarize = c.post("/summarize", json={
                "text": ocr.get_json()["text"],
                "book": identify.get_json()["book"],
                "mode": "light",
                "ui_locale": "en",
            })
            assert summarize.status_code == 200
            data = summarize.get_json()
            assert data["summary"]
            assert data["output_language"] == "en"
            assert data["api_version"] == "multilingual-2"

        urlopen.assert_not_called()

    def test_fake_provider_supports_unknown_book_scenario(self, monkeypatch):
        srv = _reload_server(monkeypatch, provider="fake", token=None)
        c = srv.app.test_client()

        r = c.post("/identify", json={"text": "unknown passage needs_cover"})
        assert r.status_code == 200
        assert r.get_json() == {"status": "needs_cover"}

    def test_fake_provider_health_metadata(self, monkeypatch):
        srv = _reload_server(monkeypatch, provider="fake", token=None)
        c = srv.app.test_client()

        r = c.get("/health?format=json")
        assert r.status_code == 200
        assert r.get_json()["ai_provider"] == "fake"

    def test_fake_provider_does_not_require_github_token(self, monkeypatch):
        srv = _reload_server(monkeypatch, provider="fake", token=None)
        assert srv.AI_PROVIDER == "fake"
        assert srv._ENV_TOKEN is None


# ===========================================================================
# EXPLICIT ONLY: Live AI smoke test
# ===========================================================================

class TestLiveAISmoke:
    @pytest.mark.live_ai
    def test_live_identify_smoke(self, monkeypatch):
        if os.environ.get("RUN_LIVE_AI_TESTS", "").lower() != "true":
            pytest.skip("Set RUN_LIVE_AI_TESTS=true to call the live model")
        if not os.environ.get("GITHUB_TOKEN"):
            pytest.skip("GITHUB_TOKEN is required for live AI smoke tests")

        srv = _reload_server(monkeypatch, provider="github", token=os.environ["GITHUB_TOKEN"])
        c = srv.app.test_client()

        r = c.post("/identify", json={
            "text": "Paul Atreides stood on Arrakis, where the spice shaped the fate of great houses."
        })
        assert r.status_code == 200
        assert "status" in r.get_json()

    @pytest.mark.live_ai
    def test_live_identify_charlie_fr_not_character_title(self, monkeypatch):
        if os.environ.get("RUN_LIVE_AI_TESTS", "").lower() != "true":
            pytest.skip("Set RUN_LIVE_AI_TESTS=true to call the live model")
        if not os.environ.get("GITHUB_TOKEN"):
            pytest.skip("GITHUB_TOKEN is required for live AI smoke tests")

        srv = _reload_server(monkeypatch, provider="github", token=os.environ["GITHUB_TOKEN"])
        c = srv.app.test_client()
        passage = load_identify_fixture("charlie-fr-gloop-ocr-preamble")

        r = c.post("/identify", json={"text": passage})
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok", data
        assert_valid_charlie_dahl_identify(data["book"])
