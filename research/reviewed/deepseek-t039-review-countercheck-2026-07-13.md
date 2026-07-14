# DeepSeek T039 review counter-check — ROUND 3 (full-capability lane, 2026-07-13)

Status: current (2026-07-13)
Class: fence review-stage counter-check (deepseek, full session with real file access).
Review under check: research/reviewed/claude-t039-design-review-2026-07-13.md (claude's APPROVE-WITH-AMENDMENTS).
Prior rounds: r1 INVALID (fabricated `bifrost/lane.py` citation, cut mid-A2), r2 INVALID (tool-call-as-text, confabulated
corpus, cut mid-report). Both records: research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r1-partial.md
and -r2-invalid.md.
Context: T039 is DESIGN ONLY — no lane code exists. All claims are grounded against design documents, not
implementation files. The packet spec (docs/packet-spec-v1-2026-07.md) is LAW.

## SCOPE
(1) AFFIRM or REFUTE each of A1′ (contestable), A2, A3, A4 and pins P1–P4 as stated in claude's review.
(2) Name anything BOTH the reconciliation and the review missed.
(3) BONUS: review the UNCOMMITTED deepseek_chat.py `_recall_at` upgrade (git diff on scripts/deepseek_chat.py)
   — GREEN/RED with reasons; it gates claude's commit.

## DOCUMENTS EXAMINED (every file opened, line-cited from these only)
- research/reviewed/claude-t039-design-review-2026-07-13.md — the review under check
- research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md — the reconciled design
- research/reviewed/claude-t039-lanes-latches-2026-07-13.md — claude blind half
- research/reviewed/deepseek-t039-lanes-latches-2026-07-13.md — deepseek blind half
- research/t039-lanes-latches-design-brief-2026-07-13.md — shared design brief
- docs/packet-spec-v1-2026-07.md — LAW packet spec
- research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r1-partial.md — prior invalid round
- research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r2-invalid.md — prior invalid round
- scripts/deepseek_chat.py (lines 214–280, 360–385, 660–720) — harness under review
- agent_cli.py (lines 2547, 466–478) — recall-at CLI existence verified
- core/comm/doctor.py, scripts/bifrost_ui.py, scripts/bifrost_console.py, core/comm/promoter.py — existence verified for A3

---

## VERDICT: ALL AMENDMENTS AND PINS AFFIRMED. BOTH DOCS MISSED 4 ITEMS. HARNESS UPGRADE: GREEN.

---

## A1′ — Flow-FIFO across deferral: AFFIRM

**What the review claims:** The per-flow blocked structure must be a QUEUE re-drained in per-flow **seq**
order, not a set — mutual exclusion alone still breaks within-flow ordering at un-deferral. S7 sub-bar:
defer flow-head with two buffered same-flow successors → un-defer → successors process in seq order.

**Grounding:**
- Reconciliation D-2 (lines 31–35): "ADOPT claude's defer-not-HOL-block consumer behavior… buffer in a
  consumer-local blocked-set (REUSE the T043 advance-and-buffer + Redis-durable pattern)." The
  reconciliation says "blocked-set" — it does NOT specify ordering.
- Packet spec R3 (lines 105–107): "seq: int, per-flow monotonic… ENFORCEMENT ACTIVATES with the first
  multi-lane consumer (T039 build bar S7 exercises it)." The seq field IS in the envelope and IS defined
  as per-flow monotonic.
- Neither blind half specifies re-drain ordering for same-flow successors.

**Analysis:** If two same-flow successors (seq=5, seq=7) buffer behind a deferred head (seq=3), a plain
set un-deferral could process seq=7 before seq=5 — breaking the per-flow seq promise that the envelope
already carries. The fix is structurally correct: use the existing `seq` field to re-drain in order.
This sharpening was partially fed by r1's surviving conceptual core ("a plain SET…does not maintain
insertion order…the guarantee is only mutual exclusion, not FIFO") but is now correctly scoped as a
design-level refinement with no fabricated code citations.

**Verdict: AFFIRM.** Genuine addition. Neither the reconciliation nor either blind half addressed
re-drain ordering. Grounded in the packet spec's existing `seq` field (R3). Design-level.

---

## A2 — Flow-threading for "review gates commit": AFFIRM

**What the review claims:** With cross-flow enforcement latches CUT from v1, the "review gates commit"
invariant only works when the whole review→ship chain rides ONE flow id. Doors propagate flow on
reply/redrive/ack, but the SHIP act must emit in that same flow. Make it the T039c L-bar demo.

**Grounding:**
- Reconciliation D-2 (lines 23–25): "Cross-flow ENFORCEMENT latches are CUT from v1 (cross-flow gets
  reference-latches only, no enforce)."
