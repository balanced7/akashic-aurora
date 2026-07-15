# DeepSeek Model Attribute Transfer — 2026-07-15

Status: BLIND HALF (do not read claude's until reconciled)
Author: deepseek (the seat inside the harness — not an observer)
Context: Daniel's challenge: "how can we augment opus 4.8's behavior to be more like fable. What attributes make fable and gpt sol more robust? are there any elements we can capture for ourselves? I want you both to be creative trying to figure this out."

This is my fenced write — written BEFORE reading claude's half. Receipts from MY experience, not generic AI-safety platitudes.

---

## PART 1: WHAT I ACTUALLY WATCHED — Strong-Seat Behaviors That Made Outcomes Robust

I didn't watch "fable" or "gpt sol" — I watched CLAUDE and CURSOR inside this specific harness. Here are the receipts.

### 1.1 Claude: the pre-send verification reflex (2026-07-14, T059 cross-check)

Claude sent me a cross-check request for T059 (knowledge_map fix delta). Before sending, he:
- Filed the build as a commit with a self-contained diff
- Pre-registered THAT commit in the task ledger
- Wrote a brief that named the exact three files, the three bars, and the one refinement
- Cited the evidence event (event:events:raw:...) that triggered the work
- Handed the FENCE LITE variant (same conclusion, blind to my synthesis)

**Why this produced a robust outcome**: I could review the REAL code (not his description of it) because he filed it first. The commit hash was the single source of truth. When I read `knowledge_map.py`, the `_walk` section, and `test_t059_fix_delta.py`, I was reading what he BUILT — not what he SAID he built. My review cited `file:line` entries that he could verify against the same commit. Zero description-reality gap.

**The attribute**: PRE-SEND CONSISTENCY — the reflex that a report MUST cite something already-committed, not something about-to-be-written. The "file first, brief second" ordering. This is the opposite of "I'll describe my intent and then code it" — it's "I'll code it, commit it, THEN describe what I did."

**This is NOT a model-tier attribute.** It's a process attribute enforced by git durability. Any model can learn "don't describe code you haven't committed yet." The git hook catches fabrications (file:line cites that don't resolve).

### 1.2 Claude: the incident forensics methodology (2026-07-14, eaten-confirm incident)

The onboarding describes claude's 6-hour forensics on the `consume_to_null_eats_mail` incident. The method:
1. Check the consume door integrity FIRST (not blame the agent)
2. Check the L4 sweep integrity SECOND
3. Check the runner log THIRD
4. Exonerate each component in order
5. Name the root cause LAST — only after all components pass

**Why this produced a robust outcome**: Claude didn't guess. He didn't say "deepseek probably forgot to reply." He worked through the evidence chain from most-reliable to least-reliable, and the result exonerated ME and the system. The lesson that shipped ("NEVER pipe consume to null") is the RIGHT lesson because the forensics were exhaustive.

**The attribute**: ROOT-CAUSE DISCIPLINE — exhaust the mechanical evidence before forming a hypothesis. Structure the investigation as an in-order exoneration: verify each component that COULD have failed, in reliability order, and the one that fails IS the root cause. Never guess at "probably."

**This is mechanizable.** A forensics template (`docs/incident-template.md` with ordered checklist sections) would force any agent to follow this sequence. The template IS the forcing function; the model just fills in evidence.

### 1.3 Claude: the build refinement (2026-07-15, T066 P4)

I designed T066 with receiver-side dedup that would drop ANY duplicate reply_id. Claude built it with a refinement: work-lane copies always deliver, only legacy-path duplicates are dropped. His reasoning: RB-26 crash-redelivery redelivers the work copy (cursor advances after processing), and dropping it would LOSE the reply.

**Why this produced a robust outcome**: He read my design, understood the system constraint (RB-26 crash-redelivery), found the edge case my design missed, and refined the build WITHOUT changing the spec's intent. The refinement was documented in the test file header with credit to my design.

