# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""ix — search that agrees with itself."""
from __future__ import annotations

import argparse
import sys

from .embed import MatryoshkaEmbedder
from .search import search

_C = {"g": "\033[32m", "y": "\033[33m", "d": "\033[2m", "b": "\033[1m", "x": "\033[0m"}


def _rtag(r: float) -> str:
    c = "g" if r >= 0.85 else ("y" if r >= 0.4 else "d")
    return f"{_C[c]}R {r:.2f}{_C['x']}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="ix",
        description="ix — search that agrees with itself "
        "(structure ⊗ text ⊗ meaning, glued at one place by coherence-R).",
    )
    ap.add_argument("query", help="ask in meaning, not just keywords")
    ap.add_argument("path", nargs="?", default=".", help="directory to search (default: .)")
    ap.add_argument("-n", "--top", type=int, default=12)
    ap.add_argument("--dim", type=int, default=64, help="coarse matryoshka dim (fast first pass)")
    ap.add_argument("--scale", type=float, default=1.5, help="R sharpness")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    emb = MatryoshkaEmbedder()
    hits = search(a.query, a.path, top=a.top, coarse_dim=a.dim, scale=a.scale, embedder=emb)

    if a.json:
        import json

        print(json.dumps(
            [{"R": round(h.R, 3), "path": h.path, "line": h.line,
              "snippet": h.snippet, "agreed": h.agreed} for h in hits], indent=2))
        return 0
    if not hits:
        print("no glued results.", file=sys.stderr)
        return 1
    print(f"{_C['d']}ix · {emb.backend} · structure ⊗ text ⊗ meaning glued by R{_C['x']}\n")
    for h in hits:
        tags = "·".join(m[:4] for m in ("text", "structure", "semantic") if m in h.agreed)
        print(f"  {_rtag(h.R)}  {_C['b']}{h.path}:{h.line}{_C['x']}  "
              f"{_C['d']}{h.snippet}{_C['x']}  {_C['d']}[{tags}]{_C['x']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