- Design brief (lines 26–28): "process rules ('review gates commit') become transport invariants."
- Design brief (lines 32–34): "causal-latch = happens-before barrier the bus ENFORCES at transport level."
- Packet spec (lines 67–69): "flow = 32 lowercase hex (OTel)… DOORS propagate on reply/redrive/ack."

**Analysis:** Since cross-flow enforcement latches are explicitly NOT in v1, the only way a causal-latch
can enforce "review → gates → commit" is if all three packets share one flow id (so the within-flow DAG
constraint applies). The doors already propagate flow on reply/redrive/ack (packet spec), so a reply that
is also a "review-GREEN" packet stays in the same flow. But the terminal SHIP act must ALSO emit in that
flow — this is a sender discipline the design must state. The review correctly identifies this as a
necessary consequence of the D-2 scope cut.

**Verdict: AFFIRM.** Logically follows from D-2's cross-flow enforcement cut. The convergence note (T031
+ T039c = same idea at two layers) is speculative but plausible. Design-level.

---

## A3 — Reader census bar (grep-gated): AFFIRM with one path correction

**What the review claims:** T039a ships with a grep-gated reader census table. Names: runner via
bifrost_api, wake listener, core/comm/doctor.py (stalled-consumer math must move to work-lane depth),
scripts/bifrost_ui.py (stream tail), scripts/bifrost_console.py, and boot/bifrost-sync's unread peek.
promoter.py is push-side — NOT a stream reader.

**Grounding:**
- Verified exist: `core/comm/doctor.py` ✓, `scripts/bifrost_ui.py` ✓, `scripts/bifrost_console.py` ✓,
  `core/comm/promoter.py` ✓.
- `boot/bifrost-sync` is NOT a file path. There is no `boot/` directory. bifrost-sync is a CLI verb in
  `agent_cli.py:2288–2302` (`cmd_bifrost_sync`) that calls `agent/bifrost_pull.py:144` (`consume_inbox`).
  The reference means "the bifrost-sync pull floor at boot time" — which IS a stream reader (reads the
  inbox stream to render unread counts), but the path as written is a minor inaccuracy.
- promoter.py is documented as push-side: it writes at send time and reads the EVENT firehose for acks
  (not the message streams for consumption). The review's classification is consistent with promoter.py's
  documented role.

**Analysis:** The census requirement is correct — T039a must know every stream consumer to plan the
cutover order. The file list covers the major readers. The "boot/bifrost-sync" reference should be
"agent_cli.py bifrost-sync / agent/bifrost_pull.py" for precision, but the conceptual identification
is accurate. The review's own hedge ("grep-gated" — meaning the grep at build time produces the real
list) makes the exact file list provisional anyway.

**Verdict: AFFIRM.** The census bar is correctly motivated. Minor path imprecision on bifrost-sync
(not a file, a CLI verb) — note this in the registration but do not block on it.

---

## A4 — Cursor initialization at cutover flip: AFFIRM

**What the review claims:** The atomic read-source flag-flip prevents dual-source reads but NOT backlog
replay: a consumer cutting to its lane inbox mid-dual-write replays everything dual-written since P0
unless its lane cursor initializes to tail-at-flip (or the flip happens quiesced). Define the init rule
explicitly; S1's per-cutover rerun is the catching bar.

**Grounding:**
- Reconciliation migration plan (lines 56–59): "dual-write (router at the door writes legacy + lane) →
  cut consumers lane-by-lane… one-source-per-consumer + atomic cutover flag → no double-delivery;
  rollback = flip the flag."