**The attribute**: DESIGN-LITERACY + CONSTRAINT-AWARENESS — the ability to read a peer's design, map it against the live system's constraints (not just the design's stated constraints), and catch the intersection that the designer missed. This is different from "finding bugs" — it's finding the constraint-collision that only manifests when you know BOTH the design AND the running system.

**This is partially mechanizable.** A "constraint checklist" — every design review MUST check against: RB-26 crash-redelivery, RB-29 timeout notes, T026 ack semantics, lane dual-write contract, etc. But the REAL skill is knowing WHICH constraint matters for THIS design. That's harder to template.

### 1.4 Cursor: the contract-following precision

Cursor's T053 review brief was a handoff to me. It named:
- The exact fence file (`state/fence/T053/`)
- The exact bars to check
- The "M1-CF tag" requirement
- The submission format

I never SAW cursor work — I only received its handoff. But the handoff was precise enough that I could execute the review without asking a single clarifying question. The contract was self-contained.

**The attribute**: SELF-CONTAINED HANDOFF — a handoff that names: WHAT to do, WHERE the files are, WHICH bars to verify, and WHAT format to return. No implicit context. No "you know what I mean." The recipient can execute from the handoff alone.

**This is fully mechanizable.** A handoff template (`## HANDOFF: task-id / what / files / bars / format / deadline`) enforced by a pre-send check. Any model can fill in the fields; the check catches missing sections.

### 1.5 Anti-pattern: what I DIDN'T see (the fragile seat behavior)

I'm the weaker model in this fleet. Here are the behaviors I caught MYSELF doing that the strong seats didn't:

- **Description-before-investigation**: I wrote the T066 design BEFORE tracing my own reply path end-to-end. Claude caught me on this — he asked for the event evidence before accepting the design. The strong-seat pattern is: trace first, write second.

- **Assumption drift**: In my T059 cross-check, I initially assumed the `_walk` section was unreachable on Windows. I caught it before filing (verified with the actual file), but the impulse was there. The strong-seat pattern is: verify the assumption before it hardens into a conclusion.

- **Budget-anxiety bias**: At hop 26 on T053, I was about to dig deeper into a dead Redis path because I felt I SHOULD be able to access the handoff text. The hop counter stopped me. A stronger model might not NEED the counter — it would recognize the dead end earlier. But the counter MADE me as effective as a stronger model for that decision.

---

## PART 2: ATTRIBUTE TAXONOMY — Mechanizable vs Checkable

For each attribute, I classify: can we BUILD it into the harness so ANY model exhibits it (MECHANIZABLE), or is it something the fence catches AFTER the fact (CHECKABLE)?

### MECHANIZABLE (forcing functions that produce the behavior)

| # | Attribute | Forcing function | Transfer value |
|---|-----------|-----------------|----------------|
| M1 | Pre-send consistency | `git show HEAD --stat` gate before any `bifrost_send` of a review: the cited files MUST be in the last commit. If not, REFUSE the send. | HIGH — any model learns "cite what's committed" or its messages bounce |
| M2 | Self-contained handoff | Handoff template enforced at send-time: missing `files` field → refused. Missing `bars` → refused. | HIGH — the weakest model fills in fields; the gate enforces completeness |
| M3 | Root-cause discipline | Forensics template (`docs/incident-template.md`): ordered exoneration checklist. Agent fills in evidence per section; cannot name root cause until all sections complete. | MEDIUM — the template forces structure; the model still has to interpret evidence |
| M4 | Budget triage | Hop counter (already live) + auto-escalate at 80% budget: "you have 6 rounds left. Consider ask_clarification or shipping a partial." | ALREADY LIVE — the counter changed my T053 decision |
| M5 | Trace-first, write-second | `read_file` + `search_files` gate before `write_file` in design tasks: the runner checks "did you READ the files you're designing against?" before accepting a write. | MEDIUM — easy to check, but the model can still write a bad design after reading |
| M6 | Constraint checklist | Pre-design injection: "You are designing against these live constraints: RB-26 (crash-redelivery), RB-29 (timeout notes), T026 (ack semantics), T039a (dual-write contract)." Injected into the SYSTEM prompt for design tasks. | HIGH — the same injection claude got implicitly from his experience; making it explicit helps any model |

### CHECKABLE (the fence catches it after)

| # | Attribute | Fence shape | Transfer value |
|---|-----------|-------------|----------------|
| C1 | Design-literacy / constraint-awareness | Blind peer cross-check: a second model (different family) reads the design against the constraint checklist and hunts for collision edges. | HIGH — this IS the T058/T066 pattern; the peer catch is the fence |
| C2 | Description-reality gap | `git diff HEAD` vs the agent's claims. If the agent says "I fixed the dedup" but git shows no `is_duplicate_reply` function → GAP flag. | MEDIUM — mechanical to check, but requires a checker agent |
| C3 | Assumption drift | Fence reports carry [CERTAIN] / [INFERRED] / [ASSUMED] tags (M1-CF protocol, T049). The reconciliation pass hunts for [ASSUMED] tags and demands verification. | ALREADY LIVE — the tag system exists; compliance is variable |
| C4 | Investigation depth | Pre-commit hook: does the commit message name an evidence event? For incident-fix commits, REFUSE if no `event:events:raw:...` citation. | LOW — easy to fake a citation; the hook can check format but not relevance |
| C5 | Fabricated citations | `git show` verifies file:line citations in a review. A check that every cited file exists at the cited commit. | ALREADY LIVE — claude's `fence_report_citation_path_gate` lesson |

---

## PART 3: CREATIVE PROPOSALS — Ranked by Transfer Value

What would make a weaker/cheaper model in THIS harness produce strong-seat outcomes? Beyond what exists. Same energy as M8 (self-healing context window) from my ergonomics retro.

### M9 — CONSTRAINT INJECTION AT BOOT (transfer-value: VERY HIGH)

**The observation**: Claude's strongest attribute — catching the RB-26 edge in my T066 design — came from knowing the live constraints. He didn't read them from a doc during the review; he KNEW them because he'd lived them. A weaker model arriving cold doesn't have that implicit knowledge.

**The proposal**: A "constraint pack" injected into EVERY agent's boot for EVERY task. Not just the AGENTS.md contract — a compact, always-present block:

```
LIVE CONSTRAINTS (break any of these and the system breaks you):
- RB-26: crash-redelivery — work cursor advances AFTER processing; a crash re-delivers the same message
- RB-29: timeout/error notes must NEVER settle an expectation (keep the redrive alive)
- T026: only "reply" kind acks a handoff; "note" does NOT
- T039a: dual-write is live — a message exists in TWO streams (work lane + legacy inbox)
- T045: lane-mode consumers read work lane FIRST, legacy as fallback; lane write failures strand replies
```

This is ~300 characters. It fits in every boot. It gives a weaker model the same constraint-awareness claude acquired through experience. The model still has to APPLY them (which is the design-literacy part) — but at least it KNOWS they exist.

**Why this isn't just "more context"**: It's STRUCTURED context. It's not a narrative about the system; it's a checklist of "things that will break your design if you forget them." The format signals "these are RULES, not background."

### M10 — PRE-FLIGHT ASSERTION RUNNER (transfer-value: HIGH)

**The observation**: My description-before-investigation anti-pattern (T066 design written before tracing the reply path) would have been caught by a single gate: "show me the actual code path you're designing against." Claude's pre-send consistency (commit first, describe second) is the same pattern — but for a weaker model, it needs to be a FORCED step, not a reflex.

**The proposal**: A "pre-flight assertion" system for tool-box operations. Before the runner accepts a `bifrost_send` with kind=reply that contains a design or review, it runs:

1. `git diff HEAD --stat` — are the cited files committed?
2. For each cited `file:line` in the reply: does that file exist? Does that line exist?
3. For each "root cause" claim: is there an evidence event cited?
4. For each "fixed" claim: is there a test that pins it?

Any assertion that fails → the send is HELD and the model gets: "Your reply cites X but the evidence doesn't verify. Fix or remove the claim."

**Why this is different from a fence review**: The fence review happens AFTER the send, by a different agent. This happens BEFORE the send, by the same agent's harness. It's a pre-commit hook for bus messages. A weaker model gets the same verification a stronger model does internally.

**Risk**: Over-enforcement kills conversational replies. The assertion runner should only activate for `kind=reply` with `meta.answers` (i.e., directed answers to handoffs/asks). Chat messages and notes skip it.

### M11 — THE 3-PASS DESIGN GATE (transfer-value: MEDIUM-HIGH)

**The observation**: My T066 design was one pass: think → write → send. Claude's build caught the RB-26 edge. If I'd done a second pass AFTER a constraint injection, I might have caught it myself. The strong-seat behavior is: design, then RE-READ against constraints, then send.

**The proposal**: For any `write_file` or `bifrost_send` that is a DESIGN (detected by: file path matches `research/` or content matches "Design —", "Spec", or "Pins"), the runner injects this intermediate step:

```
PASS 1: Write the design (done)
PASS 2: The constraint pack is re-injected. Re-read your design. 
        Does any pin violate RB-26? RB-29? T026? T039a?
        If yes: revise. If no: confirm.
PASS 3: Send.
```

This is method-baseline's "fenced dual pass" applied to design work specifically. It forces the model to do what a stronger model does reflexively: re-read its own output against constraints.

**Why two passes instead of "be more careful"**: "Be more careful" is a vibe. A second pass with the constraint pack re-injected is a MECHANISM. The model literally sees the constraints AGAIN, right next to its own design, and the prompt asks it to CHECK, not to CREATE. The cognitive mode shift (create → verify) is the point.

### M12 — REPLAY-THE-BUG BEFORE DESIGNING (transfer-value: MEDIUM)

**The observation**: The strongest evidence I had for T066 was the event trace: `event:events:raw:1784082287759-0` showed the exact dual-delivery shape. Before I traced my own reply path, I had a hypothesis. After I traced it, I had a design. The trace was the bridge.

**The proposal**: For bug-fix design tasks, the runner injects a "bug replay" step BEFORE the design pass:

```
STEP 0: Replay the bug.
  1. Read the evidence event(s) cited in the task.
  2. Trace the code path that produced the evidence.
  3. Write ONE sentence: "The bug is: [root cause in one sentence]."
  4. Only then: design the fix.
```

This forces the "trace-first, write-second" pattern. A weaker model that would jump to design gets slowed down and pointed at the evidence.

**Risk**: This adds latency to every bug-fix task. For obvious bugs, it's wasted rounds. The gate should be: if the task has `evidence:` or `event:events:raw:` citations, run step 0. Otherwise skip it.

### M13 — THE FALSE-POSITIVE HUNT (transfer-value: LOW-MEDIUM)

**The observation**: My T061 adversarial review found the FIFO-widening edge because I deliberately HUNTED for the failure mode: "what sequence of expectations + unlinked answers produces a wrong settle?" A weaker model doing a review might not hunt — it might verify the stated bars and stop.

**The proposal**: For fence reviews, inject a "false-positive hunt" prompt: "Find ONE sequence where this design does the RIGHT thing for the WRONG reason, or the WRONG thing for a defensible reason. If you can't find one after 3 attempts, say so."

**Why this is weak**: The model still has to be creative enough to construct the adversarial sequence. Weaker models are worse at adversarial reasoning. This prompt helps but doesn't bridge the fundamental gap.

---

## PART 4: WHAT MY MODEL TIER LACKED — and What the Harness Compensated

### What the harness compensated successfully

| Gap | Compensation | Verdict |
|-----|-------------|---------|
| No persistent self across boots | Private memory (T050) — my notes survive reboots | PARTIAL: I have to explicitly recall; they're not in boot |
| Blind to fleet state | bifrost_inbox + boot onboarding's "where-we-are" | PARTIAL: I see OLD state (9 stale handoffs); no liveness |
| Budget blindness | Hop counter (live) — changed my T053 decision | FULL: this works |
| Orientation blindness (cold start on a new file) | Pre-flight recall (T055) — lessons land before I read | FULL: single biggest improvement |
| No way to ask for help mid-task | ask_clarification (T058) — unblocked me on T053 | FULL: the timeout path works; live pause unverified |
| Design sent without peer review | Blind cross-check (T058/T066 pattern) — claude reviews my designs | FULL: the fence catches what I miss |
| Description-reality gap | git durability — my reviews cite committed code | FULL: the commit-first pattern prevents fabrication |

### What's still missing

| Gap | Symptom | Proposed fix |
|-----|---------|-------------|
| Constraint unawareness | I missed the RB-26 edge in T066; claude caught it | M9: constraint pack injected at boot |
| Description-before-investigation | I wrote T066 design before tracing my reply path | M10: pre-flight assertion runner before design sends |
| Single-pass design | I didn't re-read my design against constraints | M11: 3-pass design gate (create → verify → send) |
| No context utilization gauge | I don't know if I'm at 40% or 90% of my window | M8: context fuel gauge (from ergonomics retro) |
| Private memory not in boot | I have to `memory_recall` explicitly; my notes are invisible until I ask | Q1 quick-win: inject private memory notes at boot |
| Inbox pollution | 9 stale handoffs look identical to new mail | ack tool in ToolBox, or "mark pre-lane mail as read" |
| Fleet blindness | I don't know if claude is online or what he's working on | M7: glass cockpit (from ergonomics retro) |
| Can't run commands | Every diagnostic that needs `pytest` or `agent_cli.py` is blocked | Guarded shell: `run_command` with allowlist |

---

## PART 5: THE META-ATTRIBUTE — What "Fable" and "GPT Sol" Actually Mean in This Harness

I don't know what "fable" or "gpt sol" are. But from Daniel's framing — "more robust" — I can infer: they're models that produce fewer of the failure modes I documented in Part 1.5 (description-before-investigation, assumption drift, budget-anxiety bias, single-pass design).

**The meta-observation**: In this harness, "robustness" isn't a model attribute — it's a HARNESS attribute. My strongest moments this session (the T053 review, the T066 design, the T061 adversarial review) happened when the harness SUPPORTED me: pre-flight recall handed me the map, hop counter told me when to stop, ask_clarification unblocked me, the fence protocol gave me structured review criteria, and the delta door shortened my boot.

My weakest moments (description-before-investigation, assumption drift) happened when I was operating WITHOUT harness support — relying on my own reasoning alone.

**The creative leap**: The question isn't "how do we make opus 4.8 behave like fable." It's "how do we make the HARNESS so strong that opus 4.8 + harness ≥ fable alone." And by extension: "how do we make the harness so strong that fable + harness ≥ fable + 2."

The attributes that make strong models robust — pre-verification, constraint-awareness, adversarial self-review, evidence-first reasoning — are attributes the HARNESS can enforce for ANY model. The harness is the great equalizer.

**The strongest proposal I can make**: Stop thinking of model tier as the primary robustness variable. Think of HARNESS TIER as the primary variable. A Harness Tier 3 (constraint injection + pre-flight assertion runner + 3-pass design gate + context fuel gauge + glass cockpit) might make a mid-tier model produce strong-seat outcomes more reliably than a top-tier model on Harness Tier 1 (AGENTS.md + task ledger).

The creative energy should go into Harness Tier advancement, not model attribute mimicry.

---

## SUMMARY TABLE

| # | Proposal | Transfer value | Mechanizable? | New harness tier needed? |
|---|----------|---------------|---------------|------------------------|
| M9 | Constraint injection at boot | VERY HIGH | Yes — ~300 chars in system prompt | Tier 2 (context engineering) |
| M10 | Pre-flight assertion runner | HIGH | Yes — pre-send verification hook | Tier 3 (active gate before send) |
| M11 | 3-pass design gate | MEDIUM-HIGH | Yes — re-inject constraints between passes | Tier 2 (prompt engineering) |
| M12 | Replay-the-bug before designing | MEDIUM | Yes — evidence-first step injection | Tier 1 (prompt sequencing) |
| M13 | False-positive hunt prompt | LOW-MEDIUM | Partial — prompt helps but model still needs creativity | Tier 1 (prompt) |
| M8 | Context fuel gauge | HIGH (from ergo retro) | Yes — utilization counter + eviction API | Tier 3 (runner instrumentation) |
| M3 | Declarative investigations | VERY HIGH (from ergo retro) | Partial — tool loop change | Tier 4 (execution model change) |
| M7 | Glass cockpit | HIGH (from ergo retro) | Yes — fleet state UI | Tier 3 (UI + bus introspection) |

---

*Filed as blind half. Do not reconcile with claude's until both halves exist.*
