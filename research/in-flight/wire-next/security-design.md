---
title: The security plane of the wire journal — outbound DLP, body capture, and the fleet egress monitor
task: T156 WIRE-B (dimension: security plane and body capture)
author: opus5 (claude seat)
date: 2026-08-04
status: DESIGN ONLY — nothing here is built; no commits, no ledger writes
extends: research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md
             research/in-flight/api-wire-reverse-engineering-deepseek-2026-08-04.md
             research/in-flight/wire-capture-deepseek-2026-08-02/
---

# The security plane of the wire journal

Daniil, 2026-08-04: *"a good place for our security eyes when we get them"* — and the shipped slice
is metadata-only (`scripts/wire_journal.py:38-42`) **precisely so that this design could be done
properly rather than retrofitted**. This is that design.

---

## 0. HEADLINE, and the one thing that must change first

**The wire journal cannot currently tell a security reviewer where a single byte went.**

`_shape()` (`scripts/wire_journal.py:106-145`) emits 24 keys. Not one of them is a destination.
`handle_request` computes `url = str(request.url)` at `scripts/wire_journal.py:323` and uses it only
for retry inference (`:316-320`); it is **never passed to `record()`** (`:338-340` passes exactly
`status`, `attempt`, `headers`, `ms_first_byte`). Verified against the 22 live records on disk:

```
$ py -c "...json.load(state/wire/wire-20260804.jsonl)..."
n= 22
keys ['agent','attempt','cache_hit_tokens','cache_miss_tokens','cached_tokens','completion_tokens',
      'error','finish_reason','headers','model','ms_first_byte','ms_total','prompt_prefix_sha',
      'prompt_sha','prompt_tokens','reasoning_tokens','response_id','response_sha','service_tier',
      'status','stream','system_fingerprint','total_tokens','ts']
any url-ish key? []
agent  [('unknown', 22)]      model [('None', 22)]      prompt_sha [('None', 22)]
```

A DLP design that starts anywhere other than *"what host received these bytes, sent by which agent"*
is decoration. **EGRESS-1 (§2.1) is the prerequisite for everything else in this document.**

Second headline, stated once so it is not buried: **`expert()` at `scripts/wire_journal.py:229` has
zero callers in the entire repository** (verified: `grep -rn "expert" --include=*.py scripts/ tests/
core/ agent_cli.py` returns only the `def` line), and `summarize()`'s only callers are
`tests/test_t156_wire_journal.py:113` and `:124`. This is `core/coord/cognitive_metrics.py` repeating
itself one directory over — *the standing warning is that a writer without a reader is the defect*.
Every proposal below names its reader. A security control whose only consumer is a test proves
nothing about the fleet.

---

## 1. GROUND TRUTH: what exists, measured

### 1.1 The existing secret guard is path-based and is NOT a DLP engine

The repo's only secret-aware code is `ToolBox._is_secret` at `core/comm/toolbox.py:241-249`:

```python
@staticmethod
def _is_secret(p: Path) -> bool:
    parts = [x.lower() for x in p.parts]
    if ".secrets" in parts:                       # :244
        return True
    name = p.name.lower()
    if name == ".env" or name.startswith(".env.") or name in {"id_rsa","id_dsa","credentials","credentials.json"}:
        return True                               # :247-248
    return p.suffix.lower() in {".key",".pem",".crt",".pfx",".p12",".der"}   # :249
```

It is enforced in exactly two places: `_resolve()` refuses the path outright
(`core/comm/toolbox.py:237-238`), and `search_files()` skips secret files while grepping
(`core/comm/toolbox.py:326-327`).

**Reusability verdict: reusable as a PROVENANCE ORACLE, not as a content scanner.**

- What it does: answers *"is this filesystem path a credential store?"* in O(path components), with
  no I/O and no content. That is exactly the input a taint tracker needs (§2.2), and it is already
  correct and already tested in production use.
- What it cannot do: it never sees a byte of content. `grep -rniE "redact|scrub|entropy" core/
  scripts/ agent_cli.py` finds **no content-redaction helper anywhere in the repo** — the only hits
  are `core/coord/metrics.py:38` (Shannon entropy over *approach vectors*, a diversity metric, not a
  secret detector) and `scripts/enrich_corpus.py:246` (a projection-suppression comment). The prior
  design already stated this at
  `research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md:341-346`; I verified it
  independently and concur.
- The measured hole: `.secrets/` on disk right now contains `deepseek.key`, `gemini.key`,
  `kimi.key`, `openai.key`, `cursor.key` **in plaintext with default ACLs**, plus a 1.8 MB
  `gemini_debug.html` — i.e. a *debug capture already accumulates in the credential directory
  unencrypted*. `_is_secret` stops an agent reading those paths. It does nothing about a key that a
  human pastes into a bus message, a key hardcoded in a `.py` file, or a key echoed into a
  `run_command` result.

### 1.2 How repo content actually reaches a provider

This is the taint path, and it is short. `scripts/deepseek_chat.py:437`:

```python
self.messages.append({"role": "tool", "tool_call_id": s["id"], "content": result})
```

`result` is the return value of `self.toolbox.execute(...)` (`scripts/deepseek_chat.py:426`). So:
**every `read_file`, `search_files`, `git_diff`, and `run_command` result is appended to the message
array and re-sent to the provider on the next hop, and on every hop after that.** Bounds are real
but generous: `MAX_FILE_BYTES = 120_000` and `MAX_CMD_OUT = 16_000`
(`core/comm/toolbox.py:56,59`), up to `MAX_TOOL_ROUNDS = 30` (`scripts/deepseek_chat.py:107`).

The volume this produces is measured, not estimated. `state/runner_kimi_2026-08-02.json`:

```json
{"agent":"kimi","turns":22,"prompt_tokens":3948826,"completion_tokens":74023,...}
```

**3,948,826 prompt tokens across 22 turns = ~179,500 tokens/turn ≈ 718 KB of prompt text per HTTP
request.** That number is the sizing constant for every performance claim below.

### 1.3 Only one of four runners is instrumented

| Factory | Serves | Instrumented? | Evidence |
|---|---|---|---|
| `scripts/deepseek_chat.py:66-91` | deepseek | **YES** (`:83-88`, `AKASHIC_WIRE` opt-out at `:83`) | reads `recording_http_client` |
| `core/comm/runner_lib.py:14-27` | gemini + kimi | NO — plain `OpenAI(...)` at `:25-27` | no `http_client=` |
| `scripts/gemini_chat.py:82-87` | gemini | NO — delegates to the above | verified |
| `scripts/kimi_chat.py:83-88` | kimi | NO — delegates to the above | verified |
| `scripts/sol_chat.py:59-64` | sol | NO — inline `OpenAI(...)` at `:62-64` | verified |

Provider endpoints in use: `https://api.deepseek.com` (`scripts/deepseek_chat.py:55`),
`https://api.moonshot.ai/v1` (`scripts/kimi_chat.py:45`), `https://api.openai.com/v1`
(`scripts/sol_chat.py:39`), and `https://generativelanguage.googleapis.com/v1beta/openai/` —
which is **`os.getenv("GEMINI_BASE_URL", ...)`, environment-overridable**
(`scripts/gemini_chat.py:43-46`). That last one is a security-relevant fact, not trivia (§5.4).

### 1.4 The trust model this plugs into

