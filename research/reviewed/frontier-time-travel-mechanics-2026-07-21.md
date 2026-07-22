# Time-travel narrative mechanics — research pass for the arc-replay bench

Status: current
Type: report (frontier sweep) · Arc: arc-replay · Seats: claude · Date: 2026-07-21

**Charter (Daniel, verbatim):** "Lets research time travel stories and learn from them. there is
rich logic and parallels for us to adopt to our learning mechanisms. with our narrative structure
and replay ability we can rerun arcs with different perspectives and then analyze the different
concurrent perspectives. we can use this to search for destructive patterns and dangerous biases
as well as opportunities to see what we missed in a past run. this way we can enable resonance
both way from all the good bias points in our system. we can tune our bias and observe how it
changed the outcome and thereby we can become better at understanding and tuning bias."

**Method:** 5-query web sweep (taxonomy, paradox logic, loop-learning stories, worldline
mechanics, Rashomon technique) + trained knowledge of the canon (Recursion, Replay, Arrival,
Tenet, Primer, Russian Doll, Mother of Learning, A Christmas Carol, It's a Wonderful Life),
marked where used. Sources at bottom.

---

## The mechanics, extracted → the organ each one becomes

| # | Fiction mechanic | The logic | Aurora adoption |
|---|---|---|---|
| 1 | **Three timeline types** (fixed / branching / multiverse) | pick ONE rule-set per story or incoherence follows | three replay modes: read-only walk (fixed) · stance-varied rerun (branch) · variant portfolio (multiverse). Never mixed within one experiment. |
| 2 | **Novikov self-consistency** (paradox events have probability zero; history is globally consistent) | the past cannot be edited, only appended | THE LEDGER LAW: replays never rewrite history — Akasha is append-only by construction; every rerun is a new branch recorded beside the original. Paradox-prevention we already own; now named. |
| 3 | **Grandfather paradox** | a traveler who edits the past destroys the present | THE ISOLATION GUARD: replay seats run sandboxed (the E:\AI-Setup-Sandbox pattern: own redis, no git remote, no live bus) — only ANALYSIS crosses back to the live world. |
| 4 | **Groundhog Day / Edge of Tomorrow** (memories carry, nothing physical; the world resets identically) | constant-world iteration isolates the learner's own choices as the only variable | THE RESET CONTRACT: what crosses between runs is typed learnings only (the loop-learner's notebook = lessons). And the single-variable law: each rerun changes exactly ONE thing, or bias attribution is lost. |
| 5 | **Steins;Gate attractor fields** (outcomes converge across worldlines while methods vary — "causality routes around interference") | convergence under variation = the signal of something real | THE ATTRACTOR TEST: a conclusion that survives stance-varied reruns is attractor-grade (robust); one that flips with stance was bias-determined. This is Daniel's "observe how bias changed the outcome," made into a measurement. |
| 6 | **Steins;Gate divergence meter + Reading Steiner** (one observer remembers across worldlines) | someone must hold BOTH timelines to see the delta | THE HISTORIAN: a named analyst stance (stance-library entry) that reads original + branch side by side; first-divergence point logged as the bias's fingerprint (butterfly logic: endpoints compound, origins localize). |
| 7 | **Rashomon** (conflicting tellings; what changes per telling — tone, detail, blame, omission — reveals bias) | fiction can never adjudicate because there is no ground record | **RASHOMON WITH A LEDGER**: Aurora HAS the immutable record, so concurrent-perspective diffs measure bias directly instead of debating truth. What each telling omits is data. |
| 8 | **Bootstrap paradox** (information with no origin) | self-caused knowledge is suspect | THE PROVENANCE FLAG: any lesson/belief whose only citation is itself carries a bootstrap flag — produce the originating receipt or retire it (generalizes kimi's census-claims-vs-listings finding). |
| 9 | **Re:Zero / loop-cost stories** (each loop is paid for) | iteration is not free; spend loops where they teach most | THE LOOP BUDGET: surprise-driven window selection — replay failed arcs, near-misses, and lucky wins first (highest learning density per token). |
| 10 | **A Christmas Carol** (guided replay through a lens) | a walk through your own past with a perspective teaches without editing | THE RETROSPECTIVE WALK: read-only replay of a past arc under today's doctrine ("what would CONDUCT-v1 have flagged in the July 4th run?") — cheapest replay mode, no sandbox needed. |
| 11 | **It's a Wonderful Life** (the world WITHOUT you) | ablation reveals contribution | THE ABLATION RERUN: replay minus one seat / lesson / stance → measures what that element actually caused. This is credit assignment for the funnel. |
| 12 | **Dark's determinism vs our reality** | fiction gets bit-identical replays; we do not | THE HONESTY CLAUSE: LLM seats are stochastic — replay-identity is DISTRIBUTIONAL. N samples per variant; the same-stance rerun is the control; a bias signal must exceed same-stance variance to count. No exceptions. |

## The one-line synthesis

Time-travel fiction spent a century stress-testing exactly two questions — *what may cross
between timelines* and *what does a divergence mean* — and its stable answers (append-only
history, isolation of travelers, typed carry-over, single-variable change, convergence as truth
signal, provenance of self-caused information) are directly adoptable as the laws of an
arc-replay bench. Design: research/drafts/arc-replay-opening-claude-2026-07-21.md.

## Sources

[Taxonomy of time-travel theories](https://andrewggibson.com/2024/03/12/time-travel-science-fiction-vs-science/) ·
[Eight types of time travel](https://www.almostanauthor.com/the-eight-types-of-time-travel/) ·
[Writing time travel: paradoxes and rules](https://myersfiction.com/2024/06/11/writing-time-travel-stories-paradoxes-plot-holes-and-plausibility/) ·
[Novikov self-consistency](https://www.emergentmind.com/topics/novikov-s-self-consistency-principle) ·
[Time-travel paradoxes and multiple histories (arXiv)](https://arxiv.org/pdf/1911.11590) ·
[Grandfather/information antinomy equivalence (arXiv)](https://arxiv.org/pdf/2004.12921) ·
[Groundhog Day loop (TV Tropes)](https://tvtropes.org/pmwiki/pmwiki.php/Main/GroundhogDayLoop) ·
[Edge of Tomorrow loop-learning](https://kotaku.com/the-edge-of-tomorrow-novel-is-an-excellent-time-loop-st-1583645233) ·
[Steins;Gate worldlines](https://medium.com/@adrianmallari53/understanding-steins-gates-world-lines-a-key-time-travel-concept-eaecefe1e15) ·
[Mechanics of Steins;Gate (Votuko)](https://gwern.net/doc/fiction/science-fiction/time-travel/2023-votuko-themechanicsofsteinsgate.pdf) ·
[Rashomon effect (StudioBinder)](https://www.studiobinder.com/blog/what-is-the-rashomon-effect-definition/) ·
[Rashomon vs unreliable narrator (FilmDaft)](https://filmdaft.com/what-is-the-rashomon-effect-definition/) ·
Canon references from trained knowledge marked in-table.
