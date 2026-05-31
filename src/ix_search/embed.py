# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""Matryoshka (nested, truncatable) text embeddings — the semantic reading.

Default backend: model2vec static embeddings (CPU, ~30 MB, no API key, no GPU).
A matryoshka embedding nests: a prefix of the vector is itself a valid, smaller
embedding, so `truncate()` gives a coarse-but-usable vector for a fast first pass
(fold) and the full vector refines it (unfold). Degrades closed to a deterministic
hashed bag-of-tokens if model2vec / the model is unavailable, so search still runs.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

_DEFAULT_MODEL = "minishlab/potion-base-8M"


class MatryoshkaEmbedder:
    def __init__(self, model: str = _DEFAULT_MODEL):
        self.model_id = model
        self._m = self._load(model)
        self.backend = f"model2vec:{model.split('/')[-1]}" if self._m is not None else "hash-fallback"

    @staticmethod
    def _load(model):
        """Load model2vec; if the default HF cache is unwritable (e.g. a root-owned
        .locks from a container), snapshot to a writable dir and load local. Returns
        None only if model2vec is absent or the download truly fails — then the
        hashed fallback keeps search running."""
        try:
            from model2vec import StaticModel
        except Exception:  # noqa: BLE001 — model2vec not installed
            return None
        try:
            return StaticModel.from_pretrained(model)
        except Exception:  # noqa: BLE001 — likely a read-only/poisoned cache
            try:
                import os
                from pathlib import Path

                from huggingface_hub import snapshot_download

                cache = Path(os.environ.get("IX_CACHE", Path.home() / ".cache" / "ix-search"))
                cache.mkdir(parents=True, exist_ok=True)
                local = snapshot_download(model, cache_dir=str(cache))
                return StaticModel.from_pretrained(local)
            except Exception:  # noqa: BLE001
                return None

    @property
    def dim(self) -> int:
        if self._m is not None:
            return int(getattr(self._m, "dim", self._m.embedding.shape[1]))
        return 256

    def encode(self, texts) -> np.ndarray:
        texts = [t if t and t.strip() else " " for t in texts]
        if self._m is not None:
            v = np.asarray(self._m.encode(texts), dtype=np.float32)
        else:
            v = np.stack([self._hash(t) for t in texts]).astype(np.float32)
        return self._norm(v)

    @staticmethod
    def truncate(v: np.ndarray, dim) -> np.ndarray:
        """The matryoshka fold: keep the first `dim` coordinates, renormalize."""
        v = np.asarray(v, dtype=np.float32)
        if dim and 0 < int(dim) < v.shape[-1]:
            v = v[..., : int(dim)]
        return MatryoshkaEmbedder._norm(v)

    @staticmethod
    def _norm(v: np.ndarray) -> np.ndarray:
        v = np.asarray(v, dtype=np.float32)
        n = np.linalg.norm(v, axis=-1, keepdims=True)
        n[n == 0] = 1.0
        return v / n

    @staticmethod
    def _hash(t: str, d: int = 256) -> np.ndarray:
        vec = np.zeros(d, dtype=np.float32)
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]+", t.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % d
            vec[h] += 1.0
        return vec