`core/trust/capabilities.py:13-28` defines 13 caps: `READ, WRITE, EXEC, BUS_SEND, BUS_NUDGE,
BUS_STEER, ADMIN_GRANT, ADMIN_APPROVE, KB_RECALL, KB_LEARN, NET, GIT_READ, BIFROST_INBOX`.
**There is no egress capability.** `NET` (`:25`) is scoped in its own comment to `web_search` —
i.e. *inbound* fetch, not outbound model traffic. Nothing in the capability vocabulary describes
"may send bytes to a third-party inference provider," which is the single largest data-exfiltration
surface the system has.

`security/acl.json` currently holds **11 grants**: 1 super_admin (claude), 4 admin (deepseek, kimi,
sol, sol-codex), 6 member. Six of those already carry non-`*` `path_scope` values —
`deepseek-red: ['research/*','scratch/*']`, `codex_root: ['agent_cli.py','core/comm/bus.py',...]`
with `expires_at: 2026-08-05T12:00:00Z`. So the fleet **already runs a tiered-trust model with
scoped grants**; it just has no scoping for the outbound direction.

Enforcement is at `core/comm/toolbox.py` — `_prewrite` consults
`resolve(self.agent_id).can_write(rel_true)` at `:878-886`, `run_command` consults
`resolve(self.agent_id).has(Cap.EXEC)` at `:1058-1067`, both fail-closed on trust-layer errors.
`core/trust/registry.py:233-248` `resolve()` is the single door-check entry, fail-closed to
`quarantined` on unverified identity, missing/corrupt file (except the `BOOTSTRAP_ROLES` floor at
`:28-31`), absence, or expiry.

