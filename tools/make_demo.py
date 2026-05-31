# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""Generate assets/ix-demo.gif — the structural form: three readings (ast-grep ×
grep × meaning) glue at one location, R climbs to 1.00. Lab design language.
Reproducible: `python3 tools/make_demo.py`."""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 880, 400
BG = (249, 246, 238); INK = (46, 42, 36); MUT = (122, 112, 99)
ACC = (181, 83, 42); TEAL = (47, 110, 106); LINE = (222, 215, 201); TINT = (244, 230, 219)
_FONT = "/usr/share/fonts/google-noto-vf/NotoSansMono[wght].ttf"


def fnt(sz, w=400):
    f = ImageFont.truetype(_FONT, sz)
    try:
        f.set_variation_by_axes([w])
    except Exception:
        pass
    return f


def rr(d, xy, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def ease(t):
    return 1 - (1 - t) ** 3


SRC = [("ast-grep", "structure", ACC), ("grep", "text", INK), ("embeddings", "meaning", TEAL)]
NODE = (556, 150, 800, 226)
NF = 30


def frame(i):
    t = i / (NF - 1)
    R = ease(min(1.0, t * 1.12))
    glued = R >= 0.985
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 24), 'ix "retry on failure"', font=fnt(26, 600), fill=INK)
    d.text((42, 62), "ast-grep × grep × meaning — glued, with a confidence score", font=fnt(13), fill=MUT)
    nx0, ny = NODE[0], (NODE[1] + NODE[3]) // 2
    for (name, sub, col), y in zip(SRC, (120, 188, 256)):
        rr(d, (40, y, 200, y + 52), 10, outline=col, width=2)
        d.text((58, y + 10), name, font=fnt(19, 600), fill=col)
        d.text((58, y + 31), sub, font=fnt(12), fill=MUT)
        sx, sy = 200, y + 26
        frac = min(1.0, t * 1.4)
        ex, ey = sx + (nx0 - sx) * frac, sy + (ny - sy) * frac
        d.line((sx, sy, ex, ey), fill=(col if frac >= 1 else LINE), width=2)
        if frac >= 1:
            d.ellipse((nx0 - 4, ny - 4, nx0 + 4, ny + 4), fill=col)
    rr(d, NODE, 12, fill=(TINT if glued else None), outline=(ACC if glued else LINE), width=2)
    d.text((NODE[0] + 18, NODE[1] + 14), "net.py:42", font=fnt(17, 600), fill=INK)
    if glued:
        d.text((NODE[0] + 18, NODE[1] + 40), "retry_with_backoff()", font=fnt(13), fill=MUT)
    d.text((556, 88), f"R {R:0.2f}", font=fnt(42, 700), fill=(ACC if glued else MUT))
    if glued:
        d.text((300, 320), "[ ast-grep · grep · meaning ]  →  one result, R = 1.00", font=fnt(14, 500), fill=ACC)
    return im


def main():
    frames = [frame(i) for i in range(NF)] + [frame(NF - 1)] * 8
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "assets"), exist_ok=True)
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "ix-demo.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=95, loop=0, disposal=2, optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
