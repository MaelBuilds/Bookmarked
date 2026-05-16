"""One-off: test GITHUB_TOKEN against GitHub Models (no token printed)."""
import json
import os
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t, "env"
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if key.strip() == "GITHUB_TOKEN":
                    return val.strip(), "file"
    return None, "none"


def main():
    token, src = load_token()
    if not token:
        print("NO_TOKEN")
        return 1
    meta = {
        "source": src,
        "len": len(token),
        "has_outer_quotes": (
            (token.startswith('"') and token.endswith('"'))
            or (token.startswith("'") and token.endswith("'"))
        ),
        "has_edge_whitespace": token != token.strip(),
        "format": (
            "ghp"
            if token.startswith("ghp_")
            else ("github_pat" if token.startswith("github_pat_") else "other")
        ),
    }
    print("META", meta)
    payload = json.dumps(
        {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]}
    ).encode()
    req = urllib.request.Request(
        "https://models.inference.ai.azure.com/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("API_STATUS", r.status)
            return 0
    except urllib.error.HTTPError as e:
        print("API_STATUS", e.code)
        print("API_BODY", e.read()[:300])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