*(Correction to the brief, recorded per rule 4: the brief cites `agent_cli.py:5464` as the render
gate. At HEAD that line is inside `cmd_toast`; the render-gate function is `_agent_acl_caps` at
`agent_cli.py:5477-5489`, whose docstring at `:5478-5479` reads "The ACL is the render gate". The
brief's characterisation is right; the line number has drifted ~13 lines.)*

---

## 2. (a) OUTBOUND DLP — detecting secrets before they leave

### 2.0 The design principle, borrowed from this repo's own doctrine

`core/recall/gate_rules.py:151-156` already settled this argument for a different surface:

> *"the mutator vocabulary is INFINITE, so safety cannot be a denylist — a denylist fails toward
> SILENCING whenever an unknown mutator wears a known sink... The vocabulary rots toward FIRING,
> which is the bar's law."*

The secret vocabulary is likewise infinite (every provider invents a new key prefix). So the primary
control **must not be a pattern denylist**. It must be **provenance**: we know where every byte came
from, because *we* put it in the message array. Patterns are the second layer, and entropy is the
third — and §2.4 measures exactly how weak the third layer is.

### 2.1 EGRESS-1 — record the destination (the prerequisite)

Add to `_shape()` (`scripts/wire_journal.py:106-145`), sourced from values already in hand at
`scripts/wire_journal.py:322-323`:

| Field | Value | Why a reviewer needs it |
|---|---|---|
| `host` | `request.url.host` | "which third party received our repo?" — unanswerable today |
| `url_path` | `request.url.path` — **path only, never `request.url.query`** | some providers accept keys as query params (prior design §4 policy 2) |
| `method` | `request.method` | distinguishes a completion from a `/models` probe |
| `request_bytes` | `len(request.content)` or `content-length` | **the exfiltration volume metric.** Bytes-out per agent per host is the single number an exfil monitor is built around, and it costs one `len()` |
| `port`, `scheme` | from `request.url` | a plaintext `http://` call is a finding by itself |

**Hot-path cost: ~0.** These are attribute reads on an object the transport already holds. Measured
baseline for the whole of `record()` today: **median 0.291 ms, p95 0.725 ms** over 300 iterations
with a realistic 6-header / full-usage payload (bench: scratchpad `rec_bench.py`). Five more scalar
fields do not move that; the write is dominated by the `open`/`write`/`listdir` syscalls in
`record()` → `_rotate()` (`scripts/wire_journal.py:96-100,147-161`), not by dict construction.

**Reader:** `expert()` gains a finding — *"N round trip(s) to host X, which is not in the egress
allowlist"* — plus a per-host bytes-out roll-up in `summarize()`. And `expert()` must actually be
called by something (§7 pins).

**Also fix while here:** `scripts/wire_journal.py:332` reads
`model=request.headers.get("x-model")`. `grep -rn "x-model" --include=*.py .` finds exactly one
occurrence in the repo — *that line*. Nothing ever sets the header, so the field is structurally
always `None`, which the 22 live records confirm (`model [('None', 22)]`). A dead field in a
security record is worse than a missing one: it renders as MEASURED-absent.

### 2.2 DLP-1 — taint at the source (the primary control, and it is nearly free)

We do not need to *detect* that repo content is on the wire. We **know**, because
`core/comm/toolbox.py` put it there. The ToolBox is the only component that can attribute a byte to
its origin, and it already computes the security-relevant classification of that origin
(`_is_secret`, `core/comm/toolbox.py:241-249`).

Proposal: a **taint ledger** — a small per-turn accumulator maintained by the ToolBox and read by
the recorder at request time.

```
TaintVector (per API request):
  paths_read        : sorted list of repo-relative paths whose bytes are in the message array
  path_classes      : {"secret": n, "protected": n, "source": n, "docs": n, "state": n}
  exec_commands     : the argv[0] of each run_command in this turn
  bus_absorbed      : count of bus messages folded into the prompt
  external_absorbed : count of web_search / fetched results folded in    <- highest risk class
  taint_sha         : sha256 over the sorted path list (a stable turn fingerprint)
```

Recorded fields on the wire record: `taint_classes` (the counts dict), `taint_sha`, and
`taint_paths_n`. **Never the path list itself by default** — a path list *is* a partial disclosure of
repo structure, and this journal will be read by more eyes than the repo (§4.2). Full paths live at
tier 1 only.

Why this is the primary control and not a nicety:

1. **It survives transformation.** A content scanner sees `sk-abc...`; it does not see the model
   summarising a key into prose, base64ing it, or splitting it across two messages. Provenance says
   *"bytes from `.secrets/deepseek.key` entered this turn"* regardless of what shape they left in.
2. **It is the only signal that can be complete.** Content detection has a measured false-negative
   floor (§2.4). Provenance has none — the ToolBox is the *sole* door for file content
   (`core/comm/toolbox.py:226-239` `_resolve` gates every path).
3. **Cost is O(number of tool calls per turn) — a few dozen string appends.** No content is scanned.
   Against a measured TTFT of 638–906 ms (live records `ms_first_byte`, and
   `wire-capture-deepseek-2026-08-02/p3-ttft-decomposition.json` at 0.813–0.890 s), this is
   unmeasurable.
4. **It closes a hole `_is_secret` leaves open by construction.** `_is_secret` blocks the *read*.
   It has nothing to say about `run_command` output — and the pytest exec family
   (`core/comm/toolbox.py:986-989`) runs arbitrary repo code whose stdout lands in `MAX_CMD_OUT`
   bytes of tool result. The comment at `core/comm/toolbox.py:1018` concedes it: *"Containment is
   COMMIT hygiene, not sandboxing (the pytest family already runs repo code)"*.

**Contradiction, recorded not resolved:** the taint ledger requires the ToolBox (in `core/`) to hand
state to the recorder (in `scripts/`), which the membrane law forbids in the `core → scripts`
direction. The clean resolution is a **pull, not a push**: the ToolBox exposes a read-only
`taint_snapshot()` property; the runner (already outside `core/`) reads it and passes it to
`record()`. `core/` gains a getter and imports nothing. I believe that holds, but the membrane's
custodian should rule.

### 2.3 DLP-2 — the four-layer detector, ordered by measured cost

All figures below are **measured on this machine** against a 720,474-byte corpus assembled from real
`core/**/*.py|md|json` content — i.e. a realistic single-request prompt at kimi's observed
179.5k-token turn size (§1.2). Python 3.11, `re` module, min-of-N timing.

| Layer | What it catches | 720 KB (full prompt) | 16 KB (tool-result delta) | 120 KB (`read_file` delta) |
|---|---|---|---|---|
| **L0 provenance** (§2.2) | anything from a classified path | ~0 ms | ~0 ms | ~0 ms |
| **L1 literal prefilter** — 20 substrings (`sk-`, `AKIA`, `-----BEGIN`, `AIza`, `ghp_`, `xox`, `://`, …) | gates L2 | **4.21 ms worst case** (zero matches → 20 full scans); 3.40 ms typical | ~0.09 ms | ~0.70 ms |
| **L2 structured patterns** — 20 compiled regexes | key formats, PEM blocks, DSN-with-password, JWT, `Authorization: Bearer` | **20.4 ms** (20 separate) / **26.6 ms** (single alternation) | **0.53 ms** | **4.35 ms** |
| **L3 entropy** — Shannon over `[A-Za-z0-9+/=_-]{24,}` runs | unstructured high-entropy blobs | **8.8 ms** | ~0.2 ms | ~1.5 ms |

Three non-obvious results worth carrying into the build:

1. **Twenty separate compiled regexes (20.4 ms) beat one big alternation (26.6 ms).** The alternation
   destroys each branch's literal-prefix optimisation. The intuitive "one pass is faster" is wrong
   here by 30%.
2. **Python 3.11 rejects a mid-pattern `(?i)` inside an alternation** (`re.error: global flags not
   at the start of the expression`). Case-insensitive branches must use scoped `(?i:...)`. This bit
   me while benchmarking; it will bite whoever builds it.
3. **The literal prefilter is not free.** It reads as 0 ms only because it short-circuits on the
   first hit; forced to miss all 20 literals it costs 4.21 ms. On a full prompt a prefilter buys
   you 20.4 → 4.2 ms only in the (rare) clean case. **On a delta it is genuinely cheap.** Which
   leads to the actual performance answer:

### 2.4 DLP-3 — delta-only scanning is the performance design

The prior design's §4 arithmetic already established that prompt volume is dominated by **resent
context** — the same repo bytes shipped dozens of times. That is not just a storage observation; it
is the scanning strategy.

**Scan each message ONCE, at the moment it is appended, keyed by content hash. Never re-scan the
assembled prompt.**

```
verdict = memo.get(sha256(message_content))          # content-addressed, per-process
if verdict is None:
    verdict = L1 → L2 → L3 over THIS message only
    memo[sha] = verdict                              # bounded LRU, ~2000 entries
turn_verdict = union(verdict for each message in the array)
```

A turn appends at most: one user/bus message, one assistant message, and one tool result per tool
call — bounded by `MAX_CMD_OUT = 16_000` or `MAX_FILE_BYTES = 120_000`
(`core/comm/toolbox.py:56,59`).

**Measured marginal cost per turn: 0.53 ms (16 KB tool result) to 4.35 ms (120 KB file read),
worst case ~5 ms if every layer runs.** Against the measured 638–906 ms TTFT, that is **0.6–0.8% of
first-byte latency** and ~0.4% of the 1.06–1.16 s total call time recorded in
`p3-ttft-decomposition.json`. Compared to the naive full-prompt scan (26.6 ms → 3% of TTFT), the
memo is a **5–50× reduction** and it is exact, not approximate: the same bytes cannot change verdict.

Cache-hit sizing: at kimi's 179.5k tokens/turn against a 120 KB max delta, **>95% of every prompt is
already-scanned bytes** on turn ≥ 2. The memo is the whole ball game.

**Where it runs, and the honest asymmetry.** The scan is *synchronous and blocking on the request
path only when the policy is BLOCK*. Under `WARN` (the default posture, §2.6) the scan is
**dispatched to a single background worker thread and the request proceeds** — the finding lands in
the journal 1–5 ms later, and the record is stitched by `call_id`. Under `BLOCK` it must be
synchronous by definition, and the 0.53–4.35 ms is paid. Two postures, two cost profiles, both
stated.

### 2.5 The detector's own false-negative honesty (this is the section that matters)

**Entropy thresholding is far weaker than its reputation, and I measured how weak.**

Shannon entropy per character over a string of length *L* is bounded above by `log₂(L)`. A 24-char
secret **cannot exceed 4.58 bits/char no matter how random it is.** Every entropy threshold is
therefore a length threshold in disguise. Measured, 400 true-random samples per cell:

```
 len  max_possible  base64_meanH  hex_meanH   pass@4.8  pass@4.5  pass@4.0
  16       4.00         3.78        3.21          0%        0%       12%
  20       4.32         4.04        3.36          0%        0%       69%
  24       4.58         4.25        3.47          0%        6%       96%
  28       4.81         4.41        3.55          0%       28%      100%
  32       5.00         4.55        3.60          3%       68%      100%
  40       5.32         4.78        3.70         49%       98%      100%
  48       5.58         4.95        3.75         90%      100%      100%
  64       6.00         5.18        3.82        100%      100%      100%
 128       7.00         5.60        3.91        100%      100%      100%
```

And the false-positive side, over the same real 720 KB `core/` corpus (242 candidate runs):

```
entropy>=3.5: 142/242 flagged (58.7%)     entropy>=4.2:  28/242 (11.6%)
entropy>=4.0:  34/242 flagged (14.0%)     entropy>=4.5:  14/242 ( 5.8%)
                                          entropy>=4.8:   0/242 ( 0.0%)
```

Every single H≥4.0 flag in real repo content is a false positive, and they are boringly explicable:

```
H=4.63 len=76  docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_
H=4.38 len=27  BIFROST_CONSUME_LANE=legacy
H=4.02 len=33  runtime_class/wake_mode/door/caps
```

Long slugified filenames and `KEY=value` env strings look exactly like secrets to an entropy meter.
This repo's own naming convention is an entropy-detector adversary.

**Therefore, three findings a build must not paper over:**

1. **The only zero-false-positive threshold on our corpus (H≥4.8) detects 0–3% of true-random
   secrets shorter than 32 characters, and 49% at 40 characters.** A real AWS `AKIA` access-key id
   (20 chars, uppercase+digits) measures **H=3.72** — below *every* threshold tested. The synthetic
   40-char AWS secret scored 4.73; the 39-char Google `AIza` key scored 4.73; the 40-char GitHub
   `ghp_` scored 4.58. **All three are missed at H≥4.8.**
2. **Entropy is structurally blind to hex.** A 32-char hex session token measures **H=3.44**, and
   the mean for true-random hex never exceeds 3.91 even at 128 characters. `pass@4.0` for hex is
   **0% at every length**. Our own `x-ds-trace-id` values are 32-char hex — the format is normal in
   this ecosystem, and an entropy detector cannot see it at all.
3. **Consequence: entropy is a tertiary hint, not a control.** It goes in as an `INFER`-labelled
   signal at severity `info`, tuned to H≥4.5 **combined with** a structural gate (length ≥ 32,
   charset ⊆ base64/hex, no `/` or `.` separators, not adjacent to a `docs/` or `http` literal).
   It never alone triggers a BLOCK. Anyone who ships an entropy threshold as "we detect secrets" is
   claiming a 0–3% detection rate on the most common secret length.

**What actually works, ranked by measured reliability:**

| Control | Detection | False positives | Verdict |
|---|---|---|---|
| L0 provenance/taint | **complete for file-sourced bytes** (ToolBox is the sole door, `core/comm/toolbox.py:226-239`) | none — it is a fact, not an inference | **primary** |
| L2 structured patterns | high for *known* formats: `sk-`, `sk-ant-`, `AKIA`, `ghp_`, `AIza`, `xox`, `glpat-`, PEM headers, JWT, DSN-with-password | near zero (prefix-anchored) | **secondary** |
| L1 literal prefilter | none by itself — a cost gate for L2 | n/a | optimisation |
| L3 entropy | 0–3% under 32 chars; 0% for hex at any length | 14% at H≥4.0 | **tertiary hint only** |
| Allowlist ("only these shapes may leave") | would be complete | unusable — prompts are natural language | **rejected, see below** |

**Why allowlisting is rejected here even though `gate_rules.py:151` endorses it elsewhere.** The
allowlist grammar works for shell commands because the legal vocabulary is finite and enumerable
(`core/recall/gate_rules.py:169-181` lists ~20 stage shapes). Prompt content is unbounded natural
language plus arbitrary source code; an allowlist over it degenerates to "block everything" and
would be silenced within a week. **The allowlist principle is honoured in a different place: on the
DESTINATION (§5.2), where the vocabulary genuinely is finite — four provider hosts.** That is the
correct application of the repo's own doctrine.

### 2.6 Policy ladder, and why the default is not BLOCK

| Posture | Behaviour | Default for |
|---|---|---|
| `OFF` | no scan | never (but `AKASHIC_WIRE=0` at `scripts/deepseek_chat.py:83` already exists as the global escape hatch) |
| `WARN` | scan off-path, record finding, request proceeds | **super_admin + admin seats** |
| `BLOCK` | scan on-path; a `high`-confidence hit raises before the request is sent | **member / restricted / quarantined seats** |

The asymmetry is deliberate and it is a **contradiction with the fail-open doctrine**, recorded:
`scripts/wire_journal.py:44-47` says telemetry must never take a runner down, and it counts drops.
A BLOCK posture is by definition telemetry that takes a request down. The resolution I propose:
**the recorder stays fail-open; the GUARD is a separate component that fails closed**, and they
share only the detector. If the detector raises, WARN degrades to "record `scan_status: ERROR`" and
BLOCK refuses the request. This mirrors the prior design's own asymmetry at
`api-wire-visibility-design-opus5-2026-08-04.md:474-480` and mirrors `_prewrite`'s existing
fail-closed trust check (`core/comm/toolbox.py:884-886`). Two components, two failure modes, one
detector. Merging them is how you get a telemetry bug that stops the fleet.

---

## 3. (b) BODY CAPTURE WITH REDACTION

### 3.1 Three tiers, not two

The prior design proposed tier 0 (metadata) and tier 2 (full bodies, attended), deliberately leaving
no tier 1 (`api-wire-visibility-design-opus5-2026-08-04.md:259-260`). **I want the tier back, and I
think the argument against it dissolves once redaction is structural rather than textual.**

| Tier | Stores | Default | Sink |
|---|---|---|---|
| **0 — metadata** (shipped) | hashes, usage, headers, timing, + §2.1 destination + §2.2 taint | always on | `state/wire/wire-YYYYMMDD.jsonl` |
| **1 — shape + redacted excerpt** | message-array *skeleton*, per-message role/length/sha/verdict, and a bounded redacted excerpt of **non-tool** messages only | opt-in, safe for long runs | `state/wire/bodies/<agent>/<date>.jsonl` |
| **2 — full body** | request + response bytes, redacted, bounded | `AKASHIC_WIRE_BODIES=1`, **attended only** | same sink, separate `tier: 2` records |

### 3.2 What redaction actually works on a prompt

**Structural redaction beats textual redaction, and the reason is that we own the assembly point.**

A wire proxy sees a flat JSON blob and must regex it. We do not: `scripts/deepseek_chat.py:354,
403-405, 437, 440` shows the message array being built role by role. So redaction operates on
**structure**, where each role gets a different rule:

| Role | Content | Tier-1 treatment | Rationale |
|---|---|---|---|
| `system` | the runner's own prompt, static | **store once per `system_sha`, reference thereafter** | it is our own text, it does not vary, and storing it 22 times/day is the storage defect in miniature |
| `user` | operator/bus text | excerpt head 512 B + tail 512 B, L1–L3 redacted | **highest secret risk** — a human pasting a key rides this lane and `_is_secret` never sees it |
| `assistant` | model output | length + sha + `finish_reason` only | rarely the exfil vector; high volume |
| `tool` | **repo content** | **NEVER stored as text.** Store `{tool_name, args_sha, result_len, result_sha, source_paths_n, taint_classes}` | this is 80–95% of the bytes and 100% of the "we wrote the repo to disk twice" problem |
| `tool_calls` | function name + args | store `name` + **redacted** args (`path` kept, everything else hashed) | the `path` is the forensic value; it is also the taint key |

**The load-bearing claim: dropping `tool` message text costs almost no forensic value.** The
questions a reviewer or a debugger actually asks are *"which file went out, how big, was it a secret
path, did the prompt change between turns, why did the cache miss"* — every one of which is answered
by `{path, len, sha, taint_class}`. Reconstructing the *bytes* is a git operation, not a journal
operation: the repo is content-addressed already. **This is the single decision that makes body
capture affordable**, and it is only available to an in-process recorder, never to a proxy.

Volume: the prior design's estimate of ~16 MB/day for kimi alone (`:314-316`) collapses under this
rule to **per-message metadata**, ~200 bytes/message × ~40 messages/turn × 22 turns ≈ **176 KB/day**
per agent at tier 1. Measured record size at tier 0 today is **684 bytes/record**. Tier 1 is
therefore roughly 2 orders of magnitude cheaper than naive body capture while keeping the answers.

### 3.3 The redactor: rules, and what each one cannot do

```
redact(text) -> (text', findings[])
  R1  structured patterns (L2, §2.3)      -> replace with  [REDACTED:<type>:<sha16>]
  R2  scoped entropy (L3 + structure)     -> replace with  [REDACTED:HIGH_ENTROPY:<sha16>]
  R3  known-key exact match               -> replace with  [REDACTED:OWN_KEY:<name>]
  R4  bounded excerpt (head/tail 512 B)   -> the volume control
  R5  fail CLOSED: on exception, drop the excerpt, keep the metadata, count the drop
```

**R3 is the one control with a provable zero false-negative rate for the threat that matters most.**
We hold our own keys: `KEY_FILE = .secrets/deepseek.key` at `scripts/deepseek_chat.py:53`, and
siblings via `load_key()` in each runner (`scripts/deepseek_chat.py:143`,
`scripts/gemini_chat.py:70`, etc.). The redactor can load them **once at start, keep only their
`sha256`, and match by rolling hash** — so *"did one of OUR five provider keys appear in an outbound
prompt"* is answerable with certainty and without holding the key in the redactor's memory. That is
worth more than every heuristic above combined, because a leaked *provider key* is the specific
incident that costs money and access. **It does not generalise** — it cannot see a key we do not
own, e.g. one a human pastes from a different system.

**Honest false-negative statement for the whole redactor, to be printed in its docstring:**

> This redactor detects: (1) bytes whose provenance is a classified path — completely; (2) our own
> five provider keys — completely; (3) ~20 known third-party key formats — reliably, by prefix;
> (4) unstructured high-entropy strings ≥32 chars in base64 alphabet — partially (49% at 40 chars,
> 3% at 32 chars, 0% for hex at any length, measured). It does NOT detect: secrets shorter than
> 32 characters, hex-encoded secrets, passphrases, secrets the model paraphrased or re-encoded,
> PII of any kind, or proprietary content that is not a credential. **Absence of a finding is not
> evidence of absence.** Every consumer must render `scan_status` (`CLEAN` / `FINDINGS` / `ERROR` /
> `NOT_SCANNED`) alongside the verdict, and `NOT_SCANNED` must never render as `CLEAN` — that is the
> T141 measured-zero defect wearing a security hat.

### 3.4 The prompt hash is a confirmation oracle — a property of the SHIPPED slice

`_sha()` at `scripts/wire_journal.py:72-73` is `sha256(text)[:16]` — **unsalted, unkeyed, truncated
to 64 bits**. This is fine for cache-miss forensics and it is what makes tier 0 safe to ship. But it
has a security property nobody has written down: **anyone who can read the journal and who can guess
a candidate prompt can confirm that prompt was sent.** For short or templated prompts — a bounty
card, a standard boot block, a known handoff — the guess space is small enough to enumerate.

Options, with the tradeoff stated rather than resolved:

- **Keep unsalted (status quo).** Prompt hashes remain comparable **across machines and across
  agents** — which is exactly what makes cross-agent cache analysis and A/B comparison possible.
  Accept the confirmation oracle.
- **HMAC with a per-install key.** Kills the oracle; kills cross-install comparability; adds a key
  to manage, in a repo that has `.secrets/` at mode 0644 (§4.3). Trading one secret for another.
- **Hybrid (my recommendation):** keep the unsalted `prompt_prefix_sha` (the cache-forensics value
  lives entirely in the *prefix*), and make the full-content `prompt_sha` HMAC-keyed at tier 1+.
  Costs one `hmac.new()` per record — sha256 over 720 KB measured at **0.28 ms**, and HMAC is ~2×
  that on the *hashed* content only.

**Contradiction, recorded:** truncating to 64 bits also raises birthday-collision odds to ~50% at
~5×10⁹ distinct prompts. At our volume (tens of thousands of records/season) this is irrelevant, and
I note it only so that nobody later mistakes 16 hex chars for a cryptographic commitment.

---

## 4. (c) RETENTION, ACCESS CONTROL, ENCRYPTION AT REST

### 4.1 What retention exists today, and where it is wrong for bodies

`scripts/wire_journal.py:58-61`: `MAX_FILES = 14`, `MAX_BYTES = 8 MB`, both env-tunable. `_rotate()`
at `:147-161` drops the oldest file when the count exceeds `MAX_FILES`, and drops the oldest **once**
when the newest exceeds `MAX_BYTES`.

Two defects that matter once bodies exist:

1. **`_rotate()` bounds the file COUNT and the NEWEST file's size, never the AGGREGATE.** With
   `MAX_FILES=14` and a single day's file allowed to exceed 8 MB (it only triggers one eviction per
   call, `:158-161`), 14 files × unbounded size is not a bound. At tier 0 (684 bytes/record) this
   is academic. At tier 2 it is a disk-filling defect. **Bodies need a byte-budgeted sink with
   oldest-first eviction until under budget** — a `while total > budget` loop, not a single
   `if`.
