# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""ix-search — search that agrees with itself.

Three readings of a codebase — structure (ast-grep) ⊗ text (ripgrep) ⊗ semantics
(matryoshka embeddings) — glued at one location, scored by coherence-R. The runnable
instance of *The Matryoshka Sheaf*.
"""
from .embed import MatryoshkaEmbedder
from .search import search
from .sheaf import MODALITIES, Hit, glue

__version__ = "0.1.0"
__all__ = ["search", "MatryoshkaEmbedder", "glue", "Hit", "MODALITIES", "__version__"]
