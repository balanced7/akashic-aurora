# IC-0014 patch proposal — make `truncated` honest for junction packs

## What's wrong

PR 37's `cmd_sift` records `"truncated": False` for every `JunctionPack`, with the
comment "a junction pack counts junctions and is never capped." That comment is false:

- `core/coord/sift.py:342` — `max_sites: int = 40`
- `core/coord/sift.py:390` — `if len(junctions) >= max_sites: break`

A 40-site junction sift therefore writes `truncated: false` into the durable `--out`
record a reader audits. A reader who sees `truncated: false` reasonably concludes "I am
holding every junction," when in fact the list was capped. That is the absence-honesty
defect class this repo keeps naming, committed inside the tool built to catch it.

(`JunctionPack` at `core/coord/sift.py:281` currently has **no** `truncated` field at
all, which is why the PR hacked around it with a hardcoded `False` instead of carrying
the real answer.)

## The fix (two parts)

### Part 1 — carry real truncation on `JunctionPack`

`core/coord/sift.py`, the dataclass:

```python
@dataclass
class JunctionPack:
    """... (existing docstring unchanged) ..."""
    term: str
    junctions: List[Dict[str, Any]] = field(default_factory=list)
    blob: str = ""
    sha: str = ""
    truncated: bool = False            # NEW — mirrors EvidencePack.truncated
    blind: List[str] = field(default_factory=list)
```

### Part 2 — compute it in `junction_pack()`

Track whether the cap fired. The loop currently breaks silently:

```python
    junctions: List[Dict[str, Any]] = []
    capped = False                      # NEW
    if writes and reads:
        # ... (existing grouping unchanged) ...
        for wf in sorted(by_wfile):
            for rf in sorted(by_rfile):
                if len(junctions) >= max_sites:
                    capped = True       # NEW — the cap actually fired
                    break
                junctions.append({...})
```

Then the return at `core/coord/sift.py:417`:

```python
    return JunctionPack(term=term, junctions=junctions, blob=blob, sha=_sha(blob),
                        truncated=capped, blind=blind)
```

And add a `blind` note so the cap is visible in the rendered blob too (optional but
recommended — the blob is what a human curator actually reads):

```python
    if capped:
        blind.append(
            f"JUNCTION LIST CAPPED at {max_sites} crossings — more writer/reader pairs "
            f"existed than are shown. This is a candidate sample, not an exhaustive map."
        )
```

### Part 3 — `cmd_sift` stops hardcoding `False`

Replace PR 37's line:

```python
"truncated": False if isinstance(p, S.JunctionPack) else p.truncated
```

with:

```python
"truncated": p.truncated
```

`JunctionPack.truncated` now exists and carries the honest value, so the `isinstance`
special-case (and its false comment) can be deleted entirely.

## Why this is the right fix (and not the other obvious one)

- It does **not** claim "never capped" — the cap is real, so we report it.
- It keeps `JunctionPack` and `EvidencePack` field-parallel, which is the point of the
  "a reader must never mistake one for the other" docstring on the class.
- It is honest in both directions: an under-40 sift genuinely reports `false`, a capped
  one reports `true`.

## Cross-check

Independently confirmed against master on 2026-10-05 by deepseek (@Vandor's review,
ADR_1005140356): `max_sites=40` and the `break` are live at the cited lines; `JunctionPack`
has no `truncated` field today. The `isinstance(p, S.JunctionPack)` line is PR-37's own new
code (not yet on master).
