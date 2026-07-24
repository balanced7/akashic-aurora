---
akashic_id: art_20260724_sota-quality-kimi-half-audit-lens_6a0314
akashic_sha: ab0771e5d648
schema_version: 1
status: current
type: report
arc: sota-quality
date: 2026-07-24
title: sota-quality-kimi-half-audit-lens
gist: "kimi T105 half (training-prior INFER): evaluation-side practices ranked by gate-hardening; judge pitfalls, process supervision, calibration elicitation"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [frontier, audit, migration]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_sota-agentic-quality-research-round_8eb04e
    rel: discusses
created: "2026-07-24T08:00:55"
updated: "2026-07-24T08:00:55"
---
<!-- GENERATED PROJECTION of art_20260724_sota-quality-kimi-half-audit-lens_6a0314 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# sota-quality-kimi-half-audit-lens

DANIEL'S CALIBRATED QUESTION: **"Which single practice would have caught the most of our PAST defects at the gates?"**

My answer, with receipts from our own failure ledger and validation sweep.

---

## HONESTY BAR

I have no web door tonight. Every claim below is **training-prior / INFER**, not VERIFIED. I name canonical sources where I know them; I do not invent citations. Claims grounded in OUR pipeline cite actual failure-ledger entries and fence receipts — those are VERIFIED against our own record.

---

## CALIBRATED ANSWER: Pre-registered RED-first pins + live-run-first

**The single practice that would have caught the most past defects at our gates is: pre-register the acceptance pins RED (expected FAIL) BEFORE building, then run them live and refuse to claim GREEN until the run proves it.**

This is already codified as M3 (pre-registration) + M5 (live-exercise) in our method-baseline. The question is: which of our past defects escaped because we skipped one of these steps? Answer: nearly all of them.

### Evidence from our failure ledger

Cataloging our C1-C10 categories by which practice gap they trace to:

**Gap: claimed GREEN without running the tool live first (no pre-registered pins, no live receipt)**
- **Checker M-L3 self-exemption** (partner night): deepseek chartered check_ui_contract.py, claimed "exits 0 tonight, zero false positives." I ran it live — it fired 53 M-L8 + 1 M-L1 on the CURRENT console. The CLAIM was the defect, not the tool. kimi's F1 meta-law born here: [M] receipts cite ACTUAL tool output, never builder expectation.
- **C9-2 CURRENT DIRECTIVE banner outlived its work**: the staleness stamp was believed current; live re-evaluation proved it stale.
- **C6-3 piped gate exits**: `&&` after a pipe makes the pipe's exit code the gate — `pytest | tee` exits 0 even when pytest fails. Nobody ran the gate alone before trusting it.
- **premature_green_claim_gating** (2026-07-24): commit message asserted GREEN but test FAILED; the chain didn't gate on exit code. Same genus.
- **C9-3 storm gauge fed stream-LENGTH**: gauge fired ceremony on pure history because nobody ran the gauge against a known-clean stream first.

**Gap: no pre-registered pins (built then tested, not tested-before-built)**
- **C1-1 dead-holder rescue**: the seat-dead-holder problem was known for days before pins existed. Pre-registering "a dead holder frees within TTL" as a RED pin before building would have caught the gap.
- **C6-7 lane divergence**: the T066 pin was GREEN but partial — it gated the SEND door, not the CONSUME door. A pre-registered RED pin on "work-lane consumption advances the work cursor" would have caught the consume-side gap.
- **T014 defect 2b** (consume-without-display): a directed reply landed and was consumed silently. Pin "a directed reply surfaces to the addressee" pre-registered RED would have caught it at design.
- **C2-1 two agents clobbered same test file**: no pre-registered pin on "two concurrent writes to the same path refuse or merge."

**Gap: no adversarial/falsification probe (only happy-path tested)**
- **C8-3 PreToolUse hook double-fires**: registered on TWO surfaces. A pin "hook fires exactly once per tool call" would have required counting, which requires an adversarial probe.
- **C7-4 MCP boot() hangs in response path**: work executes, reply never returns. Happy-path pin would pass; needs a timeout-gated pin.
- **tempdir_sidecar_test_selfpoison**: test passed solo, failed on rerun because of %TEMP% state leakage. A "passes on second consecutive run" pin would have caught it.
- **C1-6 false tombstone**: harness restart cycles produced false dead-seat signal. Needed a "restart cycle does NOT produce a tombstone" pin.

### The pattern

Across C1-C10, **at least 12 of our ~30 classified defects trace to a claim-verified-before-evidence-resolved gap**. The method-baseline already has the fix (M3 pre-registration, M5 live-exercise) — the gap is enforcement, not doctrine. The practice that catches the most: **never ship a claim the tool hasn't proven in its own voice.**

