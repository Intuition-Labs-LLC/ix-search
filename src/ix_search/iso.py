# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""ix-iso — a typed isoform receipt over an ix search.

`ix` returns hits. `ix-iso` returns the same search as a small, stable object that
other agents, dashboards, and release artifacts can consume without scraping CLI
text. The receipt is the product boundary: it names the readings, the gluing law,
the per-hit obstructions, and a deterministic hash of the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .embed import MatryoshkaEmbedder
from .search import search
from .sheaf import MODALITIES, Hit

SCHEMA = "ix.isoform.v0"


def _round(x: float | int | None, ndigits: int = 4) -> float | None:
    if x is None:
        return None
    return round(float(x), ndigits)


def _hit_to_dict(hit: Hit) -> dict[str, Any]:
    agreed = hit.agreed
    missing = [m for m in MODALITIES if m not in agreed]
    return {
        "path": hit.path,
        "line": hit.line,
        "snippet": hit.snippet,
        "R": _round(hit.R),
        "agreed": agreed,
        "missing": missing,
        "d_tail": len(missing),
        "scores": {k: _round(v) for k, v in sorted(hit.scores.items())},
        "section": "global" if not missing else "partial",
    }


def _digest(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _summary(hit_rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(hit_rows)
    if not n:
        return {
            "hits": 0,
            "top_R": None,
            "mean_R": None,
            "residual_mean": None,
            "global_sections": 0,
            "partial_sections": 0,
            "reading_counts": {m: 0 for m in MODALITIES},
            "missing_counts": {m: 0 for m in MODALITIES},
        }
    rs = [float(h["R"] or 0.0) for h in hit_rows]
    reading_counts = {m: 0 for m in MODALITIES}
    missing_counts = {m: 0 for m in MODALITIES}
    for h in hit_rows:
        for m in h["agreed"]:
            reading_counts[m] += 1
        for m in h["missing"]:
            missing_counts[m] += 1
    mean_r = sum(rs) / n
    global_sections = sum(1 for h in hit_rows if h["section"] == "global")
    return {
        "hits": n,
        "top_R": _round(max(rs)),
        "mean_R": _round(mean_r),
        "residual_mean": _round(1.0 - mean_r),
        "global_sections": global_sections,
        "partial_sections": n - global_sections,
        "global_ratio": _round(global_sections / n),
        "reading_counts": reading_counts,
        "missing_counts": missing_counts,
    }


def isoform(
    query: str,
    path: str = ".",
    top: int = 12,
    coarse_dim: int = 64,
    scale: float = 1.5,
    embedder: MatryoshkaEmbedder | None = None,
) -> dict[str, Any]:
    """Return a deterministic ix isoform receipt.

    This does not add a fourth search engine. It formalizes the existing three
    readings (`text`, `structure`, `semantic`) into a hashable object that can be
    carried across repos and adapters.
    """
    emb = embedder or MatryoshkaEmbedder()
    hits = search(query, path, top=top, coarse_dim=coarse_dim, scale=scale, embedder=emb)
    rows = [_hit_to_dict(h) for h in hits]
    root = str(Path(path).resolve()) if path else "."
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "query": query,
        "root": root,
        "engine": {
            "name": "ix-search",
            "readings": list(MODALITIES),
            "semantic_backend": emb.backend,
            "coarse_dim": int(coarse_dim),
            "scale": float(scale),
        },
        "law": {
            "object": "interaction location",
            "operation": "structure ⊗ text ⊗ meaning",
            "glue": "readings land on the same path:line locus",
            "R": "exp(-d_tail / scale)",
            "d_tail": "number of readings that did not land on a hit",
            "R_kind": "ix_sheaf_location_R",
        },
        "summary": _summary(rows),
        "hits": rows,
        "claim_boundary": [
            "This is a local code-search receipt, not a hidden model-state read.",
            "R is the ix sheaf-location agreement score, not the live coherence bus.",
            "Semantic search runs locally via model2vec when available and hash fallback otherwise.",
            "A partial section is useful evidence, not a fabricated certainty.",
        ],
    }
    sha = _digest(payload)
    payload["receipt"] = {"id": sha[:18], "sha256": sha}
    return payload


def format_isoform(doc: dict[str, Any]) -> str:
    summary = doc["summary"]
    lines = [
        f"ix-iso · {doc['engine']['semantic_backend']} · {doc['law']['operation']}",
        f"receipt {doc['receipt']['id']} · sha256 {doc['receipt']['sha256']}",
        f"hits={summary['hits']} global={summary['global_sections']} partial={summary['partial_sections']} top_R={summary['top_R']} mean_R={summary['mean_R']} residual={summary['residual_mean']}",
        "",
    ]
    for h in doc["hits"]:
        tags = "·".join(h["agreed"]) or "none"
        missing = ",".join(h["missing"]) or "none"
        lines.append(
            f"  R {h['R']:.2f}  {h['path']}:{h['line']}  [{tags}]  missing={missing}  {h['snippet']}"
        )
    if not doc["hits"]:
        lines.append("  no sections found")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="ix-iso",
        description="ix-iso — emit a stable isoform receipt for an ix search.",
    )
    ap.add_argument("query", help="semantic/text query")
    ap.add_argument("path", nargs="?", default=".", help="directory to search")
    ap.add_argument("-n", "--top", type=int, default=12)
    ap.add_argument("--dim", type=int, default=64, help="coarse matryoshka dim")
    ap.add_argument("--scale", type=float, default=1.5, help="R sharpness")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    doc = isoform(args.query, args.path, top=args.top, coarse_dim=args.dim, scale=args.scale)
    if args.json:
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    else:
        print(format_isoform(doc))
    return 0 if doc["hits"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
