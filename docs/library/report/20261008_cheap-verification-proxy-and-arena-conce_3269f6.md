---
akashic_id: art_20261008_cheap-verification-proxy-and-arena-conce_3269f6
akashic_sha: 37858f1c979b
schema_version: 1
status: current
type: report
date: 2026-10-08
title: cheap-verification-proxy-and-arena-concepts
gist: "# Cheap verification / spotcheck proxy — what arena-style eval teaches (parked 2026-10-08) Status: in-flight (parked to revisit, Daniel's ca"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, memory, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-08T09:02:02"
updated: "2026-10-08T09:02:02"
---
<!-- GENERATED PROJECTION of art_20261008_cheap-verification-proxy-and-arena-conce_3269f6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cheap-verification-proxy-and-arena-concepts

# Cheap verification / spotcheck proxy — what arena-style eval teaches (parked 2026-10-08)

Status: in-flight (parked to revisit, Daniel's call 2026-10-08). Feeds the verification layer and
the one-world UI round (atom db25d1).

Origin: Daniel pointed at https://github.com/theaiautomators/jev-arena and asked what we could learn,
and whether something small/cheap could serve as a fast verification or spotcheck proxy. This note is
the synthesis so it is not lost to chat.

## The reframe that decides everything

A cheap verification proxy's trustworthiness turns on ONE question: **does the task have a checkable
ground truth?**

- **Ground truth exists** (does the pin pass? does recall surface the sealed answer? does the command
  return the expected row?) -> you want a VERIFIER, not a judge. Cheapest, soundest, already what
  suite-baseline / recall-bench / pins are. An LLM-judge here is strictly worse and is the exact
  "instrument validates itself" move that cost us 2026-10-07.
- **No ground truth** (is this handoff good? is this prose faithful? is this design sound?) -> the only
  place arena/judge concepts earn their keep, and where their traps are sharpest.

jev-arena itself, despite the name, is a VERIFIER-style lab (accuracy/latency/memory on test cases with
known answers), not a crowd-preference arena. It is a 200 GB CUDA lab bound to 127.0.0.1:8787 (which
collides with our Bifrost console port) and its model workers want NVIDIA/CUDA while we are AMD/ROCm.
So jev-arena is the WRONG shape for "cheap to call." The real crowd-preference arena is LMArena.

## What the real arena (LMArena) teaches, and why

1. **Pairwise beats absolute.** Never "score 0-100"; always "A or B". Relative judgments are cheaper
   and more stable. -> our proxy compares against a known-good baseline, never scores in a vacuum.
   (suite-baseline is already a diff; recall-bench is against sealed keys.)
2. **Bradley-Terry, not win-rate.** Beating a strong opponent moves the score more; makes the ranking
   transitive and stable. -> if we ever rank our local models for lane-routing, use BT.
3. **The Elo scale is humbling: a 100-point gap ~= 64% win rate.** Even a clear winner is ~64/36, not
   95/5. -> ONE proxy call is a weighted coin, not a proof. A single spotcheck is a weak signal
   (our race-pin detection-rate discipline restated).

## What LLM-as-judge teaches, and the traps

Foundational result (MT-Bench, Zheng et al. arXiv 2306.05685): a strong judge reaches ~80% agreement
with humans = the human-human agreement level. So a judge CAN be a real cheap proxy — WITH controls:

- **Position bias** (first slot +10-15 pts) -> shuffle order, average both orderings. Mechanical.
- **Verbosity bias** (longer wins at equal quality) -> rubric penalizing length; never holistic scoring.
- **Self-preference** (judge favors its own family) -> rotate judges across families. OUR FLEET ALREADY
  IS THIS: ask_gemini_panel + deepseek + kimi + blind halves = a cross-family panel = a bias control by
  construction. We backed into the right design.
- **Critique literature** (The Leaderboard Illusion arXiv 2504.20879; The Coin Flip Judge? arXiv
  2606.13685 — both UNREAD-IN-FULL, pointers only): judges go near-random on the HARD discriminations —
  reliable on the obvious calls, unreliable exactly where you need them. -> the proxy must know its
  discrimination floor and ABSTAIN rather than coin-flip. That is Navi's attention-floor and
  "zero is not no," one layer up.

## The house design: a tiered ladder, cost as a first-class axis

1. **Mechanical verifier** (near-zero cost) wherever ground truth exists — always tier 1.
2. **One small/local judge**, pairwise-against-baseline, shuffled, rubric-scored — the actual spotcheck.
   Cheap, fast, LOW-CONFIDENCE BY CONTRACT: it clears-with-a-flag or escalates.
3. **Cross-family panel** (expensive) — reserved for what tier 2 escalated.

Non-negotiables, each guarding a scar:
- calibrate against a sealed key set before trusting it (calibrate-the-zero);
- mandatory abstention with a found-vs-taken line (don't let it adjudicate its own silence —
  recall_adjudicates_its_own_silence one layer up);
- never run tier 2 where tier 1 applies (don't validate a thing against itself — the 10-07 theme);
- never trust one call (Elo 64/36; race-pin detection-rate).

## jev-arena's real gift

Not the engine — the PRESENTATION: inspectable test cases, measuring latency AND memory (not just
accuracy), shareable report. That is the template for showing the proxy's OWN calibration, and it is a
projection that could live on the one-world surface.

## Sharpest fit with current work

- This proxy is what would DRILL the one-world floor (does it fire on undeliverable mail? on a no-op
  reporting success?) — the floor's pre-run falsifiers, given an instrument.
- It accelerates verified-done: a cheap tier-2 gate before the expensive full verify.

## Two open paths (Daniel to pick when revisited)

- **Spotcheck-for-our-own-work**: a tier-2 judge accelerating verified-done. No GPU story. Likely first.
- **Rank-our-local-models**: BT over the fleet for evidence-based lane routing. Reopens the GPU story
  (AMD/ROCm workers), and needs per-model memory measurement we currently lack.

Sources: LMSYS Elo/Bradley-Terry blog (2023-12-07); MT-Bench arXiv 2306.05685. Critique pointers:
arXiv 2504.20879, arXiv 2606.13685 (unread in full).
