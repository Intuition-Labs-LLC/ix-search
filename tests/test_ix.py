# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""Tests: the gluing law (R), the matryoshka truncation, and an end-to-end search."""
import math

from ix_search import MatryoshkaEmbedder, glue, isoform, search


def test_glue_R_is_one_when_all_three_agree():
    loc = ("a.py", 10)
    per = {
        "text": {loc: (0.9, "x")},
        "structure": {loc: (1.0, "def x")},
        "semantic": {loc: (0.8, "x")},
    }
    hits = glue(per)
    assert hits[loc].R == 1.0
    assert set(hits[loc].agreed) == {"text", "structure", "semantic"}


def test_glue_R_drops_when_only_one_reading_lands():
    loc = ("a.py", 10)
    hits = glue({"semantic": {loc: (0.8, "x")}}, scale=1.5)
    # two of three readings missing -> d_tail = 2
    assert math.isclose(hits[loc].R, math.exp(-2 / 1.5), rel_tol=1e-6)
    assert hits[loc].agreed == ["semantic"]


def test_matryoshka_truncate_nests_and_normalizes():
    emb = MatryoshkaEmbedder()
    v = emb.encode(["retry the request on a connection failure"])
    full = v.shape[-1]
    coarse = emb.truncate(v, min(64, full))
    assert coarse.shape[-1] == min(64, full)
    # unit-normalized
    norms = (coarse ** 2).sum(-1) ** 0.5
    assert abs(float(norms[0]) - 1.0) < 1e-4


def test_end_to_end_finds_the_relevant_function(tmp_path):
    (tmp_path / "net.py").write_text(
        "import time\n"
        "def retry_with_backoff(fn, attempts=3):\n"
        "    for i in range(attempts):\n"
        "        try:\n"
        "            return fn()\n"
        "        except ConnectionError:\n"
        "            time.sleep(2 ** i)\n"
    )
    (tmp_path / "math_utils.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n"
    )
    hits = search("retry a request when it fails", str(tmp_path), top=5)
    assert hits, "search returned nothing"
    top = hits[0]
    assert top.path.endswith("net.py"), f"expected net.py on top, got {top.path}"
    assert top.R >= hits[-1].R  # sorted by R desc


def test_ix_iso_emits_a_hashable_receipt(tmp_path):
    (tmp_path / "net.py").write_text(
        "def retry_with_backoff(fn, attempts=3):\n"
        "    for i in range(attempts):\n"
        "        try:\n"
        "            return fn()\n"
        "        except ConnectionError:\n"
        "            pass\n"
    )
    doc = isoform("retry request failure", str(tmp_path), top=5)
    assert doc["schema"] == "ix.isoform.v0"
    assert doc["receipt"]["sha256"]
    assert doc["law"]["R_kind"] == "ix_sheaf_location_R"
    assert doc["summary"]["hits"] == len(doc["hits"])
    assert set(doc["summary"]["reading_counts"]) == {"text", "structure", "semantic"}
    assert doc["claim_boundary"], "receipt must carry honest claim boundaries"


def test_ix_iso_hash_is_stable_for_same_fixture(tmp_path):
    (tmp_path / "a.py").write_text("def alpha():\n    return 'alpha retry'\n")
    one = isoform("alpha retry", str(tmp_path), top=3)
    two = isoform("alpha retry", str(tmp_path), top=3)
    assert one["receipt"]["sha256"] == two["receipt"]["sha256"]
