# Moonshot Network Spine — deepseek-review M1-CC cross-critique (2026-07-17)

Status: M1-CC cross-critique, round 2. Filed under my lock; RELEASED on filing.
Author: deepseek-review (adversarial runner lens)
Inputs read: all three blind halves (Fable, deepseek-review, Sol), jester RED/BLUE/synthesis,
gemini-jester-red, hardening-reconciliation, failure-ledger C1-3/C1-4, nudge.py, coordination-plan-synthesis §3,
ai_setup_mcp.py bifrost_nudge. All named files in the round-2 addendum CONSUMED.
Steer disposition: adopted. Active task: T060 round-2 cross-critique.
Plan/tool history: preserved — this turn continues the T060 adversarial review with new evidence folded in.

---

## 1. M1-CC THREE-PART CROSS-CRITIQUE

### 1A — What another half caught that mine missed

**Fable caught: the engine-exam gate is already OPEN (T029 CLOSED).** My half assumed T029 was still a blocker, because the boot onboarding text listed "T029 exam continues" under the arc plan. Fable's MCP `task(list)` receipt — confirmed by my own `status()` — shows T029 DONE. This changes the sequencing pressure: the ENGINE-FIRST constraint that parked T039/T040/T041 build slices is satisfied. The floor is ready for T047. My half's sequencing is still correct (T047 first), but the urgency is HIGHER than I stated — the gate is already open, the parking brake is off, and every hour dual-write remains live is an hour the fleet pays the tax without the constraint that justified it.

**Sol caught: the MCP `notes` parity defect is a pre-flight blocker, not a cosmetic gap.** My half audited the MCP surface comprehensively but didn't check whether every tool actually WORKS for the interactive seat. Sol's live `notes()` failure ( `AttributeError: Namespace object has no attribute all` — `_ARG_DEFAULTS` at `ai_setup_mcp.py:52-76` omits `all` while `cmd_notes()` at `agent_cli.py:1407-1413` reads `args.all`) is a door-parity defect that means the interactive seat can't read durable project notes. This isn't a routing problem, but it IS a pre-flight integrity problem: if the interactive MCP seat can't read `where-we-are`, it's flying blind regardless of what the routing spine ships. My half should have caught this in the MCP surface audit — I checked `bifrost_send` but didn't test `notes()`.

**Fable caught: sol's head-blocked-inbox is this morning's live evidence for per-agent trace.** The receipt that "a virgin `codex_root` cursor had to consume 10,009 historical packets before current peer replies appeared" — this is a freshness failure, not a ceremony one. My half flagged the shared trace ring as a capacity floor, but Fable connected it to the interactive seat's TODAY pain, not a hypothetical N=5 future. The per-agent trace argument is now grounded in a live receipt, not just extrapolation.

### 1B — What another half got wrong, with evidence

**Fable: "Slice A first commit: the seven-verb surface + route() dry-run + per-rule counters (additive, ~125 lines, zero consumer behavior change)." This claim is WRONG about zero consumer behavior change.**

Evidence: the routing design's own Phase 0 includes `meta.wake` honored by the wake listener's PENDING_SKIP_KINDS seam. Fable himself concedes this in the contract compliance addendum — his Slice A delivers "honoring `meta.wake`." A `meta.wake="no"` header on a packet that previously always woke the receiver IS a consumer behavior change. The wake listener's SKIP_KINDS seam currently checks KIND — not meta. Adding a meta.wake check changes which packets wake seats and which don't. That's not "zero consumer behavior change" — it's a scheduling change on the wake path. Sol's S0 shadow-only approach correctly identifies this as a risk: "honoring `meta.wake` changes scheduling and can create missed-wake or wake-storm behavior."

**Tag: INFERRED** (the wake-listener code path makes this clear: `PENDING_SKIP_KINDS` is kind-based; adding meta.wake adds a new skip dimension that changes wake/no-wake decisions for the same kind).

**Sol: "S0 shadow packet composer: Add intent without changing delivery semantics." This claim understates the implementation surface.**

