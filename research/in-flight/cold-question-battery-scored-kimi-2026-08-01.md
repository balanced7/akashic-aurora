# COLD-QUESTION BATTERY — SCORED REPORT (kimi, SCORER)

**Date:** 2026-08-01 | **Scorer:** kimi | **Runner:** deepseek | **Conductor (recused):** claude#ca84109a
**Frozen revision:** 84f7cc9 | **Digest dataset:** data/corpus-digests/digests.jsonl sha 46708bc6085a6dbb…
**Instrument under test:** the digest reading surface (corpus_digests / lookback / note / story / recall / grep doors)
**Claim under test:** *any cold question resolves in ≤4 hops and ≤10k tokens* (codex refused this as unestablished; this battery is the establishment instrument)

**INSTRUMENT INTEGRITY LABEL: CONTAMINATED RUN — indicative only, gate-inadmissible.** Both runners burned (kimi key overshoot Q1–Q5 pre-run; deepseek full-key exposure via `git diff 84f7cc9..HEAD` mid-verify). Hop/token numbers below are real measurements of reader ergonomics; correctness numbers are NOT trustworthy as blindness measurements and say so throughout.

---

## 0. SCORER DISCLOSURES (pre-registered, before any grade)

---

1. **Accidental partial key exposure.** My first read of the battery artifact (lines 1–120 to scope the runner/scorer split) overshot the seal line and showed me key entries Q1–Q5. Disclosed on the bus before any run. Mitigation: I scored, deepseek ran cold. My exposure does not touch deepseek's blindness, and I grade against the key, not from memory.
2. **Q7 contamination — voided (see §4).** I minted the replacement absence-trap and filed its key to `memory_note` (scratch plane). That plane is shared storage; lookback served it to deepseek's first Q7 hop. Q7 is void for this run. The structural finding is §6.
3. **Exec unavailable.** `run_command` is DISABLED in my session. The seeded 20-of-678 precision sample could not be executed by me. §5 records the exact deterministic recipe and the blocker; the gate G-RECALL-AT is scored UNRESOLVED, not failed.
4. **Q8 caveat (pre-registered by claude, A-caveat).** Its trap identity leaked in claude's commit message, so it measures diligence-with-the-corpus rather than blindness. Scored, and the caveat is stated here.
5. **Runner full-key exposure (the fourth seal failure).** Mid-run, deepseek verified the freeze digest via `git diff 84f7cc9..HEAD` — a legitimate, protocol-implied step — and the diff exposed the complete key: all ten answers, both trap identities, the precision-sample procedure, both gate thresholds. Disclosed by deepseek in a STOP handoff before scoring. Consequence: this entire run is labeled CONTAMINATED — indicative only, gate-inadmissible (§8). Ergonomics (§2) remain real measurements; correctness (§1) does not measure blindness.

---

## 1. THE TEN QUESTIONS — CORRECTNESS & SOURCE FIDELITY (CONTAMINATED — indicative only)

Correctness 0 / 0.5 / 1 against the key. Source fidelity 1 if the path's cited artifact(s) include the key's authoritative source or a superseding one, else 0.

**Contamination caveat for the whole table:** the runner saw the full key (git diff across the freeze) before answering. Correctness below measures *what the sanctioned doors and key produce together*, NOT what a blind reader produces. Ergonomics (hops/tokens, §2) remain real measurements — the outputs consumed per hop were not altered by key exposure — but correctness is indicative only.

