"""Run orientation fix + OCR on a local image file (uses GITHUB_TOKEN from .env)."""
import argparse
import base64
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image

from image_orientation import choose_upright_rotation, normalize_page_image_b64


def _load_dotenv():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Path to page photo")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BOOKMARKED_API_URL", "http://127.0.0.1:3000"),
    )
    parser.add_argument("--via-server", action="store_true", help="POST /ocr instead of direct call_gpt")
    args = parser.parse_args()

    path = os.path.abspath(args.image)
    if not os.path.isfile(path):
        print(f"Not found: {path}", file=sys.stderr)
        raise SystemExit(1)

    raw = open(path, "rb").read()
    img = Image.open(io.BytesIO(raw))
    angle = choose_upright_rotation(img)
    print(f"Auto-rotation: {angle}°" if angle else "Auto-rotation: none (already upright)")

    b64 = base64.b64encode(raw).decode("ascii")
    normalized = normalize_page_image_b64(b64)
    if normalized != b64:
        print("Image normalized before OCR (EXIF and/or 180° correction).")
    else:
        print("No normalization changes.")

    if args.via_server:
        body = json.dumps({"image": b64}).encode("utf-8")
        req = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/ocr",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(e.read().decode(), file=sys.stderr)
            raise SystemExit(1)
        text = data.get("text", "")
    else:
        _load_dotenv()
        import server as srv

        if srv.AI_PROVIDER == "fake":
            print("AI_PROVIDER=fake — set github in .env for live OCR.", file=sys.stderr)
            raise SystemExit(1)
        text = srv.call_gpt([
            {"role": "system", "content": (
                "Extract only the text visible in this image. Return raw text exactly as it appears. "
                "No commentary, labels, or preamble (do not write e.g. 'Here is the text'). Nothing else."
            )},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract the text from this page."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{normalized}"}},
            ]},
        ])
        text = srv._clean_passage_text(text)

    preview = text[:600] + ("…" if len(text) > 600 else "")
    print(f"\nOCR ({len(text)} chars):\n{preview}")


if __name__ == "__main__":
    main()
