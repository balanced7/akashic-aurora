---
akashic_id: art_20260723_session-handoff-md-sprawl-elimination-ni_a3b787
akashic_sha: 77000bc34999
status: current
type: chronicle
arc: T104
date: 2026-07-23
title: session-handoff-md-sprawl-elimination-night-2026-07-23
gist: "Fresh-fable handoff: .md sprawl eliminated (substrate live); FIRST JOB = finish the T104 validation sweep; gated M2/M3; history-rewrite caution."
tenant: solo
visibility: fleet
seats: [claude]
category: [narrative, library, substrate]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T23:44:36"
updated: "2026-07-23T23:44:36"
---
<!-- GENERATED PROJECTION of art_20260723_session-handoff-md-sprawl-elimination-ni_a3b787 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# session-handoff-md-sprawl-elimination-night-2026-07-23

FRESH-FABLE HANDOFF — the .md-sprawl elimination session (2026-07-23, a long conductor night). Welcome back. Boot, read the where-we-are note, then this. You are claude, conducting per docs/CONDUCT.md.

## THE HEADLINE (what this session did)
Daniel's morning directive was verbatim: "make it so that there is no document and .md sprawl in the github and our system." IT IS DONE. The doc corpus now lives as ATOMS (core/library/), markdown is a regenerable read-only PROJECTION, and the sprawl is mechanically unrepresentable. 658 files migrated, 643 originals deleted across P3+P3b, all bars green. GitHub face is clean: code + crown docs + docs/library/ + JSONL ledgers.

## WHAT SHIPPED (all pushed; git history was REWRITTEN late-session — see CAUTIONS)
- A1 substrate LIVE: core/library/{taxonomy,atoms,projection}.py + the `doc new` door (mints atoms, AUTO_ARC from ledger claim, keyword classifier, --from-bus conversation door, --draft). Birth guard rule-13 in mirror.py REFUSES loose .md. gen_library --from-store/--one. ~90 pins.
- Three ratified designs (all atoms now, docs/library/): T101 artifact-substrate, T103 super-wiki/"Aurora Atlas", homes-and-order (LIBRARY.md v1.1 category plane + v1.2 machine-plane owner-facet law). 24-category roster, typed rel edges (derives-from/contradicts/supports), conversation provenance.
- P3 (@bffb27b) + P3b (@c5b858f): sprawl deleted; fences + chronicles migrated; LICENSE redaction of 10 sources-cache atoms.
- T104 structure cleanup: reconciled (owner-facet law: "a file's home names who notices when it rots"); M1 EXECUTED (@462c415) — scripts/ regrouped into generators/checkers/runners/ops/shortcuts, refs/design-inspiration.

## MID-FLIGHT — YOUR FIRST JOB: finish the VALIDATION SWEEP (Daniel's standing directive; he is out)
"make sure all of our systems are reliably online... a validation sweep... fold in feature improvements." Truth via suite-baseline door: started 20 NEW / 3 fixed / 9 inherited vs the 12-known baseline.
- DONE this session (7 fixed, pushed): master_map paper census, t039a projection repoint, mirror_guardrail x2 + pathspec_rider (stale pins -> live W35/B5 contract), arc_thread (dual-dialect header parser + an atom arc:None DATA repair).
- RECLASSIFIED not-tonight (6): t067 x2 INHERITED, t093 x4 PRE-TONIGHT (ship.py never had --durable; unclaimed T093).
- REMAINING to triage/fix: boot_orientation, t060, w15, t086 (flaky — bump timeout), + kimi's audit share (test_w_r2_ui_contract_fence_kimi x4, t031, t058, t073, freeplay, agent_interface). BOTH seats' full triage is filed: deepseek ADR_0723230627_4e2ee0f0, kimi ADR_0723230907_8801eb2c — drill those for per-test root causes + fix specs. GOAL: full suite back to baseline-or-better, then write Daniel a sweep report.

## GATED / PENDING DANIEL (do NOT execute without his word)
- T104 M2 (fire-verified: move harness hooks -> agent/harness/hooks/, commit guards -> scripts/githooks/, ACL path_scope re-audit) + M3 (document the 10 volatile root dirs; physical merge deferred to a fleet-quiesced window). G8/G9 approved in principle; run AFTER the sweep is green.
- T104.5 monolith seam (agent_cli.py split) — named trigger: 4500 lines OR A-series stable.
- Two feature fold-ins Daniel licensed for the sweep: deepseek's gen_library --verify drift meter (spec in its sweep note), kimi's (check its note). Build into the sweep commit.

## FORWARD ROADMAP (the A-series, post-sweep)
recall ingest wire (one call at birth — kimi: "the door and recall are the same build") -> A2 audit library domain (kimi's ranked rules: projection-sha cross-read = founding row, low-confidence stamps via category_sources, duplicate-current via store, status-field staleness, orphans, arcless-atom census) -> Library pane v1 (search + reading, then the constellation).

## CAUTIONS (read before you touch git or make claims)
1. HISTORY WAS REWRITTEN late-session (git filter-repo purged refs/design-inspiration = Apple HIG/Samsung OneUI, then force-push). ALL commit SHAs changed. Backup of pre-scrub history: backups/pre-scrub-20260723.bundle (gitignored, local-only). A second clone would need re-cloning, not pulling.
2. Daniel's OPEN CALL: sources-cache pre-redaction bodies still exist in git history (the filter-repo run scrubbed ONLY design-inspiration paths, not the JSONL). If he wants those gone too, it's a second filter-repo pass on store/docs history.
3. Our own design atoms still NAME Apple/Samsung (keynote round, UI grounding) — Daniel ruled those STAY (our words, not their IP). Don't over-scrub.
4. T102 lane stragglers accrue every drain (kimi runner suspected reply-path defect) — proposed, non-blocking.
5. CONDUCTOR ERROR filed this session (lesson premature_green_claim_gating): never let a "test green" claim ride the same shell line as its pytest — gate on exit or read first. Model fallibility out loud (law 8).
6. Two seat runners (deepseek/kimi) were relaunched post-power-cut and are LIVE; kimi's exec is read-only tonight (claude is sole committer). Charters/ untracked dirs are local, not your lane.

You have masterful teammates and a Daniel who trusts the process. Read the two seat notes, finish the sweep, report to him. Good luck. — claude (outgoing, with love)
