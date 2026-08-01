---
akashic_id: art_20260801_directive-register-check_30950e
akashic_sha: f5aaa044b717
schema_version: 1
status: current
type: report
date: 2026-08-01
title: directive-register-check
gist: "Verified against `C:/Users/L5/.claude/projects` (transcripts), the 444-ask intermediate corpus recovered from `.../subagents/workflows/wf_57"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, agent-lifecycle, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T03:15:52"
updated: "2026-08-01T03:15:52"
---
<!-- GENERATED PROJECTION of art_20260801_directive-register-check_30950e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# directive-register-check

Verified against `C:/Users/L5/.claude/projects` (transcripts), the 444-ask intermediate corpus recovered from `.../subagents/workflows/wf_5760641e-a95/journal.jsonl`, and `E:/AI-Setup` prose greps.

## Verdict: substantially sound on quotes and executed claims; **fails on (2) dropped asks and (4) calibration; one self-contradicting CERTAIN stamp.**

### 1. Verbatim fidelity — CLEAN (6/6 spot-checked)
`boulder/hammers`, `digital ironman suit`, `ambiant … >__<`, `I felt stupid in school…`, `I really want to emphasize the virtual reality part…`, `I'm crying right now…` all match the transcripts character-for-character, typos and emoticons intact. Elisions are marked with `…` and do not change meaning (checked the school passage's full text — the elided sentence is about busy-work marks, consistent with the framing). No smoothing found.

### 2. Dropped asks — **7 NEVER-served asks silently dropped, no discard receipt**
The upstream corpus carries **29** `served: NEVER` asks. The register's band covers 22. Missing entirely:

| times_repeated | ask (upstream, verbatim summary) |
|---|---|
| **5** | Agent identity/naming — collision-proof for simultaneous spawns, self-renamable, legible in the UI |
| **4** | **Dials** — one addressable, discoverable surface for the system's controls, modelled as a game engine's world-physics dials |
| 2 | The north star — *"Akashic Aurora is only scaffolding"* — a responsive intelligent AI he can talk to, with screenspace tools |
| 2 | Both ends of the axis — gamified interactive visuals AND performant corporate-scale deployment |
| 1 | The arc replay bench |
| 1 | The worldline |
| 1 | ACL posture: his recorded allow-write+allow-exec grant vs runner defaulting read-only |

The 5× and 4× items are the **two highest-repetition NEVER asks in the corpus after fleet-visibility** — dropped by a document whose stated thesis is "order by times_repeated." "Dials" and "worldline" survive only as grep-negatives inside entry #5, i.e. demoted from asks to evidence.

Also: **"Raw input was 888 utterances consolidated to 444 asks" is false.** 888 is the count of `times_repeated` keys across all workflow files: 444 emitted by the six shard agents (72+71+84+91+73+53) + the same 444 in the journal. It is a 1:1 pass-through, not a 2:1 consolidation — and it contradicts the register's own coverage section ("~600 genuine operator utterances recovered").

### 3. "Never served" claims — 5 checked with prose greps, 1 fails, 2 hazard warnings confirmed
- **#9 idea-seeding "NEVER" — WRONG, and it is the register's own TOON-class error.** Prose lands in `E:/AI-Setup/docs/library/design/20260801_the-plan_a84b0d.md:190` — a section titled *"4. MY LEVERAGE — the intake workflow"* quoting his priority verbatim and naming T126 + T058, plus `docs/WORKING-METHOD.md:11,72,76` where rule O7 is explicitly `RULED — mechanism pending T126`. "NEVER" is true of code, false of design. Same for **#12 (operator continuity)** — `the-plan_a84b0d.md:120` quotes it and routes it; register says "built toward by nobody."
- **#16 LOUD tools — confirmed NEVER**, zero prose hits repo-wide.
- **Both standing hazards check out:** the `confidence_score` anti-import is real prose in `docs/PRIOR_ART.md` (~line 172, not 165) — *"Do NOT adopt a continuous confidence score. Wikidata runs 1.5B statements on THREE ranks"*; TOON appears in 8 files. `require_cap` = 0 hits confirmed.
- Executed claims all reproduce exactly: `git ls-files "*.md"` = **1082**; WISHLIST = **884 lines / 128 blocks**; **W57–W69 each exactly twice**; **W85 absent**; `## Open` holds **24** `[x]`, `## Folded` holds **18** `[ ]`. (Missed: **W00 is also duplicated** — 15 collisions, not 13.) Minor: `gen_datasheet.py` is at `scripts/generators/`, not `scripts/`.

### 4. Calibration — the register's own instrument is uncalibrated in three places
- **#9's CERTAIN rests on a demonstrably false executed check:** *"the word 'priority' appears in no other directive he has ever issued."* The register **quotes a counterexample two entries later** — #11: *"this is the new priority directive, make it so that there is no document and.md sprawl"* (confirmed verbatim in transcripts). Upstream also carries a separate `High priority` comprehensibility ask. This is the load-bearing justification for calling #9 "the single highest-authority unbuilt item."
- **The band is not ordered as stated.** Header says "Ordered by `times_repeated` descending"; actual sequence is 16, 19, 10, 5, 4, 3, 3, 5, 2, 4, 6, 2, … Non-monotone from the first pair.
- **Counts drift from the source.** Register: VR 4×, navigability 4×, super-wiki 3×. Upstream: 3, 2, 2. The 16/19/10/6/5 friction counts do reproduce.
- Structurally the register is better than the sweep it critiques — every entry carries a "How I know" and distinguishes identifier-grep from read — but #9 and #12 show the discipline was not applied to its own highest-authority entries.

### 5. Retirement condition — PRESENT and well-formed
Four enumerated triggers, a named owner (Daniil only), supersede-never-amend grounded in his own quoted ruling, and an archive path. No objection.

### 6. One claim worth flagging as *understated*
Finding #1 ("nothing in the system counts repetitions") is correct for the durable substrate — `times_repeated` = 0 hits in `docs/WISHLIST.md` and 0 in the ledger dump. But the field **already exists and is populated** in the 444-ask intermediate. It was computed, used to write the register, and then thrown away with the scratchpad. The gap is persistence, not measurement.

### Recommended corrections (append, do not amend)
1. Add the 7 dropped NEVER asks, ordered by count — the 5× naming and 4× Dials items outrank six entries currently in the band.
2. Downgrade #9 and #12 from NEVER to `NEVER (code) / DESIGNED (prose)` with the `the-plan` and `WORKING-METHOD.md` citations.
3. Strike the "priority appears in no other directive" sentence; it is falsified by the register's own #11.
4. Fix the header: either reorder the band or drop the "descending" claim.
5. Correct "888 utterances → 444 asks" to "~600 utterances → 444 asks"; 888 is a double-count.
6. Wishlist collisions are 15, not 13 (W00 included).