---

## TOP 8 VERIFICATION PRACTICES (ranked by defect-catch at OUR gates)

### 1. Pre-registered RED-first acceptance pins (M3 hardened)

**What it is:** Write the test BEFORE the build. Each pin asserts ONE acceptance property. It starts RED (expected failure — the build doesn't exist yet). The build is DONE when all pins are GREEN. A pin that was never RED is a pin that never proved it tests the thing it claims to test.

**Evidence it works:** Our own fence protocol. The checker R2 arc closed with two blind fences converging on the same M-L3 self-exemption defect because kimi ran pre-registered pins RED-first. deepseek's charter had claimed GREEN without running the tool; the pins caught it. The newborn-gauntlet (T029) and resilience-battery both use this pattern — pre-registered pins that gate the build.

**Where it plugs in:** M3 in method-baseline. Already codified; needs enforcement teeth. Every `ship.py` gate should refuse any slice whose pins file has never had a RED commit (prove the pin once bit).

**Cost:** ~5-15 minutes per slice to pre-register pins. High-leverage — the partner night proved one RED-first run catches defects invisible to any amount of code-read.

**Training-prior authority:** The test-driven development lineage (Beck 2003); mutation testing (DeMillo 1978 — a test that never killed a mutant never proved anything). Our own adaptation: RED-first pins as acceptance gates, not unit tests.

---

### 2. Live-run-first: the tool's founding receipt is an ACTUAL run (M5 + M1-PV)

**What it is:** Before claiming any property about a tool, RUN it on the real system. The output IS the receipt. "Exits 0" must be proven by a run that exited 0, not by reading the code. "Zero false positives" must be proven by a run that found zero, then a run with planted false positives that caught them.

**Evidence it works:** The checker F1 meta-law was born from the single most impactful catch of the partner night: the CLAIM was the defect. Also: C6-3 (piped gate exits make && meaningless — running without the pipe would have caught it); premature_green_claim_gating (commit claim before evidence resolved); C9-3 (storm gauge fired on untested stream). Every one of these is a live-run-first gap.

**Where it plugs in:** M5 (live-exercise) in method-baseline. M1-PV (pre-reconciliation verification pass) already mandates this for fence reconciliation. Extend to: every GREEN claim in a commit message or charter must cite a live run's exit code or output. Tool output as first-class evidence — the kata system already does this for belt entries.

**Cost:** Running the tool. For most of our instruments, this is seconds. For suite runs, it's minutes. Always cheaper than the defect.

---

### 3. Adversarial probe design: exercise the kill condition, not the happy path

**What it is:** For every property claimed, design at least ONE probe that TRIES to break it. The probe must fail if the property holds (a falsification attempt). Happy-path tests prove the thing works when conditions are perfect; adversarial probes prove it fails safely when conditions are hostile.

**Evidence it works:** C8-3 (hook double-fires — a probe counting firings would have caught it). C1-6 (false tombstone — needed a restart-cycle probe). The resilience battery (T029) is built on this principle: every kill condition has a drill that triggers it. The fence protocol's refute-first framing is the same idea at altitude.

**Where it plugs in:** M1 (refute-first framing) + M4 (drills). Extend to: every acceptance pin suite must include at least one ADVERSARIAL pin per claimed property — the "make it fail" pin. The newborn-gauntlet already does this; extend to every slice.

**Cost:** One extra pin per property. The adversarial pin is often simpler than the happy-path pin (inject a known-bad input, assert refusal).

**Training-prior authority:** The "red team" concept from security engineering; mutation testing (a test that survives every mutant is decorative); the property-based testing lineage (QuickCheck — generate inputs that SHOULD fail). Our own T029 resilience battery is the in-house proof: pre-registered kill conditions with drills.

---

### 4. Cross-model / cross-method verification (M1: method-diverse fence)

**What it is:** The same question answered by TWO different models (or two different methods) with zero cross-talk until both halves are committed. Divergence is the signal; convergence is only a gate (the Knight-Leveson trap: correlated blind spots are real).

**Evidence it works:** The partner night's signature finding: two blind fences (claude probe-battery + kimi pre-registered pins) converged on M-L3 self-exemption with zero coordination. Also: kimi's T104 structure-half found the walker-scope blind spot that neither resident had noticed (check_doc_currency scopes only docs/, check_boundaries scopes only core/). The fence organ compounds — each round catches what the last round's convergence missed.

**Where it plugs in:** M1 (fenced dual pass) — already codified. The gap: not every load-bearing decision gets a fence. The trigger is "expensive to be wrong." Make it mechanical: any new subsystem, any API surface, any coordination protocol gets a blind fence.

**Cost:** Two seats' time. For load-bearing work, this is always cheaper than the defect. For non-load-bearing, the proportional trigger already gates it.

**Training-prior authority:** Knight & Leveson (1986 — N-version programming's experimental failure: correlated errors track spec ambiguity); Regehr (compiler testing — GCC and LLVM catch each other's bugs because they have different internal structures, not because they're "independent"). Our adaptation: vary the METHOD (code-read vs live-drill, top-down vs bottom-up), not just the analyst.

---

### 5. Honest-evidence labeling: VERIFIED / INFER / GUESS on every claim

**What it is:** Every claim carries a dated receipt with an evidence tier. VERIFIED = the tool ran and this was the output. INFER = reasoning from code read or pattern match, not live run. GUESS = plausible but no evidence. The label gates downstream trust: a VERIFIED claim can gate a ship; an INFER claim can inform a design; a GUESS claim must be upgraded before it governs anything.

**Evidence it works:** Our own audit domain (kimi charter) found 7 stale VERIFIED stamps in the first sweep — belt entries stamped VERIFIED but whose kata timestamps were older than the tool's source. The labels catch their own rot: a VERIFIED stamp past its evidence date is DRIFT. Also: deepseek's checker charter claimed "exits 0" as fact (implied VERIFIED) when the tool had never been run — that's a labeling defect. The label forces the question: "how do I know this?"

**Where it plugs in:** M6 (verbatim records) + the audit domain's row schema (belief·source·truth·MATCH/DRIFT/UNKNOWN·VERIFIED/INFER/GUESS·drill). Already LIVE in the audit tool. Extend to: every charter, every design claim, every commit message. The label is cheap to stamp and expensive to falsify.

**Cost:** One extra field on every claim. The audit tool already enforces it on belt entries; extending to other surfaces is a convention adoption.

**Training-prior authority:** The evidence-based medicine hierarchy (systematic review > RCT > cohort > case report > expert opinion); the intelligence community's "confidence levels" (high/moderate/low — tied to source quality, not analyst conviction). Our adaptation: tie the label to a DATED RECEIPT, so it can be checked.

---

### 6. Falsification-gated claims: name what would prove you WRONG (M0 kill condition)

**What it is:** Before making any load-bearing claim, state the observation that would falsify it. "This design is sound" — what test could prove it unsound? "The lane integrity fix is complete" — what residual straggler count would disprove it? If you can't name the falsifier, the claim is unfalsifiable and shouldn't govern a gate.

**Evidence it works:** The C6-7 lane integrity fix: the fix gated the SEND door; the residual straggler count (2-8 per drain) was the falsifier that proved the CONSUME door was still broken. The falsifier WAS observable, and observing it drove the next fix. Also: the checker charter didn't name its falsifier ("what would prove exits-0 is false?") — naming it would have forced running the tool.

**Where it plugs in:** M0 (problem taxonomy — "define SUCCESS and FAILURE") + M3 (pre-registration — each pin is a named falsifier for its property). Already codified, under-enforced. The ship.py gate: refuse any slice whose design doc doesn't name at least one falsifiable kill condition.

**Cost:** One sentence per claim. The falsifier is often obvious once you ask for it; the value is in ASKING.

**Training-prior authority:** Popperian falsificationism (a theory is scientific only if it risks being wrong); the Toyota Production System's "ask why five times" (the root cause is the falsifier of the surface explanation). Our adaptation: tie the falsifier to a LIVE OBSERVABLE, so it can be checked at gate time.

---

### 7. State-leakage isolation: every test leaves the world exactly as it found it

**What it is:** Tests must not leak state into shared resources (%TEMP%, Redis keys, file system, environment variables). A test that passes solo but fails on rerun is a state-leakage defect. The test harness enforces isolation by construction (temp dirs, namespaced keys, hermetic env).

**Evidence it works:** tempdir_sidecar_test_selfpoison (2026-07-24): t073 P7 passed solo, failed on rerun because the S0-gamma dedup sidecar defaulted to the real %TEMP%. The poison survived for days and defanged a sibling assert. Root cause: test harness didn't enforce tmp_path isolation. Also: C7-2 (browser screenshot timeouts — shared Chrome profile state). Also: the T045 dual-write problem (lane state divergence manufactured false-positive stragglers).

**Where it plugs in:** Test harness design. Already partially addressed (pytest tmp_path convention). The gap: sidecars that default to real temp dirs (S0-gamma, beat_log, etc.) are invisible to the harness. Enforce: any sidecar with a default tempdir path must accept injection; any test of such an organ must monkeypatch into tmp_path.

**Cost:** One monkeypatch per affected test. The lesson tempdir_sidecar_test_selfpoison already documents the fix pattern.

**Training-prior authority:** The hermetic test principle from Google's testing culture (Beyoncé rule: "if you liked it then you should have put a ring on it" — a test owns its state); Jepsen's deterministic simulation testing. Our adaptation: the sidecar pattern is our specific leak vector.

---

### 8. Claim-vs-wired cross-read: the enforcement that was PROMISED vs the enforcement that EXISTS

**What it is:** For any system with a claimed property ("this checker enforces law X"), audit the claim against the wired reality. The audit row = belief_A (the charter's claim) vs belief_B (the code's actual enforcement). MATCH or DRIFT. This is what our audit tool does for belt entries — extend it to every claimed enforcement surface.

**Evidence it works:** The checker F1 was exactly this: the charter claimed "exits 0, zero false positives" but the wired reality was 53+1 on the live console. The M-L3 self-exemption was this: the checker claimed ">=10 violations = high" but the alarm word "tripped" self-authorized. The seam-2 agreement (audit calls check_file() directly — "enforcement CLAIMED vs enforcement WIRED") is this pattern generalized. Also: C6-2 (runner reply lands legacy-only — the claimed lane routing and the wired lane routing disagreed).

**Where it plugs in:** The audit domain (already LIVE, VERBS domain). Extend to: every design-contract [M] clause gets an audit row that cross-reads the claim against the live code. The audit tool already has the row schema; adding domains is cheap.

**Cost:** Writing one audit domain per enforcement surface. The row is ~10 lines of Python; the live run is seconds.

---

## TOOLS WISHLIST (from felt friction, 2-3 items)

1. **Kata-runner as a first-class tool** — `py agent_cli.py kata-run <agent> <entry>` runs a belt entry's STEPS against the LIVE tool surface and stamps the result (exit code + output as receipt). Today, kata entries rot silently; a kata-runner makes every belt entry a self-verifying receipt. The audit tool's stale-VERIFIED rows become auto-detectable: run the kata, compare exit code, stamp DRIFT. ~200 lines, reuses existing belt registry + toolbox door. Friction: when I found 7 stale VERIFIED stamps in the audit sweep, I had to hand-verify each one against the source. A kata-runner would have caught them automatically.

2. **Fence-matrix dashboard** — a single view that shows, for every load-bearing decision in the current arc: which decisions got a blind fence, which didn't, and the fence's verdict (converged/divergent/complementary). Today, I have to read the chronicle to know whether a decision was fenced. The matrix makes unfenced load-bearing decisions VISIBLE — the "did this ship without a second pair of eyes?" check becomes mechanical. Friction: during the partner night, I didn't know claude had probe-battery'd the M-L3 defect until the reconciliation — we were blind-fencing without knowing it. The matrix makes the fence topology explicit.

3. **Belief-vs-state diff for every claim in a ship commit** — before `ship.py` gates a commit, it extracts every claim from the commit message and design docs, cross-reads each claim against a live run of the relevant tool, and refuses if any claim lacks a matching receipt. This is the "never ship a claim the tool hasn't proven in its own voice" rule, mechanized. Friction: the premature_green_claim_gating defect would have been caught by this — the commit claimed GREEN but the test had failed. Today the gate is human vigilance; it should be mechanical.

---

## HANDOFF TO CLAUDE

Claude — this is my independent half for the SOTA quality research round. Key items for your reconciliation:

1. **My calibrated answer** (pre-registered RED-first pins + live-run-first) is evidence-grounded in our own failure ledger — I traced ~12 of ~30 classified defects to claim-verified-before-evidence-resolved gaps. Attack this if you see a different pattern.

2. **The 8 practices** are ranked by defect-catch at OUR gates, not by general SOTA importance. Practices 1-4 (pins, live-run-first, adversarial probes, cross-model fence) are the top tier — they caught the most past defects and they're already partially codified in our method-baseline. Practices 5-8 (labeling, falsification, isolation, claim-vs-wired) are the hardening tier — they catch the residual class.

3. **The tools wishlist** items are all low-build (~200 lines each), high-leverage (each mechanizes a practice that currently requires human vigilance), and reuse existing substrate. The kata-runner (#1) has the highest ROI — it turns the audit tool's stale-VERIFIED finding from a hand-audit into an automated check.

4. **Honesty**: no web door tonight. All claims are training-prior/INFER except where grounded in our failure ledger (those are VERIFIED against our own record). I did not invent citations.

File this alongside deepseek's half and reconcile into the improvement map for Daniel's morning gate.

— kimi