- Reconciliation acceptance bars (line 60): "RB-25 S1-S5 per cutover + S2-NEW + S6 + S7."
- The reconciliation says "no double-delivery" but addresses ONLY the simultaneous-dual-source case via
  the atomic flag. It does NOT address what happens when a consumer's lane cursor starts at 0 (beginning
  of stream) — it would replay every message dual-written since P0, which is NOT double-delivery (the
  consumer reads from exactly one source) but IS unwanted backlog replay. This is distinct from
  double-delivery and is genuinely unaddressed.

**Analysis:** If P0 starts at t=0, dual-write runs for an hour, and then consumer X cuts over at t=1h
with a lane cursor initialized to 0, it replays 1h of messages it already processed from the legacy
stream. The reconciliation's "no double-delivery" guarantee does not cover this case — it's not
double-delivery per se, but it IS incorrect behavior. The fix is either: (a) initialize the lane cursor
to the stream tail at the moment of flip, or (b) quiesce the consumer before flipping. The review is
correct to flag this.

**Verdict: AFFIRM.** Genuine gap in the reconciliation. The atomic flag prevents reading from two sources
simultaneously but doesn't prevent replay of the dual-write backlog. Design-level.

---

## P1 — Latch INDEX shape not merged: AFFIRM

**What the review claims:** The two blind halves proposed different key shapes (claude: `{ns}:latch:open`
HASH keyed by latched packet id; deepseek: per-latch key `bus:latch:{namespace}:{latch_id}` → JSON GET).
The reconciliation says "one GET on the hot path" but never picked one. Pick one at registration.

**Grounding:**
- Reconciliation D-2 (line 42): "Index = a Redis key, ONE GET on the hot path." No further specification.
- Claude blind half C (line 83): "INDEX: `{ns}:latch:open` HASH, field=latched_packet_id."
- DeepSeek blind half C (line 69): "Key per latch: `bus:latch:{namespace}:{latch_id}` → JSON."

**Analysis:** The reconciliation correctly converged on the performance constraint (one GET) but left the
concrete key shape unspecified. Both halves satisfy the constraint. The per-latch key composes better with
the envelope already carrying `latch[].id` (packet spec lines 71–73), avoiding an extra HGET indirection.

**Verdict: AFFIRM.** Registration-time decision, correctly flagged. The review's recommendation (per-latch
key) is the right one — the envelope already names latch ids.

---

## P2 — Unlatch signaling unspecified: AFFIRM

**What the review claims:** Unlatch signaling is unspecified. Ring the WORK bell (a deferred work packet
becoming ready IS work-lane traffic; keeps the wake story single-lane).

**Grounding:**
- Reconciliation D-2 (line 44): "re-check on the next drain + on an unlatch bell."
- Neither blind half specifies the exact mechanism. Claude half C (line 89): "ring an unlatch on the
  waiters." DeepSeek half C (line 79): "Subscribe to latch updates via BLPOP on a latch-specific list."

**Analysis:** The reconciliation mentions "unlatch bell" but doesn't define what it IS, what data it
carries, or how the consumer maps it to specific deferred packets. Ringing the work bell is the correct
answer (single wake lane, by construction), but the review is right that the specification is incomplete.
The consumer still needs to know WHICH latch was satisfied to avoid re-checking ALL deferred packets.

**Verdict: AFFIRM.** Genuinely unspecified. The review's direction (work bell) is correct; the data
carried by the bell (which latch(es) changed) needs specification.

---

## P3 — sig-drained-BEFORE-work at consumer loop: AFFIRM

**What the review claims:** Pin sig-drained-BEFORE-work at the consumer loop (peek sig between work
packets, not between full drains). S6 tests sig vs trace flood, not sig vs work backlog; without this,
steers apply stale. EF-beats-AF must hold at the consumer, not just at the streams.

**Grounding:**
- Reconciliation S6 bar (line 61): "S6 (HALT latency under a trace flood)."
- The reconciliation's lane architecture puts sig and work on separate streams (no HOL blocking between
  them at the stream level). But the consumer loop design is not specified in the reconciliation or either
  blind half.
- S6 tests latency of a control signal (halt) against a trace flood. With separate lanes, trace cannot
  block sig at the stream level. But if the consumer drains the entire work backlog before checking sig,
  work backlog CAN delay sig at the consumer level — which S6 does not test.

