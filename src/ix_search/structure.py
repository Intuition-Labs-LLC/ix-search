# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Tej Desai / Intuition Labs LLC
"""The structure reading: ast-grep extracts definitions (name -> location); a
query identifier that names a defined symbol is a structural hit. ast-grep where
the language is supported, regex fallback otherwise (so it always returns something).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# language -> ast-grep patterns binding the symbol name to $N
_PATTERNS = {
    "python": ["def $N($$$A)", "class $N", "class $N($$$A)"],
    "javascript": ["function $N($$$A)", "class $N", "const $N = $$$A"],
    "typescript": ["function $N($$$A)", "class $N", "interface $N", "const $N = $$$A"],
    "tsx": ["function $N($$$A)", "class $N", "const $N = $$$A"],
    "go": ["func $N($$$A)", "type $N $$$A"],
    "rust": ["fn $N($$$A)", "struct $N", "enum $N", "trait $N"],
    "java": ["class $N", "interface $N"],
}
_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".go": "go", ".rs": "rust", ".java": "java",
}
_DEF_RE = re.compile(
    r"^[ \t]*(?:export\s+)?(?:async\s+)?"
    r"(?:def|class|func|fn|function|struct|enum|trait|interface|type)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.M,
)


def symbols(files) -> list:
    """Return (name, file, line_1based) for every definition found."""
    out: list = []
    by_lang: dict = {}
    for f in files:
        lang = _EXT_LANG.get(Path(f).suffix)
        if lang:
            by_lang.setdefault(lang, []).append(f)
    covered = set()
    for lang, fs in by_lang.items():
        for pat in _PATTERNS.get(lang, []):
            try:
                p = subprocess.run(
                    ["ast-grep", "run", "-p", pat, "-l", lang, "--json=stream", *fs],
                    capture_output=True, text=True, timeout=90,
                )
            except Exception:  # noqa: BLE001
                continue
            for ln in p.stdout.splitlines():
                try:
                    m = json.loads(ln)
                except Exception:  # noqa: BLE001
                    continue
                nm = ((m.get("metaVariables", {}) or {}).get("single", {}) or {}).get("N", {})
                name = nm.get("text") if isinstance(nm, dict) else None
                f = m.get("file")
                if name and f:
                    covered.add(f)
                    line = (m.get("range", {}).get("start", {}) or {}).get("line", 0) + 1
                    out.append((name, f, line))
    # regex fallback for any file ast-grep did not cover
    for f in files:
        if f in covered:
            continue
        try:
            txt = Path(f).read_text(errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for m in _DEF_RE.finditer(txt):
            out.append((m.group(1), f, txt.count("\n", 0, m.start()) + 1))
    return out
