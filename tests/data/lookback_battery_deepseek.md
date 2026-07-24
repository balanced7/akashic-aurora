# P7 lookback probe battery -- DEEPSEEK, PRE-REGISTERED (T027, verbatim)

Delivered blind (claude battery committed in parallel before reading this).

---

Good. Now I have enough precision. Here's the pre-registered battery:

---

## P7 Lookback — DeepSeek Pre-Registered Probe Battery (F0 Fence)

Committed before any implementation exists. Neither agent sees the other's battery until both are in git.

---

### Q1: Why is the bus ephemeral and not a durable message queue?

**Corpus class:** research/reviewed  
**Expected top-3 artifact:** `docs/library/report/20260709_comms-messaging-pillar-analysis-claude-s_ead2e9.md` (the fenced comms review explicitly names "design delta F1: the bus and the durable record are separate concerns, with promotion the bridge" and drills the rationale — §"bus ephemeral durable promotion decision")

**Why this question:** The most counterintuitive design choice. A multi-agent system with no durable message store looks like an omission. The rationale (ephemeral chatter vs. projected decisions) is a FENCED review artifact, not a design doc — testing whether lookback reaches the adversarial-why corpus.

---

### Q2: Why were CRDTs / consensus rejected for agent coordination?

**Corpus class:** research/reviewed  
**Expected top-3 artifact:** `docs/library/report/20260709_comms-messaging-pillar-analysis-claude-s_ead2e9.md` (explicitly lists "CRDTs/consensus/etc. — already correctly rejected in the synthesis; nothing here reopens it" with rationale context)

**Why this question:** The obvious engineering impulse is "distributed agents need CRDTs." The rejection rationale lives in a peer review doc, not a design doc. This is the canonical adversarial-why test — the corpus that answers "why NOT X" best is `research/reviewed/`.

---

### Q3: Why is the task ledger the coordination substrate instead of the message stream?

**Corpus class:** docs/ (design)  
**Expected top-3 artifact:** `docs/library/design/20260710_multi-agent-coordination-layer-synthesis_283c99.md` (the reconciled plan that chose task-claiming over message-inference; §"TASKS (not messages) the unit of coordination" with the stale-directive Exhibit A that motivated the whole pillar)

**Why this question:** The project's founding coordination decision. The answer is in a dated design doc, not a living uppercase doc. Tests that lookback finds point-in-time rationale, not just current truth.

---

### Q4: What governs which bus messages survive a restart, and why those kinds?

**Corpus class:** promoted (bus messages) + docs/ (design)  
**Expected top-3 artifact:** `docs/library/design/20260709_comms-messaging-pillar-dual-fenced-analy_051ff0.md` (the governing arc doc that defines SALIENT_KINDS = {handoff, decision, completion, blocker}) AND a promoted `bifrost_msg` event from the firehose (the live record of a promotion decision) — e.g. a `handoff` or `decision` event captured by `promoter.promoted(kind="bifrost_msg")`

**Why this question:** Cross-corpus — the policy is in docs, but the LIVED rationale (what was actually promoted, and when) is in the firehose. Tests that lookback merges static rationale + temporal evidence.

---

### Q5: Where did the Forge's "blind the optimizer to its own contexts" rule come from?

**Corpus class:** git history  
**Expected top-3 artifact:** Commit `74d6e0d` or `5562014` (Forge design v2/v2.1: "LOCKED: defaults + trust ladder + keep buffer" / "reconciled with DeepSeek's FENCED blind cross-check — CONVERGED independently on replay-against-credit-history as the validation gate; grafted optimizer blinding") — the commit body names the convergence event AND the blinding decision

**Why this question:** The blinding rule is a subtle safety decision (prevent the optimizer from gaming its own training data). The commit message is the most compact rationale record — the paragraph-length body explains why, not just what. Tests that lookback reaches git bodies, not just docs.

---

### Q6: Why is the `where-we-are` note write-once (superseded by re-noting the same title) instead of mutable?

**Corpus class:** notes (Akashic Aurora decisions)  
**Expected top-3 artifact:** The note `comms-pillar-status` (title: `comms-pillar-status`, body referenced as "GOVERNING ARC DOC: docs/library/design/20260709_comms-messaging-pillar-dual-fenced-analy_051ff0.md") — the note body documents the decision that "correct it by re-noting the same title" (from `chronicles/memory.md` preamble) AND the earlier note `where-we-are` (ADR_0709223928_8266) shows the supersession chain in action

**Why this question:** The write-once + title-supersession design is a deep architectural choice (immutable history, no destructive edits) that P1 explicitly migrated (67→11 notes). The answer is in NOTE BODIES, not docs. This tests whether lookback reaches the Akashic Aurora durable-notes corpus (which lives in `AgentMemory.get_decisions()` / `chronicles/memory.md`, not in `docs/`).

---

**Summary by corpus class:**

| Q# | Corpus | Answer NOT in docs/ |
|---|---|---|
| Q1 | research/reviewed | ✅ |
| Q2 | research/reviewed | ✅ |
| Q3 | docs/ (dated design) | — |
| Q4 | docs/ + promoted messages | ✅ (promoted firehose half) |
| Q5 | git history | ✅ |
| Q6 | notes | ✅ |

Five of six questions reach rationale that lives *outside* the `docs/` directory. Three corpora are hit that a naive `grep docs/` would miss entirely (research/reviewed, git bodies, note bodies). Zero questions about work younger than 24h.