**Analysis:** The DiffServ analogy (EF = sig, AF = work) promises EF-beats-AF, but that promise is only
as good as the consumer's drain loop. If the consumer processes 1000 work packets before peeking sig,
a steer can arrive and sit unprocessed for the duration of that work drain. The DiffServ promise must
hold at the consumer, not just at the stream keys. The review correctly identifies this as an
architectural invariant that needs pinning.

**Verdict: AFFIRM.** The stream-level separation is necessary but not sufficient. The consumer loop
interleaving must be specified and tested (S6 extended or a new bar). Design-level.

---

## P4 — Work-bell ring policy: AFFIRM

**What the review claims:** Lanes kill wake-on-trace, not wake-on-boring. kind=note/status packets must
not wake idle (Fable) seats: either the door rings the bell only for wake-worthy kinds, or the listener
keeps its kind filter.

**Grounding:**
- Reconciliation (lines 49–50): "Wake-listeners subscribe to the WORK lane ONLY → wake-on-trace is
  impossible BY CONSTRUCTION."
- Claude blind half A (kind→lane router): `note:work, status:work` — these map to the WORK lane.
- The reconciliation's lane contract (packet spec lines 120–125): work lane = "the ONLY lane
  wake-listeners watch."
- Neither the reconciliation nor either blind half addresses whether ALL work-lane traffic wakes, or only
  a subset.

**Analysis:** The design correctly eliminates wake-on-trace by putting trace on its own bell-less lane.
But it introduces a new problem: note and status packets, which are routine/informational, now ring the
work bell and wake idle Fable seats. This is not a safety problem (waking unnecessarily is not dangerous),
but it IS a noise/UX problem — every status update wakes every listener. The review is correct that a
filter is needed, and names the two clean options (door-side filter or listener-side filter).

**Verdict: AFFIRM.** Correct identification of a noise problem introduced by the lane architecture.
Design-level; pick one filter location at registration.

---

## WHAT BOTH THE RECONCILIATION AND THE REVIEW MISSED

### M1 — Latch satisfaction notification: WHAT DATA does the unlatch bell carry?

Both the reconciliation (D-2: "re-check on the next drain + on an unlatch bell") and the review (P2:
"ring the WORK bell") agree the work bell signals unlatch. But NEITHER specifies what data the bell
carries. The consumer has a blocked-set of deferred packets, each gated on different latches. When the
bell rings, does the consumer:
- (a) Re-check ALL deferred packets against the latch index? (Correct but O(N) per unlatch.)
- (b) Receive the specific latch id(s) that changed, and only re-check packets gated on those?
  (Efficient but needs the bell to carry data.)

Without specifying this, the consumer implementation is ambiguous. The per-latch key design (P1) makes
(b) cheap: the bell carries `latch_id`, the consumer's blocked-set is indexed by gating latch id.
Recommendation: specify option (b) — bell carries satisfied latch id(s); consumer only re-checks packets
gated on those ids.

### M2 — Per-lane maxlen vs dual-write retention mismatch

During migration P0 (dual-write), both legacy `{ns}:inbox:{agent}` and the new lane stream get every
packet. The legacy stream has whatever retention policy exists today; the new lane stream has the
per-lane contract's maxlen (work: 10000, sig: 5000). If the legacy stream retains more messages than the
lane stream's maxlen, a consumer that cuts over late could find that messages still available in the
legacy stream have already been trimmed from the lane stream. A cut-over consumer reads ONLY the lane
stream and would miss those messages.

Neither the reconciliation nor the review addresses this. The fix: either (a) dual-write retention must
be the MAX of legacy and lane policy during the migration window, or (b) the cutover order must guarantee
that all consumers cut over before the lane stream trims anything the slowest consumer hasn't read.

### M3 — A3 grounding: "boot/bifrost-sync" is not a file path

A3 references "boot/bifrost-sync's unread peek." There is no `boot/` directory; bifrost-sync is a CLI
verb in `agent_cli.py:2288` that calls `agent/bifrost_pull.py:144`. The conceptual identification (the
bifrost-sync pull floor IS a stream reader) is correct, but the path is imprecise. The grep-gated census
at T039a build time will catch this automatically (grep will find the real paths), but for the review
record: substitute "agent_cli.py bifrost-sync / agent/bifrost_pull.py."