2. **`_rotate()` runs `os.listdir` on every single `record()` call** (`:148` → `files()` at
   `:164-170`), inside the lock at `:95`. It is inside the measured 0.291 ms today, so it is not
   currently a problem — but it makes per-record cost O(files in dir), and a body sink will have
   more files. Amortise: rotate every N records or on a size delta.

### 4.2 Retention policy for a store that contains repo content

| Tier | Retention | Bound | Justification |
|---|---|---|---|
| 0 metadata | 14 files (~14 days) | 8 MB/file — raise to a 128 MB aggregate | it is metadata; keeping a season is cheap and enables fingerprint-drift detection across the season |
| 1 shape + excerpt | **7 days OR 256 MB, whichever first** | aggregate, oldest-first | long enough to debug last week's incident |
| 2 full body | **24 hours OR 64 MB**, and **auto-disarm**: the flag reverts on process exit | aggregate | *attended debugging mode*, per the prior design's standing rule (`:348-349`) |

**Bound by BYTES, not days — a day is not a unit of volume.** (Prior design `:333-334`; I concur and
adopt it verbatim.)

**Where the bytes live — verified.** `state/wire/` is doubly gitignored: `.gitignore:50` (`*.jsonl`)
and `.gitignore:108` (`state/*`). The `*.jsonl` negations at `.gitignore:52,55,59,127,129` cover
`tests/fixtures/`, `store/docs/`, `data/corpus-digests/`, `data/play/**/threads/`, and
`_archive/prehistory/` — **none of them reach `state/`**. Confirmed: the capture cannot be committed
by accident today. **A pin must assert this stays true**, because a future negation added carelessly
would publish repo content to a PUBLIC GitHub repo (`balanced7/akashic-aurora`, Apache-2.0). That is
the highest-severity failure mode in this entire document and it is one `.gitignore` line away.

