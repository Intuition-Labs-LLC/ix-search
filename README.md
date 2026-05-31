<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# ix — search that agrees with itself

Ask your code in **meaning**. `ix` glues three readings — **structure** (ast-grep) ⊗ **text** (ripgrep) ⊗ **semantics** (matryoshka embeddings) — at one location, and hands back an **R**: how sure, *because they agreed*.

```bash
pip install ix-search          # the command is `ix`
ix "the part that retries on failure" .
```

```
ix · model2vec:potion-base-8M · structure ⊗ text ⊗ meaning glued by R

  R 1.00  src/net.py:42    def retry_with_backoff(...)     [text·stru·sema]
  R 0.51  src/http.py:88   except ConnectionError: ...     [text·sema]
  R 0.26  src/util.py:12   # exponential backoff helper    [sema]
```

Every hit carries **R = exp(−d_tail / scale)** — the soft Čech gluing obstruction from *The Matryoshka Sheaf*. **R = 1** when all three readings land on the same place; lower when only some agree. The tag shows which readings glued. It's **confidence, not a black-box cosine.**

## Why it's different

- **Three readings glue.** Lexical, structural, and semantic search are three *sections* over one location. `ix` glues them and scores the agreement. A semantic-only hit (R low) is flagged honestly; a hit where structure *and* text *and* meaning land (R = 1) is the one you want.
- **Matryoshka = speed.** The embeddings are nested (a prefix is itself a smaller embedding), so `ix` does a fast coarse pass on a truncated vector, then unfolds to full dim only on the survivors. `--dim` tunes the coarse pass.
- **Local, no API key.** Default embeddings are [model2vec](https://github.com/MinishLab/model2vec) static vectors — CPU, ~30 MB, no GPU, nothing leaves the machine.

## Use it

```bash
ix "where do we validate the auth token" src/
ix "rate limiting" . --top 20
ix "off-by-one in the pagination" . --json     # machine-readable, for an agent
```

For an agent, the `--json` output gives `(path, line, R, agreed)` per hit — so it can **act on confidence** (take R ≈ 1, escalate R < 1) instead of guessing on a single cosine.

```python
from ix_search import search
for h in search("retry on failure", "."):
    print(h.R, h.path, h.line, h.agreed)
```

## The theory

`ix` is the runnable instance of **The Matryoshka Sheaf** — a sheaf where local readings glue into one global result exactly when they agree, with `R = exp(−d_tail/scale)` as the gluing obstruction.

- Paper + runnable code: https://huggingface.co/datasets/intuitionlabs/matryoshka-sheaf
- ELI5: https://intuitionlabs.tech/codebox/phi/35-the-matryoshka-sheaf

Requires [`ast-grep`](https://ast-grep.github.io) and [`ripgrep`](https://github.com/BurntSushi/ripgrep) on `PATH` for the structure + text readings (semantic-only still works without them).

---

AGPL-3.0-or-later · [Intuition Labs](https://intuitionlabs.tech)