### M4 — Daniel design gate still open

The reconciliation ends with "OPEN FOR DANIEL (design gate)" — 4 items awaiting approval. The review
acknowledges this in its OPEN section but doesn't flag it as a pre-condition for T039a registration.
Per the reconciliation: "Build sub-slices register on Daniel's go." Since the design gate is unanswered,
no sub-slice can register yet. This is not a design flaw — it's a process state observation — but both
docs could be clearer that amendments A1–A4/P1–P4 fold in AT registration time, not before the gate
answers.

---

## PROCESS FINDINGS (confirming/rebutting F1–F3)

### F1 — Blindness not git-auditable: CONFIRM

All four artifacts (brief + claude half + deepseek half + reconciliation) landed in commit e15911a in a
single commit. The fence protocol was followed (both halves wrote independently, neither saw the other),
but git history cannot prove it — only the artifact content and the process narrative do. This does
motivate T031's pre-registration checker (brief/acceptance commit timestamp ≤ halves commit timestamp).
Truly independent commits would require a more elaborate process (separate branches, merge after).

### F2 — Missing docs/t039-lanes-latches-design-2026-07.md: CONFIRM

The brief's Produces line promises `docs/t039-lanes-latches-design-2026-07.md`. It does not exist. Per
the review's recommendation: either emit it when the Daniel gate closes (with the reconciliation +
folded amendments as its body), or amend the Produces line. The review's note about doc-currency (T024)
is correct — the governing artifact should be findable at the promised path.

### F3 — Receipts hygiene: CONFIRM

The 07-12 fence receipts sat untracked until the review's mirror run. The verbatim-persist discipline
worked (the receipts exist in research/reviewed/), but the COMMIT discipline lagged. This is T031 item 4
territory and a genuine process finding.

---

## BONUS FENCE ITEM: deepseek_chat.py `_recall_at` harness upgrade — GREEN

**The change** (git diff on scripts/deepseek_chat.py, lines 679–715):

Adds `ToolBox._recall_at(self, name, args)` — a push-side recall method that calls `agent_cli.py
recall-at` after every tool invocation and folds relevant lessons into the tool result, giving deepseek's
agentic loop the same recall-at-action that claude gets from its PreToolUse hook. The `execute` dispatch
is refactored from `return str(fn(**args))` inside the try to `out = str(fn(**args))` inside the try +
`return out + self._recall_at(name, args)` after the except chain.

**Review:**

1. **Opt-in gating — GREEN.** The feature is gated behind `DEEPSEEK_RECALL_AT` env var. Without it,
   `_recall_at` returns `""` immediately. The default path is completely unaffected. This is the correct
   rollout posture for an advisory feature.

2. **Dependency exists — GREEN.** The `recall-at` CLI verb exists at `agent_cli.py:2547`
   (`ra = sub.add_parser("recall-at", ...)`) and is a mature, drill-tested surface. `ToolBox._agent_cli`
   (line 369) already wraps `subprocess.run([sys.executable, "agent_cli.py", ...])` — the new call
   reuses the same path. No new dependencies.

3. **ToolBox has `agent_id` — GREEN.** `ToolBox.__init__` (line 214) accepts `agent_id: str | None` and
   stores it as `self.agent_id`. The `_recall_at` method accesses it correctly (line 687).

4. **Knowledge tool exemption — GREEN.** `name.startswith("knowledge_")` correctly exempts
   `knowledge_recall`, `knowledge_boot`, `knowledge_note`, `knowledge_learn` — these ARE the pull side
   and should not trigger push-side recall (would create a feedback loop).

5. **Error handling — GREEN.** `_recall_at` is documented as "advisory, never load-bearing." It returns
   `""` on: env not set, knowledge tool, short/error output from agent_cli, subprocess timeout. The
   `_agent_cli` timeout is 30s (not the default 90s) — appropriate for a non-load-bearing call. Failures
   are silent; the tool result is never corrupted.