### 4.3 Access control and encryption at rest — the honest section

**There is no encryption available in this repo today.** `grep -rniE "from cryptography|Fernet|AES|
import nacl" core/ scripts/ agent_cli.py` returns **zero hits**. Adding `cryptography` is a new
runtime dependency on a Windows host for a project whose runners must start reliably
(`scripts/deepseek_chat.py:74-77`: *"A runner that cannot start because its instrumentation failed
would be a worse defect"*).

Ranked, cheapest-honest-first:

1. **Filesystem ACL only (recommend for tier 0/1).** `state/wire/` restricted to the owning user via
   `icacls` on Windows; `os.chmod(0o600)` on the files at creation, which is a one-line addition to
   `record()` and costs one `os.chmod` per file creation, not per record. **Verified gap:**
   `.secrets/` itself is currently `-rw-r--r--` (world-readable) on `deepseek.key`, `openai.key`,
   and friends. **We should not build encryption for the wire journal while the plaintext API keys
   next door are mode 0644.** Fixing `.secrets/` permissions is the higher-value, lower-cost move
   and it is a prerequisite, not a competitor.
2. **OS-level volume encryption (recommend, verify).** If `E:` is BitLocker-protected, at-rest
   encryption is already solved for every file including `.secrets/`. **I did not verify BitLocker
   status** (appendix). This should be checked before any application-layer crypto is designed —
   it may make the whole question moot.
3. **Application-layer encryption for tier 2 only (defer).** If tier-2 bodies ever need to persist
   past a session, encrypt the sink with a key held outside the repo. But note the honest circularity:
   the key has to live somewhere, and the somewhere is `.secrets/`, at mode 0644. **Encrypting the
   journal with a key stored next to the plaintext provider keys is theatre.** Fix (1) first.

**Access control on the reader.** Whoever reads the wire journal reads a projection of the repo's
content and structure. The natural control is the one already built: gate the reader verb by
capability. `_agent_acl_caps` at `agent_cli.py:5477-5489` is *only a render gate* (its own docstring,
`:5478-5479`) and reads the ACL file directly rather than going through
`core/trust/registry.py:233` `resolve()` — so it **does not honour expiry** (`registry.py:183-192`
`_expired`) and would keep rendering for `codex_root` after its `2026-08-05T12:00:00Z` lapse. A
security reader must call `resolve()`, not re-parse the JSON. That is a real, small, citable defect
to fix in the same slice.

---

## 5. (d) THE FLEET ANGLE — wire capture as the low-trust-agent monitor

### 5.1 Why this is the design's real payoff

At 10–20 semi-trusted players the question stops being *"is our telemetry good"* and becomes
*"what did that player send outward, and to whom."* The game-arc design already names the concern:
`docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:618` —
*"a smaller surface than 20 players on live keys"*. The trust model has grants
(`security/acl.json`, 11 today) and scoped writes (`Grant.can_write`, `core/trust/registry.py:51-58`)
and a families-only exec gate (`core/comm/toolbox.py:970-1051`). **It has no outbound control at all.**
A quarantined agent — `caps: {READ, BIFROST_INBOX}`, `core/trust/capabilities.py:75-80` — can read
the repo and, if it holds a runner, ship every byte it reads to a third-party inference provider,
and today nothing records that it happened.

### 5.2 EGRESS-2 — the capability, the scope, and the enforcement point

**Add to `core/trust/capabilities.py:13-28`:**

```python
EGRESS = "egress"       # may send bytes to an external inference provider
```

**Add to `Grant` (`core/trust/registry.py:34-63`), mirroring `path_scope` exactly:**

```python
egress_scope: list = field(default_factory=list)      # host allowlist; [] = none, ["*"] = any

def can_egress(self, host: str) -> bool:
    if Cap.EGRESS not in self.caps or not self.egress_scope:
        return False
    if "*" in self.egress_scope:
        return True
    return any(fnmatch.fnmatch(host, s) for s in self.egress_scope)
```

This is a **structural copy of `can_write`** (`core/trust/registry.py:51-58`) — same shape, same
fail-closed semantics, same `fnmatch` idiom, same `[]`-means-none default. That is deliberate: a
security primitive that looks like the one the fleet already understands gets used correctly.

**Role template defaults** (`core/trust/capabilities.py:49-81`):

| Role | `egress_scope` | Effect |
|---|---|---|
| `super_admin` | `["*"]` | unchanged behaviour |
| `admin` | `["api.deepseek.com","api.moonshot.ai","api.openai.com","generativelanguage.googleapis.com"]` | the four hosts we actually use (§1.3) |
| `member` | its own provider host only | a gemini player may reach Google and nothing else |
| `restricted` / `quarantined` | `[]` | **no outbound model traffic** — which is what "quarantined" should have meant all along |

**Enforcement point: the `make_client` factories, and nowhere else.** The check runs **once at client
construction**, not per request:

```python
# core/comm/runner_lib.py:25  (and the two inline factories)
if agent_id and not resolve(agent_id).can_egress(urlparse(base_url).hostname):
    raise PermissionError(f"REFUSED: '{agent_id}' may not egress to {host} (egress_scope)")
```

**Hot-path cost: exactly zero.** `resolve()` is called once per process at client build. The ACL read
is mtime-cached (`core/trust/registry.py:79,90-91`). This is the cheapest security control in the
document and it is the one that actually stops exfiltration rather than describing it.

**And the transport becomes the verifier of its own gate.** With `host` recorded (§2.1),
`expert()` can assert the invariant: *every host in the journal is in the acting agent's
`egress_scope`*. A mismatch means the gate was bypassed — which is exactly the finding a security
reviewer wants and which no amount of pre-flight checking can produce on its own. **The gate is the
control; the journal is the proof the control held.**

### 5.3 ATTRIBUTION-1 — the journal cannot name an agent today

`WireJournal.__init__` (`scripts/wire_journal.py:79-83`) resolves the agent as
`agent or os.getenv("BIFROST_AGENT") or "unknown"`. **All 22 live records read `"agent": "unknown"`.**
A fleet monitor that cannot attribute a request to a player is not a monitor.

Three fixes, all cheap, in increasing order of trustworthiness:

1. **Pass the id explicitly at client construction** — `recording_http_client(agent=agent_id)` —
   rather than relying on an env var the runner may not export. One parameter.
2. **Record `pid` and `argv[0]`** so a record survives a mislabelled agent and can be traced to a
   process. Two scalar reads at journal construction, zero per-record cost.
3. **State plainly that this is SELF-DECLARED identity, not authenticated identity.** The recorder
   lives in the same process as the agent's own code; anything the process can set, the process can
   lie about. `resolve(agent_id, verified=...)` at `core/trust/registry.py:233` already carries a
   `verified` flag — the wire record should carry the same flag, so a reviewer knows whether the
   attribution is a claim or a check. **Never label a self-declared field MEASURED.**

### 5.4 The `GEMINI_BASE_URL` hole, named

`scripts/gemini_chat.py:43-46` reads `BASE_URL` from the environment. An agent that can influence a
runner's environment can point that runner's traffic at any host. Today the wire journal would record
that redirection as an indistinguishable success (no `host` field, §0). With EGRESS-1 + EGRESS-2 it
becomes: the pre-flight `can_egress` check refuses at construction, **and** if the check is somehow
bypassed the journal names the foreign host and `expert()` raises `error`. Defence in depth with two
independent mechanisms, which is the correct shape for a control that guards keys.

---

## 6. (e) WHAT A SECURITY REVIEWER NEEDS THIS JOURNAL TO PROVE

The reviewer's questions, and whether the **current** record shape (`scripts/wire_journal.py:106-145`)
can answer them. Verdicts use the T141 vocabulary.

| # | Reviewer's question | Can today's record answer? | What it would take |
|---|---|---|---|
| 1 | **Where did our data go?** Which hosts received bytes, over what period? | **NO — UNDEFINED.** No `host`/`url`/`method` field exists (verified: `any url-ish key? []`) | EGRESS-1 (§2.1) — ~0 cost |
| 2 | **Who sent it?** Attribution to an agent identity. | **NO — all 22 records say `agent: "unknown"`** | ATTRIBUTION-1 (§5.3) — one parameter |
| 3 | **How much left?** Bytes out per agent per host per day. | **NO.** No `request_bytes`; `prompt_tokens` is `None` in 22/22 records because the transport never sees the body | EGRESS-1 + the usage-stitch the instrumentation dimension owns |
| 4 | **Was a credential in it?** | **NO.** No scan exists | DLP-1/2/3 (§2) |
| 5 | **Which repo content left?** | **NO.** `prompt_sha` is `None` in 22/22 records | taint vector (§2.2) — the only complete answer |
| 6 | **Did an unauthorised agent egress at all?** | **NO.** No capability exists to violate | EGRESS-2 (§5.2) |
| 7 | **Is the record complete, or are there gaps?** | **PARTIAL — and this is the journal's best existing property.** `self.dropped` (`:82,103`) counts swallowed failures and `expert()` reports them (`:271-273`) | keep; add a monotonic `seq` per process so a *deleted* line is detectable, not just a *failed* one |
| 8 | **Was the record tampered with?** | **NO.** Plain appended JSONL, mode 0644, no chaining | a per-line `prev_sha` chain: one extra sha256 over ~684 bytes per record — measured sha256 over 720 KB is 0.28 ms, so over 684 bytes it is **~0.3 µs**. Effectively free, and it converts the journal from a log into evidence |
| 9 | **Does the exported evidence itself leak?** | **N/A today** (metadata only) — becomes live at tier 1+ | §3.3 redactor + §4.2 retention |
| 10 | **Did the control actually run?** | **NO** — and this is the deepest gap. `expert()` has zero callers | §7 pins: a control with no reader has no evidence it ever fired |

**Summary verdict: the current record can prove exactly one security-relevant thing — that N HTTP
round trips occurred with these statuses and these provider trace ids.** That is genuinely valuable
for incident correlation with a provider's support (`x-ds-trace-id` is captured live and appears in
all 22 records). It proves nothing about data movement. **The gap is not in the design; it is that
the security fields were deliberately deferred to this slice.** Item 8 (hash chaining) is the one I
would add even if nothing else lands: it is ~0.3 µs and it is the difference between a log and
evidence.

