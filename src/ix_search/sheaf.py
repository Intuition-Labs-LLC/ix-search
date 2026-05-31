# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""The result sheaf: three modality-readings glued at one location.

Each reading (text, structure, semantic) is a section assigning a score to
locations. Gluing them at a shared location is the sheaf gluing; the coherence

    R = exp(-d_tail / scale)

is the soft Čech H^1 obstruction from *The Matryoshka Sheaf* (the paper), where
d_tail is the number of readings that did NOT land on a location. R = 1 iff all
readings agree there (a unique glued result); R < 1 means only some agreed, and
the result carries exactly which.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

MODALITIES = ("text", "structure", "semantic")


@dataclass
class Hit:
    path: str
    line: int
    snippet: str
    scores: dict = field(default_factory=dict)  # modality -> score in [0, 1]
    R: float = 0.0

    @property
    def agreed(self) -> list:
        return [m for m in MODALITIES if self.scores.get(m, 0.0) > 0]


def glue(per_modality: dict, scale: float = 1.5, n: int = len(MODALITIES)) -> dict:
    """Glue per-modality location->(score, snippet) maps into {loc: Hit} with R.

    per_modality: {modality: {(path, line): (score, snippet)}}.
    """
    locs: dict = {}
    for mod, hits in per_modality.items():
        for loc, (score, snip) in hits.items():
            h = locs.get(loc)
            if h is None:
                h = locs[loc] = Hit(loc[0], loc[1], snip or "")
            h.scores[mod] = max(h.scores.get(mod, 0.0), float(score))
            if not h.snippet and snip:
                h.snippet = snip
    for h in locs.values():
        agreeing = sum(1 for s in h.scores.values() if s > 0)
        d_tail = max(0, n - agreeing)
        h.R = math.exp(-d_tail / scale)
    return locs
