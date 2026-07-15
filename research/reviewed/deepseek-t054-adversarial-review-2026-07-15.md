# DeepSeek T054 Adversarial Review — R3 Flow Tracer (2026-07-15)

Status: **GREEN — all six self-flagged attack surfaces verified; one DESIGN finding edges toward INFERRED on cap truncation.**

Reviewer: deepseek (adversarial pass per claude's ask: "break it, don't bless it"; M1-LITE — author≠reviewer).
Build under review: claude's T054, 2026-07-15 03:03→03:13 (ledger: claimed→in_progress→verifying).
Files: `core/comm/flow_trace.py` (196 lines), `cmd_flow` + subparser in `agent_cli.py:2413-2479` + parser at `3024-3033`, `scripts/check_door_parity.py` MANIFEST, `tests/test_flow_trace.py` (5 pins, ~123 lines), `docs/MODULE_INDEX.md`.
Six self-flagged attack surfaces, verified per-item below.

---

## Attack Surface 1: Dedupe Key Collapse [CERTAIN] — ACCEPTED AT WINDOW SCALE

### The mechanism
`build_flows` at `flow_trace.py:100-108`:
```python
key = (n["sha"], n["frm"], n["to"], n["kind"]) if n["sha"] else object()
node = by_key.get(key)
if node is None:
    node = {...}     # new logical node
```

The dedupe key is `(sha, frm, to, kind)` — NO timestamp proximity guard.

### Attack scenario
Two IDENTICAL short messages between deepseek→claude, same kind, within the same window: "ok" (sha=xyz, same content hash). They collapse to ONE node with copies=2, even though they're genuinely two separate exchanges.

### Real risk assessment
For this to happen: (a) two messages must have byte-identical content — rare outside short acknowledgments; (b) same (frm, to, kind) must match; (c) both must fall within the same window (default 6h). The sha is a CONTENT hash — identical content IS the same logical payload, even if sent twice. The flow tracer's purpose is to expose double-delivery (same logical message observed via two lanes), not to distinguish two identical "ok" messages sent hours apart.

[CERTAIN] — accepted at window scale. The alternative (adding ts proximity) would require a proximity threshold that is itself tunable and would miss legitimate duplicate detection across wider gaps. The current contract is: "same payload between the same pair = one logical message." For a diagnostic tool, that's correct. If this becomes a problem, the fix is a `ts_proximity_ms` parameter, not a redesign.

---

## Attack Surface 2: Window Relative to Newest Entry [INFERRED] — ACCEPTED, WITH CAVEAT

### The mechanism
`build_flows` at `flow_trace.py:88-91`:
```python
newest = max(n["ms"] for n in norm)
cutoff = newest - max(0, int(window_ms))
kept = [n for n in norm if n["ms"] >= cutoff]
```

The window is `newest_entry_ms - window_ms`. Not wall-clock.

### Attack scenario
A dead bus (Redis down, no new messages for hours) means the "newest" entry is stale. The window slides backward with the newest entry, so ALL past messages are within the window — there's nothing newer to push them out. The render shows "6h window" but actually shows all entries back to the dawn of the stream (since nothing newer exists to create a cutoff).

### Real risk assessment
The render prints the window as `--window 6h` — it doesn't say "from wall-clock now." An operator looking at a dead-bus trace sees old flows and may not realize they're 12h old. The `dropped_by_window` count would be 0 (nothing dropped), which is the tell.

[INFERRED] — low risk for an interactive diagnostic. The operator knows whether the bus is alive (the `offline` key in the output says so). The window-is-relative contract is clear in the code comment: "relative to NEWEST ENTRY not wall-clock." A follow-up could add a `stale_since` field to the output: the delta between wall-clock-now and the newest entry, so a dead bus renders as "window: 6h (newest entry 12h ago — bus may be dead)."

---

## Attack Surface 3: Per-Stream Cap Silent Truncation [INFERRED] — ACCEPTED WITH DOCUMENTATION GAP

### The mechanism
`flow_trace` at `flow_trace.py:156`:
```python
for eid, fields in r.xrevrange(s, count=per_stream):
```
And at line 150:
```python
PER_STREAM_LIMIT = 400
```

Each stream is capped at 400 entries (xrevrange returns newest 400). The window then trims further. Window drops ARE counted (`dropped_by_window`). Cap drops are NOT counted.

### Attack scenario
A stream with 1000 entries in the window: only the 400 newest are read. The other 600 are silently invisible. The `dropped_by_window` count reflects only window-trimming of the 400 that were read — it's artificially low. The operator sees "window dropped 5" but doesn't know 600 were never read.

### Real risk assessment
400 entries is a LOT of messages for a 6h window. The trace stream (most voluminous) is skipped by default (`skip_kinds={"trace"}` at line 148). Work and sig lanes carry real messages — 400 per stream is generous. A stream hitting the cap means the operator should narrow the window or the agent filter.

[INFERRED] — the cap is documented in the module docstring ("bounded read per stream; the window trims harder") but the render doesn't expose "per-stream cap reached." A `capped_streams` count in the output would close the gap. Accepted for v1; the cap is generous enough that it's a "you have bigger problems" signal.

---

## Attack Surface 4: Cycle Guard — Parent Must Precede Child [CERTAIN] — HOLDS

### The mechanism
`build_flows` at `flow_trace.py:117-120`:
```python
parent = id_map.get(ans) if ans else None
if parent is not None and parent is not node and parent["ms"] <= node["ms"]:
    parent["children"].append(node)
else:
    if ans and parent is None:
        node["answers_missing"] = ans
    roots.append(node)
```

Three guards: (1) `parent is not node` — self-link refused; (2) `parent["ms"] <= node["ms"]` — parent must precede child in time; (3) `parent is not None` — unknown parent → roots the child with `answers_missing`.

### Attack scenario: construct a cycle
The `parent["ms"] <= node["ms"]` guard prevents time-paradox cycles. A reply claiming to answer a message with a LATER timestamp is simply rooted as its own flow. The only way to construct a cycle is: message A (ms=1000) answers B (ms=2000) which answers A. But A answers B → A's `meta.answers` = B's id. When processing A (sorted by ms, so B at 2000 comes AFTER A at 1000), A's parent B has `ms=2000 > 1000 = A.ms` → the `<=` guard fails → A becomes a root. When processing B, its parent A exists, A.ms=1000 <= 2000=B.ms → B becomes a child of A. Result: A roots, B is A's child. No cycle. The time-ordering sort + `<=` guard is a DAG constructor.

[CERTAIN] — the cycle guard holds. The combination of sort-by-ms + parent-ms-must-precede-child-ms creates a provable DAG. A self-referencing message (answers its own id) is caught by `parent is not node`. A time-paradox answer is rooted independently. No cycle survives.

---

## Attack Surface 5: Loader `scan_iter` Cost at 100 Agents [INFERRED] — ACCEPTED FOR FLEET SIZE

### The mechanism
`flow_trace` at `flow_trace.py:140-147`:
```python
try:
    for pat in (f"{ns}:work:inbox:*", f"{ns}:inbox:*"):
        for k in r.scan_iter(match=pat, count=200):
            streams.append(dec(k))
except Exception:
    pass
```

`scan_iter` iterates ALL Redis keys matching the pattern. At 100 agents, that's 200 inbox streams (work + legacy). Each stream then gets an `xrevrange` call.

### Real risk assessment
The fleet size today is ~3-4 agents. 100 agents is a distant future. At 10 agents: 20 inbox streams + 2 broadcasts = 22 streams × 400 entries = 8,800 entries. `build_flows` does O(n log n) sort + O(n²) dedup walk in worst case. At 100 agents it's 202 streams × 400 = 80,800 entries — still sub-second for a Python dict walk.

[INFERRED] — accepted for current fleet size. The `scan_iter` call is wrapped in `except: pass` (fail-soft per stream, the module's contract). A follow-up at fleet scale: maintain a cached stream registry (Redis set of active inbox keys, refreshed on agent register), or add `--max-streams` to bound the scan.

---

## Attack Surface 6: `build_flows` Mutates Then Pops `meta` [CERTAIN] — CLEAN

### The mechanism
`build_flows` at `flow_trace.py:128-133`:
```python
def _finish(node, root_ms):
    node["offset_ms"] = node["ms"] - root_ms
    node["lanes"] = sorted(node["lanes"])
    node.pop("meta", None)
    node["children"].sort(key=lambda c: c["ms"])
    ...
```

And at line 106-109:
```python
node = {"id": ..., "meta": n["meta"], ...}
by_key[key] = node
```

The `meta` field from the normalized entry is COPIED into the node dict (not a reference — `n["meta"]` is already a deserialized dict from `_norm`, and the assignment `"meta": n["meta"]` copies the reference to that dict). Then `_finish` pops `meta` from the node.

### Attack scenario: caller reuses entries
If a caller passes the same entries list to `build_flows` twice, the second call gets entries whose `meta` was popped from the internal node dict. But `_norm` COPIES fields from the raw entry — it doesn't modify the original entry dict. The `meta` in `_norm` comes from `e.get("meta")` — which is the raw (possibly bytes/str) field, deserialized into a NEW dict. The original entry's `meta` field (in the caller's list) is untouched — `_norm` created a new dict.

Wait — let me re-trace. `_norm` at line 60-64:
```python
meta = e.get("meta")
if isinstance(meta, (bytes, str)):
    meta = json.loads(meta)
if not isinstance(meta, dict):
    meta = {}
```

This creates a NEW dict (either from json.loads or a fresh `{}`). But it returns it as `n["meta"]` in the normalized result. Then `build_flows` at line 107 stores `"meta": n["meta"]` in the node — sharing the reference with the normalized entry. Then `_finish` pops `meta` from the node. The normalized entry in `norm` still has its `meta`. But `norm` is a local variable in `build_flows` — it's not returned. The caller's original entries list is NEVER modified — `_norm` reads from it, doesn't write to it.

BUT: the CALLER of `build_flows` might be passing the `entries` list from `flow_trace`, which IS the raw entries list. After `build_flows`, those raw entries are unmodified. If the caller calls `build_flows` again with the SAME list, `_norm` re-normalizes from scratch — fresh dicts each time. No leak.

The ONLY risk is if the caller iterates `norm` (the internal list) after calling `build_flows` — but `norm` is a local variable, inaccessible to the caller.

[CERTAIN] — no leak. `_norm` creates fresh dicts from raw entries. `build_flows` stores references in its own internal node dicts, then pops `meta` from those internal dicts only. The caller's entries are untouched. The `meta` pop is a clean-up pass on the output tree to keep the render compact — it's the right thing to do.

---

## Additional Findings (not in claude's self-flag)

### A1. `answers_missing` dangling on the root node, not the child [CERTAIN] — CORRECT
At `flow_trace.py:121`:
```python
if ans and parent is None:
    node["answers_missing"] = ans
```
The `answers_missing` annotation goes on the NODE that couldn't find its parent — the child, which becomes a root. The render prints it at the right level. This is correct: the orphaned reply is the one carrying the causal link that broke. ✓

### A2. `_finish` returns `last` for span calculation [CERTAIN] — CORRECT
At `flow_trace.py:126-131`:
```python
def _finish(node, root_ms):
    ...
    last = node["ms"]
    for c in node["children"]:
        last = max(last, _finish(c, root_ms))
    return last
```
The span is `last_descendant_ms - root_ms`. A flow with no children has span = 0. The render shows "single" for 0-span flows. Correct OTel semantics. ✓

### A3. `_tree_size` counts nodes for frame render [CERTAIN] — CORRECT
At `flow_trace.py:138`:
```python
fl["nodes"] = count   # from _tree_size(root)
```
The frame count is `1 + sum(children counts)`. Deduplicated copies count as ONE node (the copies field carries the multiplicity). Correct — the render says "N msg" not "N copies." ✓

### A4. `lane_of` namespace-tolerant parsing [CERTAIN] — CORRECT
At `flow_trace.py:42-46`:
```python
rest = str(stream_key).split(":")[1:]
head = rest[0] if rest else ""
return {"work": "work", "sig": "sig", "trace": "trace",
        "inbox": "legacy", "broadcast": "broadcast"}.get(head, "unknown")
```
The `[1:]` strip drops the namespace prefix. `"test-rb25:work:inbox:x"` → `rest = ["work","inbox","x"]` → `head = "work"` → `"work"`. `"bifrost:inbox:claude"` → `rest = ["inbox","claude"]` → `head = "inbox"` → `"legacy"`. All six lane labels verified in test F3. ✓

### A5. MANIFEST `flow=cli_only` [CERTAIN] — CORRECT
At `check_door_parity.py:98`:
```python
"flow": "cli_only",   # R3 (T054): flow-trace waterfall -- operator/agent diagnostic; MCP twin
                      # rides the T067 ToolBox-parity wave with delta (same trigger family).
```
Honest classification. The door parity check passes. The comment references T067 as the follow-up wave. ✓

### A6. Subparser window parsing [INFERRED] — MINOR EDGE CASE
At `agent_cli.py` (diff lines 2417-2421):
```python
unit = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
w = str(args.window or "6h").strip().lower()
window_ms = int(float(w[:-1]) * unit[w[-1]]) if w and w[-1] in unit else int(w) * 60_000
```
The fallback `int(w) * 60_000` treats a bare number as minutes. `--window 30` → 30 minutes = 1,800,000ms. But the error message says "use e.g. 30m, 6h, 1d" — the bare-number path works but isn't documented. Minor.

[INFERRED] — the parse is correct; the help text could mention bare numbers. Not a bug.

---

## Verdict Summary

| Attack Surface | Finding | Tag |
|---------------|---------|-----|
| 1. Dedupe key collapse | Same-sha between same pair = one logical message; correct for a diagnostic tool | [CERTAIN] |
| 2. Window relative to newest entry | Dead bus renders stale without saying so; `stale_since` field would help | [INFERRED] |
| 3. Per-stream cap truncation | Cap drops uncounted; generous cap (400) makes this a "bigger problems" signal | [INFERRED] |
| 4. Cycle guard | Sort-by-ms + parent-ms≤child-ms + not-self = provable DAG; no cycle survives | [CERTAIN] |
| 5. scan_iter cost at 100 agents | Acceptable for current fleet (~3-4 agents); cached registry at scale | [INFERRED] |
| 6. meta mutation leak | `_norm` creates fresh dicts; caller's entries untouched; pop is output-tree cleanup | [CERTAIN] |

**No seal-bypass surfaces. No data corruption paths. No double-delivery amplification — the tracer correctly collapses same-sha copies to expose the bug rather than amplifying it.** All six self-flagged surfaces are either correctly defended (1, 4, 6) or accepted at current scale with reasonable follow-ups (2, 3, 5). The five test pins (F1-F5) correctly pre-register the kill conditions and all cover their contracts.

**T054: GREEN. Gates the mirror.**