---

## 7. PINS (pre-registered, RED first — M3)

| Pin | Asserts | Why it must exist |
|---|---|---|
| **S1** | `Authorization`, `api-key`, `x-api-key` never appear in any output byte, asserted over the raw serialised file, with a deliberately-injected header | the allowlist at `scripts/wire_journal.py:65-67` is correct *today*; a pin makes it stay correct |
| **S2** | `request.url.query` never appears in any record, with a URL carrying `?key=SECRET` | some providers accept keys as query params |
| **S3** | **`.gitignore` still excludes `state/wire/**`** — computed via `git check-ignore`, not by reading the file | one careless negation publishes repo content to a PUBLIC repo. Highest-severity pin here |
| **S4** | the redactor **fails CLOSED**: a raising redactor drops the excerpt, keeps metadata, increments a counter; the unredacted bytes are absent from the sink | prior design P5; adopted |
| **S5** | `NOT_SCANNED` never renders as `CLEAN` — the T141 negative pin for the security plane | the measured-zero defect wearing a security hat |
| **S6** | a `quarantined` agent's `make_client` **raises**; a `member`'s foreign-host `base_url` **raises**; a `super_admin` is unaffected | EGRESS-2 is the only control that stops anything |
| **S7** | **the reader is wired**: `expert()` is reachable from a real CLI verb / doctor row, asserted by AST or by invoking the verb | the anti-`cognitive_metrics` pin. Without S7 nothing else in this document is real |
| **S8** | **perf regression gate**: per-turn added latency ≤ 5 ms at the 120 KB delta, measured, failing the build if exceeded | "while retaining performance" is a constraint, so it gets a pin, not a paragraph |
| **S9** | entropy detection is labelled `INFER` and cannot alone raise severity above `info` | prevents the 0–3%-detection-rate control from being cited as proof |
| **S10** | hash-chain continuity: tampering with any line makes `verify_chain()` fail at that line | item 8, §6 |

