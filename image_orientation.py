"""Auto-upright book page photos before OCR (EXIF + 180° layout heuristic)."""

import base64
import io

from PIL import Image, ImageOps

_ANALYSIS_LONG_EDGE = 512
_INK_THRESHOLD = 200
# Ignore 180° flip when top/bottom ink difference is tiny (symmetric pages).
_FLIP_MIN_SCORE_DELTA = 500


def _ink_profile(gray):
    """Row ink variance and bottom-minus-top mass (page numbers often sit low on the page)."""
    w, h = gray.size
    px = gray.load()
    rows = []
    for y in range(h):
        s = 0
        for x in range(w):
            if px[x, y] < _INK_THRESHOLD:
                s += 1
        rows.append(s)
    if h < 3:
        return 0.0, 0.0
    mean = sum(rows) / h
    var = sum((r - mean) ** 2 for r in rows) / h if mean else 0.0
    third = h // 3
    top = sum(rows[:third])
    bottom = sum(rows[2 * third :])
    return var, bottom - top


def _downscale_for_analysis(img):
    long_edge = max(img.size)
    if long_edge <= _ANALYSIS_LONG_EDGE:
        return img
    scale = _ANALYSIS_LONG_EDGE / long_edge
    return img.resize(
        (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
        Image.Resampling.BILINEAR,
    )


def choose_upright_rotation(img):
    """Return clockwise correction in degrees: 0 or 180."""
    work = _downscale_for_analysis(img)
    if work.mode != 'L':
        work = work.convert('L')

    _, bt_0 = _ink_profile(work)
    _, bt_180 = _ink_profile(work.rotate(-180, expand=True))

    if abs(bt_180 - bt_0) < _FLIP_MIN_SCORE_DELTA:
        return 0
    return 180 if bt_180 > bt_0 else 0


def normalize_page_image_bytes(raw):
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    angle = choose_upright_rotation(img)
    if angle:
        img = img.rotate(-angle, expand=True)
    return img.convert('RGB')


def normalize_page_image_b64(b64_string):
    raw = base64.b64decode(b64_string)
    img = normalize_page_image_bytes(raw)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=92, optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii')
