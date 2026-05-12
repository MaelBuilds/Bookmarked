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


# ===========================================================================
# MUST-HAVE: Input validation
# ===========================================================================

class TestOCRValidation:
    def test_missing_image(self, client):
        r = client.post("/ocr", json={})
        assert r.status_code == 400
        assert "No image" in r.get_json()["error"]

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
        assert "No text" in r.get_json()["error"]

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

    def _make_http_error(self, code):
        return urllib.error.HTTPError(
            url="https://example.com", code=code, msg="",
            hdrs=MagicMock(), fp=io.BytesIO(b"{}"),
        )

    def test_401_invalid_token(self, client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(401)):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 401
        assert "token" in r.get_json()["error"].lower()

    def test_429_rate_limited(self, client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(429)):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 429
        assert "rate limit" in r.get_json()["error"].lower()

    def test_500_api_down(self, client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(500)):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502
        assert "down" in r.get_json()["error"].lower()

    def test_503_unavailable(self, client):
        with patch("server.urllib.request.urlopen", side_effect=self._make_http_error(503)):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502

    def test_network_unreachable(self, client):
        with patch("server.urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502
        assert "reach" in r.get_json()["error"].lower()

    def test_timeout(self, client):
        with patch("server.urllib.request.urlopen", side_effect=TimeoutError()):
            r = client.post("/identify", json={"text": "some text"})
        assert r.status_code == 502

    def test_malformed_json_response(self, client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"unexpected": "shape"}'

        with patch("server.urllib.request.urlopen", return_value=mock_resp), \
             patch("server.json.load", return_value={"unexpected": "shape"}):
            r = client.post("/identify", json={"text": "some text"})
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
        with _mock_gpt("summary") as mock:
            client.post("/summarize", json={
                "text": "passage", "book": "Dune by Frank Herbert", "mode": "light"
            })
        messages = mock.call_args[0][0]
        system = messages[0]["content"]
        assert "4-6 sentences" in system
        assert "three sections" not in system

    def test_full_mode_uses_full_prompt(self, client):
        with _mock_gpt("summary") as mock:
            client.post("/summarize", json={
                "text": "passage", "book": "Dune by Frank Herbert", "mode": "full"
            })
        messages = mock.call_args[0][0]
        system = messages[0]["content"]
        assert "three sections" in system
        assert "4-6 sentences" not in system

    def test_default_mode_is_light(self, client):
        with _mock_gpt("summary") as mock:
            client.post("/summarize", json={
                "text": "passage", "book": "Dune by Frank Herbert"
            })
        messages = mock.call_args[0][0]
        assert "4-6 sentences" in messages[0]["content"]

    def test_user_message_includes_book_and_passage(self, client):
        with _mock_gpt("summary") as mock:
            client.post("/summarize", json={
                "text": "the passage text", "book": "Dune by Frank Herbert"
            })
        user_msg = mock.call_args[0][0][1]["content"]
        assert "Dune by Frank Herbert" in user_msg
        assert "the passage text" in user_msg

    def test_spoiler_wall_in_both_prompts(self):
        from server import PROMPT_LIGHT, PROMPT_FULL
        assert "No spoilers beyond" in PROMPT_LIGHT
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
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-123")
        import importlib, server
        importlib.reload(server)
        assert server._ENV_TOKEN == "env-token-123"

    def test_loads_from_dotenv_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("GITHUB_TOKEN=file-token-456\n")
        monkeypatch.setattr("server.os.path.dirname", lambda _: str(tmp_path))
        monkeypatch.setattr("server.__file__", str(tmp_path / "server.py"))
        import importlib, server
        importlib.reload(server)
        assert server._ENV_TOKEN == "file-token-456"

    def test_raises_when_no_token(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr("server.os.path.dirname", lambda _: str(tmp_path))
        monkeypatch.setattr("server.__file__", str(tmp_path / "server.py"))
        import importlib, server
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN not set"):
            importlib.reload(server)


# ===========================================================================
# SHOULD-HAVE: Happy paths (routes return expected shapes)
# ===========================================================================

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
