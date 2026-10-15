<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# ix-iso

`ix-iso` is the formal receipt layer for `ix-search`.

`ix` answers: where did the readings land?

`ix-iso` answers: what typed object did that search produce, what glued, what did
not glue, and what hash proves this exact reading?

## Schema

```text
ix.isoform.v0
```

Core fields:

| Field | Meaning |
|---|---|
| `query` | The user's search intent. |
| `root` | The searched root path. |
| `engine.readings` | Always `text`, `structure`, `semantic`. |
| `law.R_kind` | Always `ix_sheaf_location_R`. |
| `summary` | Aggregate counts over the returned hits. |
| `hits[]` | Per-location sections with `agreed`, `missing`, `d_tail`, and `R`. |
| `receipt.sha256` | SHA-256 over the manifest before the receipt field is attached. |

## Law

Each search location is a candidate sheaf section. Three readings may land there:

```text
text ⊗ structure ⊗ semantic
```

The score is:

```text
R = exp(-d_tail / scale)
```

where `d_tail` is the number of readings that did not land on that hit.

This is a local search agreement score. It is not the live coherence bus. It is
not a model-internal residual stream. It is a receipt over observable local search
readings.

## Why It Exists

The ix series has multiple rungs: search, embeddings, tiles, blocks, glue, mint.
The common object across them is not a CLI output. It is an isoform:

```text
readings + gluing law + residual + receipt
```

`ix-iso` makes that object explicit for the top-level search rung so Agent Zero,
opencode plugins, dashboards, Hugging Face Spaces, and future kernel rungs can all
consume the same shape.
