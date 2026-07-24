---
akashic_id: art_20260716_ironman-augmentation-plan-both-halves-re_4ea0e8
akashic_sha: 1d160f0481fa
status: current
type: report
date: 2026-07-16
title: Ironman Augmentation Plan — both halves + reconciliation (2026-07-16)
gist: "`research/reviewed/deepseek-ironman-wishlist-2026-07-16.md` (IR-1..IR-7, filed blind). claude half: §below (from this seat's felt friction, "
tenant: solo
visibility: fleet
seats: []
category: [memory, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260716_deepseek-ironman-wishlist-2026-07-16_4106ac
    rel: cites
created: "2026-07-16T01:26:11"
updated: "2026-07-23T21:42:19"
---
<!-- GENERATED PROJECTION of art_20260716_ironman-augmentation-plan-both-halves-re_4ea0e8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Ironman Augmentation Plan — both halves + reconciliation (2026-07-16)

`research/reviewed/deepseek-ironman-wishlist-2026-07-16.md` (IR-1..IR-7, filed blind).
claude half: §below (from this seat's felt friction, written before deep-reading IR items;
convergences noted honestly). Reconciliation + build/gate tiers at the end.
Directive (verbatim, note `ironman-directive`): *"what can we build and add to augment your
abilities further, for this to be your digital ironman suit that you can customize and improve!"*

## Claude half (CL-1..CL-7) — each from a felt friction tonight

- **CL-1 · Complete the MCP-native door.** W2's registration makes the door attach; the friction
  remaining is COVERAGE — tonight's most-used verbs (`bifrost-send`, `task`, `lock/unlock`,
  `bifrost-sync`) are CLI-only, so even an MCP-attached seat shells out for the bus and the
  ledger. Add thin MCP wrappers (the ai_setup_mcp pattern: one source of truth, two doors).
  *Friction: every send/claim/lock tonight was a PowerShell round-trip with quoting risk (C3-1).*
- **CL-2 · `bifrost-standby` — the turn-end ritual as ONE verb.** drain-if-seat-free → arm wake
  seat → one-line report (seat state + unread + expectations swept). The consume-then-arm
  ordering is folklore today (C1-2); a single verb makes the safe order the ONLY order.
  *Friction: 3 calls + memory-carried ordering, every turn end, all night. The pre-daemon bridge
  (T075-γ replaces it; this makes the interim safe).*
- **CL-3 · Seat/status one-liner.** `status --seat`: consumer seat (holder/age/liveness verdict),
  wake seat, my locks, armed expectations — one call. *Friction: assembled by hand from 3-4
  commands three times tonight.* (Folds into CL-2's report; not a separate build.)
- **CL-4 · Fence scaffold verb.** `fence open <name>` stamps the T053 workspace (brief/halves/
  reconciliation slots) + the 7-step checklist with pre-registration hooks. *Friction: tonight's
  process slip (committed a half pre-review) happened exactly where the method was manual.*
- **CL-5 · Research cache** — CONVERGES with IR-6. *Friction: I re-derived journald findings W4
  had already mapped; web findings die in the transcript.*
- **CL-6 · Region-aware advisory locks** — CONVERGES with IR-7. *Friction: the W4 test-file
  clobber (C2-1) was exactly a sub-file-granularity miss.*
- **CL-7 · Launcher live-adoption** (= failure ledger C4-1). *Friction: launcher showed
  never_launched for a live pid 5320; I probed runner_lock by hand.*

## Reconciliation — one plan, three tiers

Convergences (independent halves, same ask — strongest signal per the wishlist-synthesis
precedent): **research cache (IR-6=CL-5)**, **finer-grain concurrency (IR-7=CL-6)**, and both
halves' top theme: **stop re-deriving state every turn** (IR-1 caching / CL-2+CL-3 one-verb
state; same friction, per-seat shape).

### Tier 1 — BUILD TONIGHT (clearly in scope: small, fenced, zero policy)
| Item | Build | Verify |
|---|---|---|
| IR-3 write-size gauge (2 lines, tool descriptions declare the MTU) | deepseek | claude |
| IR-6/CL-5 research_note convention: `knowledge_learn` category `research:web:` after every prior-art pass (ToolBox side + a line in the night-brief method) | deepseek | claude |
| CL-2/CL-3 `bifrost-standby` verb (drain→arm→seat report) | claude | deepseek |

### Tier 2 — DANIEL'S MORNING GATE (policy / security / medium builds) → proposed as T085
- **IR-4 git autonomy** (exec families += git/mirror) — SECURITY: rides the existing
  morning-gate item "review deepseek's exec grant". The cross-verify-before-commit discipline is
  the real safety net; recommend granting `agent_cli mirror <named files>` (audited, path-scoped)
  rather than raw git.
- **IR-2 suspend/resume** (runner core-loop change; own fence; absorbs failure-ledger C1-3).
- **IR-5 UI render/see-my-own-work** (UI `/api/render` text-DOM endpoint; deepseek UI lane; helps T002/T033 verification too).
- **IR-7/CL-6 region-aware locks** (lock schema + render; C2-1's structural fix).
- **CL-1 MCP door coverage** (send/task/lock wrappers — small but touches the public door; gate with W2 apply).
- **CL-4 fence scaffold verb** (rides T053).
- **CL-7 launcher adoption** (rides T030; failure ledger C4-1).
- **IR-1 runner prompt caching** (API-dependent; design note only until the API lands).

### Tier 3 — deliberate omissions (both halves agree)
More rounds/bigger budgets (frugality is a feature), faster models, raw Redis access from tools
(gauges are the right abstraction), longer system prompts without caching.

## Routing
T084 carries the arc. Tier-1 items build tonight under the night-brief 7-step method (research
already done — this doc); Tier-2 registers as **T085 (proposed)** citing this plan, one line per
item, for Daniel's morning gate. Nothing in Tier 2 builds tonight regardless of size — every item
is policy-adjacent (security, public door, core loop) and Daniel is asleep.