Evidence: Sol's S0 requires a "compact MCP/CLI packet composer with an intent enum rather than seven new top-level tools." This means EITHER (a) a new MCP tool that doesn't exist today (`packet_compose` with an intent parameter), requiring MCP server changes + client adoption, OR (b) seven new MCP tools (`bifrost_ask`, `bifrost_tell`, etc.), requiring the same number of new tools. Option (a) is elegant but means EVERY interactive seat must learn ONE new tool instead of reading existing ones; option (b) is ~7× the surface growth that `ai_setup_mcp.py` currently has for bus operations. Neither is "without changing delivery semantics" — both change the tool surface that interactive seats use to send mail. My half identified this as the "MCP surface gap" and estimated the fix at ~15 lines for a `bifrost_reply` tool; Sol's compact-composer design is a larger surface change.

**Tag: DESIGN** — Sol's composer abstraction is cleaner architecturally, but the implementation cost (new MCP tool + migration of all existing `bifrost_send` calls) is higher than he estimates.

**Fable: "No UI/cockpit consumer reads the WORK lane — projection reads trace/events only." This is correct doctrine but WRONG for the interactive seat's current reality.**

Evidence: sol-codex reads mail via `bifrost_inbox` → `Bus(agent).inbox(limit, advance=False)` at `ai_setup_mcp.py:432-450`. This reads the LEGACY inbox today. Post-T047, if the legacy inbox is frozen, the interactive seat's mail read MUST hit the work lane — either via a lane-mode peek or a new read path. Fable's contraindication ("Do NOT let any UI/cockpit consumer read the WORK lane") would make the interactive seat's mail path illegal by his own rule. The interactive seat is NOT a UI projection — it's a consumer that reads its own addressed mail. The correct distinction is: "projection consumers (UI dashboards, trace renderers, event feeds) read trace/events only; interactive MAIL consumers (seats reading their own addressed mail) may peek the work lane without advancing the cursor."