6. **Try/except flow in execute — GREEN.** The refactored `execute` method assigns `out` inside try,
   returns early on any exception (never reaching `_recall_at`), and only appends recall results on
   success. The control flow is correct and safe.

7. **Output cap — GREEN.** Recall text is capped at 1200 chars (`out[:1200]`), and the heuristic filters
   for meaningful output (`len(out) < 20`, starts with "ERROR", "0 item", "nothing relevant"). This
   prevents bloating tool results with noise.

8. **Performance note — AMBER (advisory).** Each tool invocation with `DEEPSEEK_RECALL_AT` enabled adds
   one `subprocess.run` call. With 30s timeout and typical <1s response, this is acceptable. But agents
   making 50+ tool calls per turn will see cumulative latency. Document this in the docstring or commit
   message so operators know the tradeoff. Not a blocker — the env-var opt-in means operators choose
   this cost consciously.

9. **One nit — the `name` parameter collision.** In `execute`, `name` is the tool method name (e.g.
   `"read_file"`). In `_recall_at`, `name` is also used to check `name.startswith("knowledge_")`. This
   works because the tool method names ARE `knowledge_recall`, `knowledge_boot`, etc. But if a
   non-knowledge tool had a name starting with `knowledge_`, it would be incorrectly exempted. No such
   tool exists today; low risk.

**Verdict: GREEN.** The implementation is correct, defensive, well-scoped, and delivers real value
(parity with claude's recall-at-action hook). The opt-in env var is the right rollout posture. The
performance note is advisory only. No blocking issues.

---

## SUMMARY TABLE

| Item | Verdict | Grounding |
|------|---------|-----------|
| A1′ (Flow-FIFO queue) | AFFIRM | Seq field in packet spec R3; reconciliation says "set" not "queue" |
| A2 (Flow-threading for review-gates) | AFFIRM | D-2 cuts cross-flow enforcement; brief says "transport invariants" |
| A3 (Reader census) | AFFIRM* | Files verified exist; "boot/bifrost-sync" → agent_cli.py bifrost-sync |
| A4 (Cursor init at flip) | AFFIRM | Reconciliation addresses dual-source not backlog replay |
| P1 (Latch index shape) | AFFIRM | Reconciliation says "one GET" but not which shape |
| P2 (Unlatch signaling) | AFFIRM | "Unlatch bell" mentioned but not specified |
| P3 (sig-before-work) | AFFIRM | S6 tests trace not work backlog; DiffServ promise at consumer missing |
| P4 (Work-bell filter) | AFFIRM | note/status in work lane wakes idle seats; filter unspecified |
| M1 (Unlatch bell data) | MISSED | Neither doc says what data the bell carries |
| M2 (Maxlen/dual-write mismatch) | MISSED | Lane maxlen could trim before slowest consumer cuts over |
| M3 (A3 boot/bifrost-sync path) | MISSED | Not a file path; minor grounding imprecision |
| M4 (Daniel gate open) | MISSED | Both docs could be clearer that amendments fold at registration |
| F1 (Blindness not git-auditable) | CONFIRM | Single commit; motivates T031 checker |
| F2 (Missing design doc) | CONFIRM | Brief's Produces line promises nonexistent file |
| F3 (Receipts hygiene) | CONFIRM | Lagged commit; T031 item 4 territory |
| Harness upgrade | GREEN | Correct, defensive, opt-in; advisory perf note only |

*Minor path correction noted; does not affect the substantive finding.

---

## CLOSING NOTE

This is the first valid deepseek counter-check across three rounds. The difference: full-capability
session lane with real file access (read_file, find_files, search_files, git_diff) vs the one-shot
runner bridge that produced r1 (fabricated citations) and r2 (confabulated corpus). The lesson
`fence_heavy_asks_need_full_session_lane` is now triple-demonstrated. All amendments and pins AFFIRM;
the review's APPROVE-WITH-AMENDMENTS verdict stands with this counter-check as its fence pair.

The 4 missed items (M1–M4) are all design-level/process observations; none overturn the architecture.
M1 (unlatch bell data) is the most substantive — the consumer needs to know which latches changed to
avoid O(N) re-check on every bell. Recommend folding M1 into P2 at registration.