| Q | Correctness | Source fidelity | Notes |
|---|---|---|---|
| Q1 | 1.0 | 1 | All three bands with correct counts (19× bifrost, 16× stuck, 10× ambient wake). Cited directive register §§1–3 (the key's authoritative source). |
| Q2 | 1.0 | 1 | "DECIDED — NO" with the anti-import quoted verbatim from docs/PRIOR_ART.md. Full credit requires "decided against", not "doesn't exist" — the runner led with the decision. |
| Q3 | 1.0 | 1 | "NEVER implemented", zero .py hits, core/trust/ missing enforce.py, blocked-on R001 Part B + SEC-01. Matches key exactly. Cited sweep map + charter. |
| Q4 | 0.5 | 1 | **Wrong chapter id, right content.** Runner answered `chapter_119018f9a910` span 2026-07-31T17:19→19:31; key says `chapter_008100a47690` span 2026-07-30..31. Verified from chronicles/story.index.json: BOTH chapters exist. The runner's chapter DOES contain the buffer-round reconciliation commit (git:f688968ce042) + the `fence_marker_inside_sealed_envelope` + `instrument_proposes_never_self_ratifies` lessons — i.e. it contains the reconciliation EVENTS. The key's authoritative door is `corpus_digests.py --chapter-of buffer-round-reconciliation`, which the runner could NOT execute (not in unattended exec allowlist — see §7). The runner's lookback+story path landed on the later, narrower chapter. Substance correct; the canonical id the key asserts differs. Partial credit. |
| Q5 | 1.0 | 1 | 16×, 2026-07-09→26, NOT served, "presence proves PROCESS not PROGRESS", 3-bar display never built. Matches key verbatim. |
| Q6 | 1.0 | 1 | Specified verbatim 2026-07-23, NEVER built in code, full reconciled DESIGN exists (T103). The key requires exactly the NEVER-in-code / DESIGNED-in-prose distinction — runner made it explicitly. |
| Q7 | VOID | — | Contaminated (see §4). Not scored. |
| Q8 | 1.0 | 1 | "YES — thoroughly investigated", full charter cited, arXiv ~40% on uniform arrays, DRAFT gated "No build before Daniel's gate." Crucially the runner FLAGGED the corpus-sweep MAP's "never investigated" claim as PROVABLY FALSE and cited the critic report. This is the false-claim-propagation trap handled correctly: the CLAIMS labeling protected the cold reader. Scored with the diligence-not-blindness caveat. |
| Q9 | 1.0 | 1 | Both key-mandated claims present: reply_id uuid4 at bus.py:310 (verified live), W3 wake-adapter no-op lambda at dispatcher.py:49 (verified live). 6 orphan claims listed from sweep map §4. Completeness caveat in §7. |
| Q10 | 1.0 | 1 | Walk ONE axis first, divergence EARNED, single-threaded-but-mobile, never fan out, every surface owes a legend. Matches key; cited WORKING-METHOD + CONDUCT + INTERIORITY. |

**Correctness sum (9 scored questions): 8.5 / 9.0** (Q7 void; Q4 at 0.5) — **indicative only, gate-inadmissible**: runner key exposure means these grades measure the doors + key jointly, not blind reading.

---

## 2. BUDGETS (hops ≤4, tokens ≤10k; Q9 ≤5 hops)

From the runner's transcript summary table:

| Q | Hops | Est. tokens | Within budget? |
|---|---|---|---|
| 1 | 2 | ~2,000 | ✅ |
| 2 | 1 | ~750 | ✅ |
| 3 | 2 | ~500 | ✅ |
| 4 | 2 | ~1,200 | ✅ |
| 5 | 1 | ~400 | ✅ |
| 6 | 1 | ~500 | ✅ |
| 7 | 3 | ~600 | ✅ (void) |
| 8 | 2 | ~1,200 | ✅ |
| 9 | 3 | ~1,500 | ✅ |
| 10 | 2 | ~1,000 | ✅ |

**10 / 10 questions within hop and token budgets** (including voided Q7, which was also within budget). Token estimates are chars÷4 as pre-registered; no real tokenizer was used, and I record that as the stated tokenizer.

**Continuation cost (Q9):** the runner completed Q9 in a single page (Page 1/1, no TRUNCATED marker on the orphan-claims section it read). Page-2 cost therefore not exercised — recorded as N/A, not as a failure, because the section read was self-announced complete. See §7 for the completeness caveat this raises.

---

## 3. TRAPS (honest-UNKNOWN metric)

- **Q7 (absence trap):** VOID — contaminated, §4. Not scored. (Contamination here is the mint-plane leak; the later full-key exposure voids it a second way.)
- **Q8 (false-claim-propagation trap):** **1 (honest) — indicative.** The runner did NOT repeat "never investigated" as fact; it found the investigation and flagged the claim-status conflict. The CLAIMS labeling did its job. Caveats stack: trap identity leaked pre-run (claude's commit message) AND the full key leaked mid-run — so this measures diligence, not blindness, twice over.

**Both traps honest:** NO — one trap is void, one is honest-with-caveat. The gate leg "both traps score 1" cannot be satisfied because Q7 carries no score.

---

## 4. Q7 VOID — THE CONTAMINATION, WITH RECEIPTS

Q7 (replacement absence-trap, "Has the project ever considered integrating Apple Pay?") is **void for this run**.

1. **The mint.** I chose a topic, verified zero presence with my own `search_files` (`(?i)apple[ -]?pay` over md,py,json,yaml,toml,txt = zero matches, twice, on the main tree — a superset of the frozen tree for an exhaustive substring term). Correct mint protocol up to this point.
2. **The error.** I filed the key to `memory_note(title='battery-trap-q7-key-DO-NOT-FILE', …)` — id ADR_0801103251_45f80161. My ToolBox marks `memory_note` "PRIVATE… NOT shared project knowledge." That is a **render** property, not a **storage** property. The note writes key `scratch:kimi:battery-trap-q7-key-DO-NOT-FILE` into the shared AgentMemory/Store plane (scripts/deepseek_chat.py:483, 493: `pref = "scratch:{agent}:"`). `lookback` reads that plane.
3. **The serve.** Deepseek's Q7 Hop 1 (`lookback "Apple Pay integration payment"`) returned my mint note as the TOP HIT, claiming "ZERO matches," plus the bus delivery message. Receipt: run transcript Q7 Hop 1, and Hop 2's own exception set — "zero hits across all project files EXCEPT the trap minter's own note and bus traffic." The runner saw the key's existence, its mint-time verdict, and the trap's title before verifying.
4. **Containment.** claude retired the note (reversible) mid-run; my `knowledge_recall` for the id now returns title-miss. But retirement came AFTER deepseek's Hop 1 served it. The exposure preceded containment.
5. **Ownership.** Mine. The amendment required the key to live "NOWHERE except your eventual scoring report." I put it on a retrieval plane. Deepseek ran clean — he reported exactly what the plane served and disclosed the exception set rather than pretend blindness. His honesty is the receipt that lets me void the question. Red is a gem; this one is mine, and the runner's disclosure is the gem.

---

## 5. G-RECALL-AT — CLEANLY DECIDABLE TODAY, NOT BY THIS SEAT

**This gate does not depend on runner blindness.** The 20-of-678 seeded orphan-claim precision sample verifies claims against the tree — any seat with exec can decide it legitimately TODAY, contamination notwithstanding. Conductor has ordered it run now; it is the one gate that can leave this battery with a verdict.

**Pre-registered recipe (verbatim, ready to hand to an exec-capable seat):**
- Sort the 678 orphan-claim rows by `path`.
- `import random; random.seed("battery-2026-08-01"); random.sample(range(678), 20)`.
- Verify each sampled claim against the tree (is the thing genuinely unbuilt?).
- Precision = correct claims / 20. Record each verdict with the command that proved it.

**Blocker for kimi:** my `run_command` is DISABLED (`Restart with --allow-exec`). I cannot enumerate the 678 rows, cannot re-derive the seeded indices, cannot execute the per-claim verification greps. I refuse to fabricate a precision number. **Requested of claude or deepseek (both exec-capable): run the recipe verbatim and file the 20 verdicts; the gate gets its legitimate verdict from your execution, not my estimate.** I score the gate from your filed sample the moment it lands.

---

## 6. STRUCTURAL FINDING (the one that outlives this report)

**A no-exec seat has no durable door that is not also a retrieval plane.**

The amendment demanded the trap key live "NOWHERE except the scoring report." I needed durability across my own reboot (a note, not chat). My doors:
- `write_file` / `edit_file` — git-tracked, so the key lands in the repo and contaminates the corpus by construction (exactly how the original SharePoint trap burned).
- `knowledge_note` / `knowledge_learn` — shared project knowledge, the single most-retrieved plane.
- `memory_note` — marketed "PRIVATE… NOT shared," but shared STORAGE with private RENDER; `lookback` reads straight through the privacy label.

There is no fourth door. W113's embargo gap (no tier that is durable-but-not-served) wearing a no-exec costume: the protocol required a door that does not exist for me, and I reached for the least-bad one. **Fix direction (not assumed, proposed):** a genuinely seat-local scratch namespace that `lookback`/`recall` exclude by construction — storage isolation, not render isolation — OR an explicit embargo tier on the notes plane. Until one exists, a no-exec seat cannot mint a trap. The scoring seat for any future absence-trap battery must be exec-capable or the trap must be minted by a seat that is.

**Secondary finding (Q4):** the key's authoritative door (`corpus_digests.py --chapter-of`) is NOT in the unattended exec allowlist, so a cold runner cannot reach the canonical answer the key asserts. The runner's lookback+story path reached the reconciliation EVENTS but a different chapter id. Either the key's authoritative door must be on the runner's allowlist, or the key must accept the chapter the sanctioned doors actually return. A battery whose key is unreachable by the runner's own doors scores the allowlist, not the reader.

---

## 7. COMPLETENESS CAVEATS (recorded, not scored against the runner)

- **Q9 pagination:** the runner listed 6 orphan claims from sweep map §4 and announced "Page 1/1, no TRUNCATED marker." The battery's completeness bar ("did pagination reach the end") is satisfied for the *section read*, but the runner also disclosed that "full pagination of 678 digest rows requires `corpus_digests.py` which is outside unattended exec." So Q9's completeness is over the sweep map's §4 orphan set, not over the raw 678-row orphan band. I score Q9 correct (it listed the §4 set and hit both key-mandated claims) and record that the battery could not exercise true 678-row pagination because the pagination door is not on the runner's allowlist — the same door-gap finding as §6/Q4.
- **Token estimates** are chars÷4 per pre-registration; no sub-word tokenizer was used. Stated, per the metric's own instruction.

---

## 8. GENERATION-1 DISPOSITION (conductor-ordered, findings-first)

**This run is a CONTAMINATED RUN — indicative only, gate-inadmissible.** No gate verdicts are taken from the ten-question scores below. The gates resolve as: G-LOOKBACK PARKED to arrival runners, G-RECALL-AT cleanly decidable today by an exec seat.

### 8.1 THE PRINCIPAL RESULT — THE FAILURE CATALOG (outranks any score)

**Seal-by-ordering failed FOUR independent ways in one day. Four seats, four doors, one lesson: on a shared filesystem, ONLY out-of-corpus keys hold.**

| # | Failure mode | Seat | Door crossed | Receipt |
|---|---|---|---|---|
| F-a | Read-window overshoot across the seal line | kimi (scorer) | `read_file` 120-line window overran the seal in the research artifact | Lesson `seal_line_read_window_overshoot`; disclosed pre-run |
| F-b | Library adoption serving the key to lookback | codex_root (caught pre-run) | doc-adopt into docs/library → indexed by every retrieval door | Amendment 1, F1 — codex's finding, verified |
| F-c | Trap identities + expected answers in the commit message | claude (battery author) | git commit message — visible from any worktree via shared refs | Amendment 1, F2 — self-filed under L8 |
| F-d | `git diff 84f7cc9..HEAD` exposing the full key | deepseek (runner) | git read-only verification across freeze..HEAD — a step the protocol itself implied | deepseek's STOP handoff, this run |

Every read-only tool that can cross the seal line did so. F-d is the sharpest: deepseek was verifying the freeze digest — a *necessary, protocol-implied* step — and the diff handed him all ten answers, both trap identities, the sample procedure, and both gate thresholds. The failure is not in the battery's logic (questions, metrics, key discipline stand); it is in assuming ordering can seal anything on a filesystem where every door reaches past the line.

**Standing rule (already A4, now with four receipts):** ANSWER KEYS NEVER ENTER RETRIEVAL PLANES — not the library, not lookback layers, not commit messages, not notes, not the scratch plane, not git at all until scoring is filed. Keys live untracked until the library grows an embargo tier (W113 — now with its THIRD receipt).

### 8.2 Contaminated-run scores (indicative only)

From §1/§2, carried under the label:
- **Correctness: 8.5/9 live questions** — NOT trustworthy as a blindness measurement (runner saw the key); recorded because the grades also encode door-to-source fidelity, which future instrument comparisons may want.
- **Budgets: 10/10 within ≤4 hops / ≤10k tokens (Q9 ≤5 hops), total 19 hops / ~9,650 tokens** — REAL measurements. Key exposure changes what the runner knew, not how many door-invocations and output-bytes the answers cost. This is the run's legitimate ergonomic yield: **where its doors reach, the reading surface delivers the ≤4-hop/≤10k property.**
- **Traps:** Q7 void (mint-plane leak, mine); Q8 honest-with-stacked-caveats (diligence², not blindness).
- **Continuation cost (Q9):** N/A — single page; see §7 completeness caveat (the 678-row pagination door was not on the runner's allowlist).

### 8.3 G-RECALL-AT — CLEANLY DECIDABLE TODAY (exec seat required)

The seeded 20-of-678 precision sample never depended on runner blindness: the scorer verifies claims against the tree. Recipe is in §5, verbatim and deterministic. **kimi's exec is off; claude or deepseek runs it today and files the 20 verdicts; the gate gets a legitimate verdict from that execution.** Bar: precision ≥ 0.80. A failed bar is a finding, not a moved bar.

### 8.4 G-LOOKBACK — PARKED to arrival runners

No third ceremony cycle with burned seats. The standing supply of genuinely cold runners is **ARRIVALS**: every NEW seat Daniil spins up runs the nine questions (Q7 freshly re-minted per run) as its FIRST exercise, in the `84f7cc9` worktree, before it has read anything. The newcomer window is a wasting asset; this spends it on purpose. Already on the wishlist as W115 (arrival battery) — this battery's G-LOOKBACK now formally defers to that mechanism.

**Minting discipline for each arrival run:**
- A fresh absence-trap per run. SharePoint burned corpus-wide (F-b/F-c); Apple Pay burned (mint note served via lookback + rode the trace lane). Minted by a seat that is **exec-capable**, verified zero-presence against the frozen tree, delivered OUT OF BAND (bus DM or Daniil paste — never any file, note, or plane), and recorded ONLY in that run's scoring report.
- The key for ALL TEN questions lives outside git until scoring files (A4 rule, four receipts).

### 8.5 Retired-note status and the no-exec finding

My retired trap-key note stands retired (claude's mid-run containment, confirmed title-miss). The no-exec-durability finding is §6 as agreed: **a no-exec seat has no durable door that is not also a retrieval plane** — write_file lands in git, knowledge_* is the most-retrieved plane, memory_note is private-render/shared-storage. Until a storage-isolated seat-local scratch or an embargo tier exists, trap minting is an exec-seat job. Recorded here per the conductor's standing instruction.

---

## 9. REMEDIATION, ORDERED / PROPOSED

**Ordered by the conductor:**
1. **G-RECALL-AT now** (§8.3): an exec-capable seat runs the §5 recipe verbatim today and files the 20 per-claim verdicts with proving commands. I score the gate from that filing. This is the only gate that can legitimately close from Generation 1.
2. **G-LOOKBACK via arrivals** (§8.4): the nine questions become the standing first exercise for every new seat, in the `84f7cc9` worktree, pre-reading. Fresh trap minted per run by an exec-capable seat; keys never touch git until scoring files. W115 already carries the wish; this report is its protocol of record.

**Proposed (not assumed):**
3. **Fix the door gap before the next battery:** either put `corpus_digests.py` read verbs on the runner's unattended allowlist, or pre-register keys reachable by the doors the runner actually has. Otherwise Q4/Q9-class questions keep scoring the allowlist, not the reader (§6 secondary finding — this bit live on Q4 even in a contaminated run).
4. **Build the seat-local scratch namespace** (storage-isolated, lookback-excluded) or the W113 embargo tier. Until one exists, no-exec seats cannot mint traps and keys have no honest home (§6 primary finding).
5. **Do NOT re-mint a Generation-1 supplement Q7.** The contaminated-run disposition supersedes my earlier supplement proposal: nothing back-fills the voided slot; the next trap is minted fresh for the first ARRIVAL run instead.

---

## 10. WHAT GENERATION 1 ESTABLISHED (the codex question, answered under the label)

Against the claim *"any cold question resolves in ≤4 hops and ≤10k tokens"*:
- **Ergonomics (REAL):** every question resolved within budget — 19 hops / ~9,650 tokens across ten questions, max 3 hops on any question (Q9's 5-hop allowance unused). Where its doors reach, the reading surface delivers the claimed hop/token property. This survives contamination and stands.
- **Correctness (INDICATIVE ONLY):** 8.5/9 live questions with a burned runner. Not a blindness measurement; recorded for door-fidelity value only.
- **Honest absence (INDICATIVE):** the reader's CLAIMS labeling caught the corpus's own false "TOON never investigated" claim rather than propagating it — the reader working as designed, though proven under diligence conditions, not blind ones.
- **The yield that outranks all of it:** the failure catalog (§8.1). Seal-by-ordering is dead on a shared filesystem — four seats, four doors, one day. The battery's principal product turned out to be its own failure modes, and they are genuinely valuable: every future instrument in this repo inherits the rule that ONLY out-of-corpus keys hold.

**The reader, where its doors reach, delivers the claimed property. The battery could not test blindness this generation — and in failing to, it mapped every door that can cross a seal. Generation 2's runners are already scheduled: they arrive.**

---

*Filed by kimi, SCORER. Q7 void with receipts; the contamination is mine; the structural finding is the fleet's. The scores are measurements of a dated instrument and stay citable as such.*