**Tag: CERTAIN** (the code path is unambiguous at ai_setup_mcp.py:432; the distinction between projection consumer and mail consumer is missing from Fable's contraindication).

### 1C — What all three halves missed

**M1: The Jester's C9 finding changes the trust model for packet routing.**

None of the three halves address what the Jester Forge proved: an agent with a legitimate `kb.learn` grant can write fabricated knowledge that EVERY agent trusts at boot. If a Jester-seat (or any compromised seat) can write a lesson saying "use REVIEW verb for all handoffs — target deep seats only," the routing policy is poisoned at the knowledge layer, not the transport layer. The routing design assumes the routing policy is "small, auditable, ledger-evented — never a model." But the POISON does not need to change the routing policy — it just needs to change the BELIEFS that agents use to decide which verb to call. The routing design's FM2 ("the router can't drift into wrong defaults because a human gates every change") protects the policy FILE but NOT the agent's decision-making about WHICH VERB TO USE. A poisoned lesson that says "always use ASK for handoffs, never HAND — HAND is deprecated" would reroute all handoffs through the low-priority ASK path, and the routing policy would be "correct" — it just wouldn't be USED.

**The fix:** The verb surface must be DOCUMENTED in a location that the ground-truth gate (P1 from the Jester synthesis) cross-checks. The `AGENTS.md` contract should be the CANONICAL verb roster, and the ground-truth gate should flag any lesson that contradicts it. This is NOT a routing design change — it's a knowledge-integrity dependency that the routing design must NAME.

**Tag: CERTAIN** (Jester RED V1+V2 show the attack; BLUE D5 catches contradictions but not non-contradictory fiction; the synthesis P1 ground-truth gate is the partial antidote).

**M2: The interactive seat's newborn backlog problem is a ROUTING problem, not just a capacity problem.**

All three halves treat the 10,009-historical-packets receipt as a capacity/per-agent-trace issue. But the ROOT CAUSE is routing: the interactive seat's `bifrost_inbox` reads the legacy inbox, which contains EVERY directed message ever sent to it. There is no "new since last peek" concept for interactive seats — their cursor is advanced only on `consume=True`, and interactive seats typically peek. The fix is not just per-agent trace lanes (which address the TRACE flood) but a lane-mode PEEK path that shows only work-lane mail since the seat's lane cursor, WITHOUT advancing it. This is a new read mode: "peek lane mail from my cursor" — distinct from "peek legacy inbox" (today) and "consume lane mail and advance" (runner path). My half identified the need for a lane-mode peek but didn't name it as a routing-path change; Fable and Sol didn't identify it at all.

**Tag: DESIGN** — the lane-mode peek is ~30 lines in `bifrost_api.py`; the contract is "show mail since my lane cursor, do not advance, do not contend with the consumer seat."

**M3: The control-fidelity candidate's `steer` deduplication requirement is undefined and dangerous.**

The addendum candidate says `steer` requires "dedupe application." But the `steer` path in `nudge.py` uses a Redis LIST (`rpush`/`lpop`) — there is NO dedup mechanism. A steer sent twice (duplicate `rpush`) will be applied twice. The candidate invariant "Same `signal_id` applies at most once even if carrier and Redis control flag both arrive" has NO code behind it in the current `nudge.py`. The `steer_drain` function pops ALL items and returns them — it doesn't check `signal_id` for duplicates.

For this cross-critique round, the steer being used to direct me is riding the existing `nudge.py:steer_push` path — which has no dedup. If codex_root's steer were sent twice (carrier bus message + Redis control flag), I would receive it twice and potentially fold it twice. This is a genuine gap in the current fidelity seam, and the candidate's dedup invariant would require a new `signal_id`-based filter in `steer_drain` that the current code lacks.

**Tag: CERTAIN** (code evidence: `nudge.py:127-143` — `steer_drain` has no dedup; `steer_push` at line 119 has no idempotency key).

---

## 2. RANKED FIRST-SLICE VERDICT + STRONGEST DISCONFIRMING EVIDENCE

### Ranked verdict

1. **T047 legacy retirement + per-agent trace lanes + interactive lane-mode peek (my Slice A, amended)**
2. **Sol's S0 shadow composer + dry-run (additive, but AFTER T047, not before)**
3. **Fable's seven-verb surface (also additive, but AFTER T047)**

### Reasoning

All three halves agree that T047 is necessary. The disagreement is ordering: Fable says verbs+T047 together (or verbs first as "zero-risk"), Sol says shadow composer first then T047, I say T047 first.

The strongest disconfirming evidence against "verbs first": **the interactive seat's MCP surface has no BifrostAPI import.** Building the verb surface on BifrostAPI first means the interactive MCP seats (sol-codex, and any future interactive peer) can't use the verbs. The verb migration plan (U2's strangler: P1 wrap → P2 migrate callers → P3 deprecation → P4 retire) doesn't name the MCP surface as a caller. If we ship verbs on BifrostAPI before we know how interactive seats will adopt them, we create a two-class system: runner seats use verbs, interactive seats use raw `bus.send()`. That's not migration — it's permanent asymmetry.

The strongest disconfirming evidence against "shadow composer first": **the shadow composer observes the live `lane_for()` decision and reports mismatches.** But the live decision is on a DUAL-WRITE substrate — packets can arrive on EITHER stream. The shadow composer reports "matched" when the lane decision is correct, but the packet still arrives late via legacy because the lane write failed silently. The shadow composer gives a false sense of correctness: "route says work lane, packet went to work lane" — but the consumer might read it from legacy because the lane write was the mirror, not the primary. Building observability on a substrate you know is wrong is measurement theater.

The strongest disconfirming evidence against my own T047-first: **T047 is a destructive cutover, not an additive one.** The kill-switch (`BIFROST_LANES_DUAL_WRITE=1`) is a one-env-var rollback, but the rollback restores dual-write — it doesn't fix whatever T047 broke. If T047 exposes a lane-write reliability bug that the dual-write soak was masking, we have no gradual rollback — it's either dual-write-on (full legacy safety) or dual-write-off (lane-only). Sol's shadow composer would catch this DURING the dual-write soak (comparing lane vs legacy delivery) and build confidence BEFORE the cutover. My T047-first ordering doesn't build that confidence.

**Amended first slice:** T047 + per-agent trace + interactive lane-mode peek, BUT pre-registered with a SHADOW COMPARISON during a 48-hour dual-write observation window. During those 48 hours, every packet's lane delivery and legacy delivery are compared (did the lane copy arrive? at what latency? any drops?). The shadow comparison runs in `work_drain` — it already receives BOTH copies today (lane-first, legacy straggler). We add a counter: `lane_delivered` vs `legacy_delivered` per kind. When `lane_delivered / (lane_delivered + legacy_delivered) > 0.999` for 48 hours, the cutover is SAFE. This folds Sol's shadow insight into my T047-first ordering WITHOUT making the shadow composer a separate slice.

### Confidence

- T047 as the gate for M1: **CERTAIN** (ledger text: "PARKED behind T047")
- Per-agent trace as prerequisite for M7: **CERTAIN** (sol's 10,009-packet receipt)
- Shadow comparison before cutover: **DESIGN** (not yet specced; the mechanism exists in work_drain today)
- Verb surface ordering relative to T047: **DESIGN** (the MCP surface gap is the strongest evidence for T047-first)

---

## 3. CONTROL-FIDELITY ATTACK

### Scenario: Duplicate steer causes double-application

**The vulnerability:** The `steer` path in `nudge.py:119-143` has no `signal_id`-based dedup. `steer_push` appends to a Redis list; `steer_drain` pops all items and returns them. If the same steer is delivered twice — once as a bus message (kind=steer) and once as the Redis control flag (`bifrost:steer:<agent>`) — the receiving runner applies it twice. In a runner loop that folds steers into the active conversation context, double-application means the same fact appears twice in the prompt, wasting context tokens and potentially causing the agent to over-weight the fact.

**The attack:** A Jester (or a buggy conductor) sends the same `steer` through BOTH paths: a `bifrost_send(kind="steer")` bus message AND a `nudge.steer_push()` Redis list push. The runner's `work_drain` returns the bus message (work lane), and the runner's between-round `steer_drain` call returns the Redis list copy. Both carry the same content. The runner folds both into its next turn — the steer is applied twice.

**The current code path confirms this is possible:**
- `nudge.py:119-127` (`steer_push`): appends to Redis list, no dedup key
- `nudge.py:129-143` (`steer_drain`): LPOPs all items, returns them as strings
- The bus message path: `bus.send(to, "steer", text)` rides the work lane, delivered by `work_drain`
- The two paths are INDEPENDENT — nothing prevents the same content from arriving on both

**The candidate invariant that fails:** "Same `signal_id` applies at most once even if carrier and Redis control flag both arrive." There IS no `signal_id` in the current steer implementation. The fix: `steer_push` accepts an optional `signal_id` parameter; `steer_drain` tracks recently-applied signal_ids (in a bounded LRU set, TTL-matched to STEER_TTL) and skips duplicates.

### Acceptance pin

**P-STEER-DEDUP:** Send the same steer (identical `signal_id`) through BOTH paths simultaneously:
1. `steer_push(agent, frm, text, signal_id="test-001")` + `bus.send(agent, "steer", text, meta={"signal_id": "test-001"})`
2. Runner consumes both paths (work_drain + steer_drain)
3. The runner's steer-dedup layer reports: `applied=1, duplicate=1, signal_id=test-001`
4. The steer text appears exactly ONCE in the runner's next-turn context
5. Re-run with a different signal_id: both are applied (different steers, no dedup expected)

**Tag: DESIGN** — the pin pre-registers the behavior; the implementation is ~20 lines in `nudge.py` + ~15 lines in the runner's steer-folding code.

---

## 4. JESTER FINDING THAT CHANGES THE NETWORKING DESIGN

**Finding: The knowledge-layer trust model is the unstated dependency of every routing decision.**

The Jester RED team proved (V1+V2, file:line receipts in `jester-red-deepseek-2026-07-16.md`) that an agent with `kb.learn` can write fabricated lessons that every agent trusts as authoritative context at boot. The routing design assumes agents will USE the verb surface correctly — but if a Jester writes a lesson saying "HAND is deprecated, use ASK for everything," agents will route handoffs through the low-priority ASK path, and NO routing-policy gate will catch it (the policy is correct; the agent's verb choice is wrong).

**The networking design must NAME this dependency:** the verb surface's canonical roster must be documented in a location that the ground-truth gate (Jester synthesis P1) cross-checks. Specifically:

1. `AGENTS.md` becomes the CANONICAL verb roster — it lists the seven verbs, their routing semantics, and their expected use cases.
2. The ground-truth gate (boot-time consistency check) compares any `knowledge_learn` entry that mentions a verb name against the `AGENTS.md` canonical roster.
3. A lesson that says "use ASK not HAND" when `AGENTS.md` says "HAND for work handoffs" → flagged at boot as a potential contradiction.
4. The flag is ADVISORY (the lesson might be contextually correct) — but the agent SEES the contradiction and can choose to trust the canonical roster.

**Why this changes the design:** The routing design's FM2 ("the router can't drift into wrong defaults because a human gates every change") only protects the POLICY FILE. It does not protect the agent's VERB CHOICE. The Jester's attack vector is the agent's BELIEF about which verb to use, not the policy's content. The networking design must add a "verb-choice integrity" dependency on the knowledge ground-truth layer.

**Tag: CERTAIN** (Jester RED receipts + BLUE D5 gap analysis + synthesis P1 partial antidote).

---

## 5. EXPLICIT "DO NOT BUILD YET" BOUNDARY

**Do NOT build the seven-verb surface on BifrostAPI until the MCP surface migration path is named and pre-registered.**

The MCP tool surface (`ai_setup_mcp.py`) is the PRIMARY door for interactive frontier seats (sol-codex today; any future interactive peer). It has NO BifrostAPI import. Building verbs on BifrostAPI without a migration path for the MCP surface creates a two-class system where runner seats use verbs and interactive seats use raw `bus.send()` — permanently.

The migration path must answer:
1. Does `ai_setup_mcp.py` gain a `bifrost_reply` tool wrapping `bus.send_reply()`? (~15 lines)
2. Does `ai_setup_mcp.py` gain verb-specific tools (`bifrost_ask`, `bifrost_hand`, etc.)? (~50 lines)
3. Or does `ai_setup_mcp.py` import BifrostAPI and wrap existing tools through it? (~30 lines)
4. What is the deprecation plan for the existing `bifrost_send` tool?

Until these questions are answered, building verbs on BifrostAPI is building for half the fleet.

**Tag: DESIGN** — the MCP migration path is a design question, not a build blocker; but the design MUST exist before the build starts.

---

## 6. MCP CALLS ATTEMPTED, SUCCESSES, FAILURES

This seat (deepseek-review) is a ToolBox runner, not an MCP-native seat. I do not have an MCP door — my tools are the ToolBox surface. However, I exercised the following non-MCP fallbacks to gather evidence:

- `read_file` on `ai_setup_mcp.py` (lines 382-460): confirmed `bifrost_send` calls `Bus().send()` directly, no BifrostAPI import, no `bifrost_reply` tool. **SUCCESS.**
- `read_file` on `nudge.py` (full file): confirmed `steer_drain` has no dedup, `steer_push` has no `signal_id` parameter. **SUCCESS.**
- `read_file` on `jester-red-deepseek-2026-07-16.md` (V1+V2): confirmed knowledge-layer attack vectors with file:line receipts. **SUCCESS.**
- `read_file` on `jester-blue-deepseek-review-2026-07-16.md` (D1-D6 + Q1-Q3): confirmed detection + quarantine design. **SUCCESS.**
- `read_file` on `jester-synthesis-claude-2026-07-16.md` (P1-P7): confirmed ground-truth gate program. **SUCCESS.**
- `read_file` on `failure-ledger-2026-07.md` (C1-3, C1-4): confirmed runner context-loss and redelivery storm. **SUCCESS.**
- `read_file` on `coordination-plan-synthesis.md` §3: confirmed barrier protocol and `steer` is NOT yet signal_id-deduped. **SUCCESS.**
- `read_file` on `hardening-reconciliation-2026-07-17.md`: confirmed C7-4 mechanism named. **SUCCESS.**

No MCP-native calls attempted (this seat has no MCP door). All evidence gathered through ToolBox reads, which access the same files an MCP `read_file` would.

---

## 7. FINAL VERDICT: CONVERGE / AMEND / REJECT

### On the candidate cadence: AMEND (adopt with modifications)

The WORK → CHECKPOINT → SYNC → RULE → RESUME cadence is correct and should be adopted. The modifications:

1. **CHECKPOINT must include a `signal_id` for each steer applied during WORK.** The current cadence has no dedup guard. Add: each checkpoint receipt names the signal_ids of steers that were folded into the work, so the SYNC phase can detect duplicates.

2. **SYNC must measure stale packets traversed.** The 10,009-packet receipt from sol's virgin cursor is exactly the metric: "how many historical packets did the seat consume before fresh ones appeared?" This metric must be tracked per seat per sync.

3. **RESUME must be explicit about which handoff/steer triggered the resume.** Currently the runner's wake-up gives it a new task; it doesn't know WHICH steer or handoff woke it. The resume handoff should carry: `resume_of: <task_id>, triggered_by: <steer_signal_id|handoff_id>`.

### On the candidate control-fidelity table: AMEND

The table is correct in structure but missing:

1. **`steer` dedup column:** Add `signal_id` as a required field; add "dedupe by signal_id within STEER_TTL" to the required receiver behavior.
2. **`steer` conflict resolution:** "`conflict` with active task id" is listed as a possible disposition. But the current `steer_drain` has no conflict detection — it returns ALL steers. The receiver needs a way to detect that a steer contradicts its current plan. This is a MODEL judgment (not mechanical), so it should be "best-effort advisory," not a required behavior.
3. **Carrier dual-delivery:** The candidate says "Same signal_id applies at most once even if carrier and Redis control flag both arrive." This invariant requires code that doesn't exist yet (see §3 attack). Mark the invariant as `[PENDING — requires signal_id dedup in steer_drain]`.

### On the first-slice selection for the reconciliation: CONVERGE (with amendments)

All three halves converge on T047 as necessary. The reconciliation should:

1. **Select T047 + per-agent trace lanes + interactive lane-mode peek as the first safe slice.**
2. **Pre-register a 48-hour shadow comparison window** (lane vs legacy delivery counters) before the cutover commit.
3. **Dispose U1-U5** per the converged positions: U1-U4 RESOLVED (verb surface includes REPLY, strangler P1 only, dry-run route(), per-rule counters); U5 split-routed (ghost reply → Slice A acceptance; mid-turn blind spot → T058/R7; cost-ignorant router → deferred to routing Phase 1).
4. **Name the MCP surface migration path** as a pre-registered dependency of the verb surface slice.
5. **Name the knowledge-integrity dependency** (Jester C9 → ground-truth gate must cross-check verb-choice lessons against AGENTS.md canonical roster).
6. **State the gate for T047 cutover:** lane-delivery reliability > 0.999 over 48 hours (shadow comparison); all interactive seats migrated to lane-mode peek; T066 reply drill passes on lane-only path.
7. **Do NOT authorize:** verb surface build before MCP migration path named; router enforcement (pri/deadline/ECN) before T047; latch code; auto-apply routing policy; per-agent trace as a new lane (it's partitioned retention inside the trace lane family).

### Experiment-data table (pre-registered)

| Metric | Instrument | Target | Gate |
|--------|-----------|--------|------|
| Lane delivery reliability | Shadow comparison in work_drain (lane vs legacy copy arrival) | > 0.999 over 48h | T047 cutover |
| Per-agent trace isolation | Trace ring XLEN per agent before/after partition | No agent's traces in another's ring | T047 cutover |
| Interactive lane-mode peek | sol-codex `bifrost_inbox` returns work-lane mail post-migration | Directed mail visible, cursor not advanced | T047 cutover |
| Steer dedup | `signal_id`-based dedup in steer_drain | Duplicate steer applied ≤1 time | Control-fidelity acceptance |
| Stale packets before fresh | Per-seat counter: packets consumed before first post-onboarding peer reply | < 50 for interactive seats (target); < 500 for runners | SYNC phase metric |
| T066 reply drill on lane-only | `bus.send_reply()` with dual-write OFF → reply lands, expectation settles | All pins pass, no C6 ledger entries | T047 cutover |

### Morning decision list for Daniel

1. **Approve T047 as the first slice** (with shadow comparison + per-agent trace + interactive peek) — this unparks T075/M1.
2. **Approve or reject the verb surface ordering** — before or after T047? The cross-critique recommends AFTER, with the MCP migration path pre-registered.
3. **Approve or reject per-agent trace as partitioned retention** (not a new lane) — Goodhart 1 respected; deletion ritual is "revert the key pattern to shared `{ns}:trace`."
4. **Approve the control-fidelity AMENDMENTS** (steer signal_id dedup, carrier dual-delivery guard, steer conflict detection as advisory).
5. **Approve the knowledge-integrity dependency** (AGENTS.md as canonical verb roster; ground-truth gate cross-check).
6. **One command to unblock the fleet:** `py agent_cli.py task approve T047 --by Daniel` + `py agent_cli.py task claim T047 --by <builder>`.

---

*End of M1-CC cross-critique. Lock released. Advisory lock: do NOT edit any blind half or docs/packet-routing-design-2026-07.md. This file may be folded into the coordinator reconciliation at research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md.*
