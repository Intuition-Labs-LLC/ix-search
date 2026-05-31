# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""The search: read a codebase three ways (text ⊗ structure ⊗ semantics), glue the
readings at one location, score each by coherence-R. Matryoshka embeddings give a
coarse first pass (truncated) then a fine refine (full dim)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from . import structure
from .embed import MatryoshkaEmbedder
from .sheaf import glue

_CODE_EXT = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".h", ".cc",
    ".cpp", ".hpp", ".rb", ".php", ".cs", ".swift", ".kt", ".scala", ".sh", ".lua",
    ".md", ".txt", ".toml", ".yaml", ".yml", ".sql",
}


def _files(path: str, limit: int = 4000) -> list:
    try:
        p = subprocess.run(["rg", "--files", path], capture_output=True, text=True, timeout=60)
        fs = [f for f in p.stdout.splitlines() if Path(f).suffix in _CODE_EXT]
    except Exception:  # noqa: BLE001
        fs = [str(q) for q in Path(path).rglob("*") if q.is_file() and q.suffix in _CODE_EXT]
    return fs[:limit]


def _chunks(files, window: int = 12, stride: int = 8) -> list:
    out = []  # (path, line_1based, text)
    for f in files:
        try:
            lines = Path(f).read_text(errors="ignore").splitlines()
        except Exception:  # noqa: BLE001
            continue
        for i in range(0, len(lines), stride):
            seg = lines[i : i + window]
            if any(s.strip() for s in seg):
                out.append((f, i + 1, "\n".join(seg)))
    return out


def _tokens(q: str) -> list:
    return [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]+", q.lower()) if len(t) >= 2]


def _firstline(txt: str) -> str:
    for s in txt.splitlines():
        if s.strip():
            return s.strip()[:100]
    return txt[:100]


def _namesim(qtok: str, name: str) -> float:
    name = name.lower()
    if qtok == name:
        return 1.0
    if qtok in name or name in qtok:
        return 0.8
    parts = set(re.findall(r"[a-z0-9]+", re.sub(r"([A-Z])", r" \1", name).lower()))
    return 1.0 if qtok in parts else 0.0


def search(query, path=".", top=12, coarse_dim=64, scale=1.5, embedder=None):
    files = _files(path)
    chunks = _chunks(files)
    if not chunks:
        return []
    locs = [(c[0], c[1]) for c in chunks]
    qtok = set(_tokens(query))

    # --- text reading (lexical: query tokens present in the chunk) ---
    text_hits = {}
    for (f, ln, txt), loc in zip(chunks, locs):
        common = qtok & set(_tokens(txt))
        if common:
            text_hits[loc] = (len(common) / max(len(qtok), 1), _firstline(txt))

    # --- structure reading (ast-grep symbols whose name matches a query token) ---
    struct_hits = {}
    byfile = {}
    for (f, ln, txt), loc in zip(chunks, locs):
        byfile.setdefault(f, []).append((ln, loc, txt))
    for name, f, line in structure.symbols(files):
        if f not in byfile:
            continue
        sim = max((_namesim(t, name) for t in qtok), default=0.0)
        if sim >= 0.5:
            ln_, loc_, txt_ = min(byfile[f], key=lambda c: abs(c[0] - line))
            prev = struct_hits.get(loc_, (0.0, ""))[0]
            struct_hits[loc_] = (max(prev, sim), f"def {name}")

    # --- semantic reading (matryoshka: coarse shortlist -> fine rerank) ---
    emb = embedder or MatryoshkaEmbedder()
    vecs = emb.encode([c[2] for c in chunks])
    qv = emb.encode([query])[0]
    cq = emb.truncate(qv[None, :], coarse_dim)[0]
    coarse = emb.truncate(vecs, coarse_dim) @ cq
    shortlist = np.argsort(-coarse)[: max(top * 4, 40)]
    fine = vecs[shortlist] @ qv
    fmax = float(fine.max()) if len(fine) else 1.0
    order = shortlist[np.argsort(-fine)]
    sem_hits = {}
    for idx in order[: max(top * 3, 30)]:
        s = float(vecs[idx] @ qv)
        if s > 0.15:
            sem_hits[locs[idx]] = (min(1.0, s / max(fmax, 1e-6)), _firstline(chunks[idx][2]))

    glued = glue({"text": text_hits, "structure": struct_hits, "semantic": sem_hits}, scale=scale)
    return sorted(
        glued.values(),
        key=lambda h: (round(h.R, 4), h.scores.get("semantic", 0.0)),
        reverse=True,
    )[:top]