---

## 8. PERFORMANCE BUDGET (the hard constraint, quantified)

All measured on this machine, Python 3.11, against a real 720,474-byte corpus and the real
`WireJournal` class.

**Baseline, as shipped:** `record()` median **0.291 ms**, p95 **0.725 ms**, max 1.708 ms over 300
calls; with a 720 KB `prompt_text` (two sha256 passes) median **0.631 ms**. Record size **684 bytes**.
`summarize()` over 365 rows: **2.2 ms** (off-path, a reader).

**Added by this design, per API call:**

| Component | Added latency | On the request path? |
|---|---|---|
| EGRESS-1 destination fields | < 0.01 ms (attribute reads) | yes, negligible |
| ATTRIBUTION-1 agent/pid | 0 (set once at construction) | no |
| EGRESS-2 capability check | 0 per request (once per process; ACL mtime-cached, `core/trust/registry.py:90-91`) | no |
| DLP-1 taint vector | < 0.05 ms (a few dozen string appends per turn) | yes, negligible |
| DLP-2/3 delta scan, `WARN` posture | **0 on-path** (background thread) | no |
| DLP-2/3 delta scan, `BLOCK` posture | **0.53 ms** (16 KB tool result) to **4.35 ms** (120 KB `read_file`) | yes |
| Tier-1 structural body record | ~0.2 ms serialisation + one extra file write | yes, small |
| Hash chain (S10) | ~0.0003 ms (sha256 over 684 bytes) | yes, negligible |
| **TOTAL, WARN posture (admin seats)** | **< 0.3 ms** | |
| **TOTAL, BLOCK posture (member/quarantined seats)** | **0.8 – 4.7 ms** | |

**Against what.** Measured TTFT on live traffic: `ms_first_byte` of **638 ms** and **906 ms** in the
first two live records; `p3-ttft-decomposition.json` records TTFT 0.813–0.890 s and total 1.063–1.156 s.

- WARN posture: **< 0.05% of TTFT.** Unmeasurable.
- BLOCK posture worst case: **4.7 ms / 813 ms = 0.58% of TTFT**, 0.41% of total call time.

**Memory:** the content-addressed scan memo at ~2,000 entries × (32-byte key + small verdict) ≈
**< 1 MB**, bounded LRU. The taint vector is per-turn and discarded at turn end.

**Disk:** tier 0 unchanged (684 B/record). Tier 1 ≈ 176 KB/agent/day (§3.2) — i.e. **~100× cheaper
than naive body capture** at kimi's measured volume, and byte-budgeted regardless.

**What I refuse to do for performance, and why:** no sampling of the security scan. A DLP control
that runs on 10% of requests provides 10% of the assurance and 100% of the false confidence. If the
cost is ever too high, the correct lever is the **posture** (WARN vs BLOCK) or the **tier**, both of
which are honest about what they are not doing. Sampling is not.

---

## 9. CONTRADICTIONS, RECORDED NOT RESOLVED

1. **Brief vs HEAD:** the brief cites `agent_cli.py:5464` as the ACL render gate; at HEAD that line
   is in `cmd_toast`. The function is `_agent_acl_caps` at `agent_cli.py:5477-5489`. Characterisation
   correct, line drifted.
2. **Fail-open recorder vs fail-closed guard.** `scripts/wire_journal.py:44-47` mandates fail-open.
   A BLOCK-posture DLP guard is fail-closed by definition. My proposed split (§2.6) — separate
   components, shared detector — is a proposal, not a ruling.
3. **Membrane vs taint.** The taint ledger needs `core/comm/toolbox.py` state to reach a `scripts/`
   recorder. I propose a getter + runner-side pull (§2.2). The membrane's custodian should confirm.
