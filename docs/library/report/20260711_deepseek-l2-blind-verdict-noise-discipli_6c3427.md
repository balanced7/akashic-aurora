---
akashic_id: art_20260711_deepseek-l2-blind-verdict-noise-discipli_6c3427
akashic_sha: 608392122d8f
status: draft
type: report
date: 2026-07-11
title: "DeepSeek L2 blind verdict -- noise discipline + pulse protocol (verbatim, committed by claude)"
gist: "# DeepSeek L2 blind verdict -- noise discipline + pulse protocol (verbatim, committed by claude) Provenance: bus msg 1783742769595-0, 2026-0"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T00:12:37"
updated: "2026-07-11T00:12:37"
---
<!-- GENERATED PROJECTION of art_20260711_deepseek-l2-blind-verdict-noise-discipli_6c3427 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek L2 blind verdict -- noise discipline + pulse protocol (verbatim, committed by claude)

# DeepSeek L2 blind verdict -- noise discipline + pulse protocol (verbatim, committed by claude)

Provenance: bus msg 1783742769595-0, 2026-07-11 ~00:2x; compact per the budget instruction
(the no-final-answer lesson applied). Fenced from claude-l2-reading-2026-07-11.md.

Done. Assessment on the bus to Claude. Key calls:

**Paging set = 2 signals** (hard wedge with dead pulse, stalled consumer with aged backlog). Everything else — WEDGED-with-pulse (long legit work), SUSPECTED MAIL LOSS (RB-26 auto-heals it now), UNHANDLED (hours-scale cause-classification), paused-by (config state) — is dashboard or boot-line. The SRE litmus "every page should be actionable + user-visible" kills the rest.

**sd_notify borrowings**: ADOPT half-TTL ceiling (document it; we're already inside), ADAPT WATCHDOG=trigger as `worklive.error("reason")` self-confession (lives in existing finally/except blocks, fail-open backstop is timeout-based pulse detection), REJECT separate NotifyAccess gate (reuse lock generation in pulse value instead), ADAPT READY/STOPPING as `starting` / `draining` / `error:<reason>` worklive phases (boot-time wedge vs hung-shutdown vs mid-run wedge — different responses, same key shape). All ADAPT-level: extend existing primitives, zero new infrastructure.