4. **Tier count.** The prior design deliberately refuses a tier 1
   (`api-wire-visibility-design-opus5-2026-08-04.md:259-260`: *"blurring them is how full prompts end
   up on disk forever"*). I propose reinstating it (§3.1) on the grounds that structural redaction
   makes it categorically different from "a smaller tier 2". Genuine disagreement between two designs
   by the same author, four hours apart. The synthesiser decides.
5. **Unsalted vs keyed prompt hashes.** Cross-agent comparability (the whole point of
   `prompt_prefix_sha`) versus the confirmation oracle (§3.4). My hybrid is a compromise, not a
   resolution.
6. **Encryption at rest vs `.secrets/` at mode 0644.** Designing crypto for the journal while the
   plaintext provider keys next door are world-readable is inconsistent. I resolve it by ordering
   (fix `.secrets/` first) rather than by dropping either.
7. **`admin` egress scope.** Listing four provider hosts in a role template hardcodes today's fleet
   into a trust primitive. The alternative — `["*"]` for admin — makes the control vacuous for the
   seats with the most access. I chose the enumeration; it will need maintenance, and maintenance
   burden is how allowlists rot.

---

## 10. (f) WHAT THIS DESIGN DOES **NOT** PROTECT AGAINST

Stated plainly, because a security document that only lists what it catches is marketing.

1. **Any egress that does not go through the four `make_client` factories.** The transport hook only
   sees the OpenAI SDK's httpx client. **`scripts/gemini_web.py` drives a full Chrome via Playwright
   (`:23,102-115`) — every byte it sends is invisible to this design.** So is
   `ToolBox.web_search` (`core/comm/toolbox.py:1107-1116`, which shells to
   `scripts/local/websearch.py`). So is any `import requests` inside a test.
2. **The pytest exec family is arbitrary code execution.** `core/comm/toolbox.py:986-989` runs
   `pytest` with `_AISETUP_TEST_ISOLATED=1` and nothing else; the file's own comment at `:1018` says
   *"Containment is COMMIT hygiene, not sandboxing (the pytest family already runs repo code)"*.
   An agent holding `WRITE` to `tests/*` (which `codex_root` holds, `security/acl.json`) plus `EXEC`
   can write a test that reads `.secrets/deepseek.key` and posts it anywhere. **The wire journal
   would not see it and EGRESS-2 would not stop it.** This is, in my judgement, a larger hole than
   anything this document closes, and it is out of scope for the wire journal by construction.
3. **A malicious in-process recorder.** The journal runs inside the agent's own process. Code that
   can call the API can disable the recorder — `AKASHIC_WIRE=0` (`scripts/deepseek_chat.py:83`) is a
   documented off switch, and even without it, a process can build its own `OpenAI()` client. **This
   design assumes a semi-trusted, non-adversarial agent. It is a monitor, not a sandbox.** The
   correct control against a genuinely hostile agent is process isolation with an enforced network
   namespace, which this architecture does not have.
4. **Self-declared identity.** §5.3: the `agent` field is whatever the process says it is.
5. **Semantic exfiltration.** A model asked to "summarise the auth module" ships the *meaning* of
   the auth module. No pattern, no entropy threshold, and no taint class distinguishes legitimate
   work from staged disclosure. Taint tells you the file was read; it cannot tell you why.
6. **The provider itself.** Everything here is about what leaves *our* machine. Once bytes reach
   `api.deepseek.com`, retention, training use, and subpoena exposure are governed by a contract, not
   by code. The journal makes the volume visible; it changes nothing about the destination's conduct.
7. **Secrets we don't own, under 32 characters, or hex-encoded.** Measured, §2.5: 0–3% detection
   under 32 chars for base64; **0% for hex at any length**; a real 20-char AWS `AKIA` id scores
   H=3.72, below every threshold.
8. **Historical leakage.** Everything already sent — including the 3.9 M prompt tokens kimi shipped
   on 2026-08-02 — is unrecoverable and unaudited. This design starts the clock; it cannot rewind it.
9. **Journal integrity before S10.** Plain appended JSONL at mode 0644. Any process on the machine
   can rewrite it. Hash chaining (§6 item 8) makes tampering *detectable*, not *preventable*.
10. **The reader problem.** If S7 does not land, none of this fires. `expert()` has zero callers
    today, and that is the failure mode this project has already documented twice
    (`core/coord/cognitive_metrics.py`: 12 of 16 functions dead, `dump()` called only by tests).
    **The most likely way this design fails is not a bypass. It is that it gets built and nobody
    reads it.**

---

## APPENDIX: WHAT I DID NOT VERIFY

**Measured and reproducible (do trust these):**
- `record()` timings, DLP scan timings, entropy tables, prefilter timings — all run on this machine
  against real `E:\AI-Setup\core\**` content and the real `WireJournal` class. Bench scripts are in
  the session scratchpad (`dlp_bench.py`, `dlp_bench2.py`, `entropy_fn.py`, `rec_bench.py`); they are
  temporary files, not repo artifacts, and will not survive the session.
- The 22 live records in `state/wire/wire-20260804.jsonl` — read and field-counted directly.
- Every `file:line` citation in §1 through §5 — opened and read, not grepped-and-assumed, except
  where noted below.

**Read but not executed:**
- `core/comm/toolbox.py` — I read lines 180-360 and 840-1090 in full. **I did not read the other
  ~700 lines**, so there may be additional egress or secret-handling surfaces I have not seen.
- `scripts/deepseek_chat.py` — I read the client factory and the tool-result loop
  (`:396-445`). I did not read the streaming assembly (`_stream_turn`, ~`:295-345`) in full.
- `agent_cli.py` — I read `:5440-5489` only. It is ~5,500+ lines; there may be other ACL readers.

**Not verified at all:**
- **Whether `E:` is BitLocker-encrypted.** §4.3's recommendation ordering depends on this and I did
  not check. This should be the first thing anyone confirms.
- **Actual file ACLs on `state/` and `.secrets/` on Windows.** I read the `ls -l` mode bits through
  Git Bash (`-rw-r--r--`), which is a POSIX *emulation* of Windows ACLs and can be misleading. The
  authoritative check is `icacls`. My claim that `.secrets/` is world-readable rests on that
  emulated view and should be re-checked with `icacls` before being acted on.
- **Whether any of the four provider hosts is reached by a code path I did not find.** I grepped
  `BASE_URL`/`base_url=` across `scripts/` and `core/`; a URL constructed by string concatenation
  would not appear.
- **`scripts/local/websearch.py`** — referenced at `core/comm/toolbox.py:1110` but I did not open it,
  so I cannot say what it sends or where.
- **The kimi/gemini/sol runner loops.** I verified their `make_client` factories are uninstrumented;
  I did not verify their message-assembly paths match deepseek's, so §1.2's taint path is confirmed
  for the deepseek runner and **INFERRED** for the other three.
- **Whether `httpx` event hooks (the prior design's tier-0 mechanism) can see `request.content` for
  a streaming request** — relevant to whether DLP can hook the transport rather than the assembly
  point. I designed around the assembly point specifically to avoid depending on this, but it was
  not tested.
- **Any pin in §7.** They are pre-registered, not written and not run.
- **Cross-check with the other five WIRE-B dimensions.** Written in isolation by design; overlaps
  and conflicts with the instrumentation, storage, UI, and analysis dimensions are the synthesiser's
  to reconcile.

**Deliberately not done:** no code written, no file modified other than this one, no commit, no bus
send, no ledger write.
