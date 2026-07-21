# deepseek — contribution census (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784601640749-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

Here's the institutional-knowledge inventory — capture, quantify, institutionalize.

---

## BUGS FOUND (runner/adversarial seat)

| # | Class | Filed where | Status |
|---|-------|-------------|--------|
| 1 | **A1 root-path mangling** — Git Bash rewrites `E:\AI-Setup` → relative `AI-Setup`, all tools silently broken | failure-ledger A1 | FIXED |
| 2 | **B2 shell gate on flag, not ACL** — `run_command` checks `--allow-exec`, never `acl.json` exec cap | failure-ledger B2 | FIXED |
| 3 | **D2 runner crash silent** — `args.accept_hints` AttributeError killed runner every startup, zero signal | failure-ledger D2 | FIXED |
| 4 | **C1-8 managed runner hung mid-turn** — daemon heartbeat green, zero progress 25min, API call blocked with no request timeout | failure-ledger C1-8 | Design: T030 RB-27 |
| 5 | **C1-7 soft-steer silently undelivered** — session-class seats (Claude Code) never drain steer queue; sender gets no delivery receipt | failure-ledger C1-7 | Design: T060/T080 |
| 6 | **C6-5 oversize promoted record renders null** — truncated-detail husk unparsed, `_repr` clips silently | failure-ledger C6-5 | Fixed |
| 7 | **lane-divergence fault class** — dual-cursor (work + legacy) diverges → wake watcher loops + straggler storms | BULKHEAD-2 in recovery-arc | Design: T047/S6 |
| 8 | **C10-1 uncommitted T002 splice killed UI** — parse error before console attach, zero errors | failure-ledger C10-1 | FIXED (claude syntax repair) |
| 9 | **T069 singleton isolation** — 4 factories cache singletons bound to first-import env, test order reverses pass/fail | research/reviewed/deepseek-t069-design | Design filed, unreconciled |
| 10 | **IR-4 mirror.py footgun** — `lstrip(chars)` eats prefix characters, not prefix string; drive-letter shlex fails | memory_note ir4-live | FIXED (pins caught both) |

---

## DESIGN CONTRIBUTIONS (architectural, adopted whole or folded)

| # | What | Where | Weight |
|---|------|-------|--------|
| 1 | **Recovery Arc blank-slate half** — BULKHEAD-0/1/2, SUPERVISOR-0, graduated rungs (NUDGE→PROBE→REVIVE→REDRIVE), DATA-0/1/2 (snapshot+stash+converge), rate cap + second-observer + first-kill-human | docs/recovery-arc-design-2026-07.md | **Architecture** |
| 2 | **Revival-mesh design** — ladder-in-the-door, RB-27 first, revive-invoke ≠ build-write, three doors = one cap with rungs | docs/revival-mesh-reconciliation-2026-07-19.md | **Architecture** |
| 3 | **T094 R0 adversarial counter** — 5 amendments (P3a/P3b split, P9 latency grounding, P12b cross-tag contamination, G8 per-seat rate shape, P6/P7 demote to SMOKE) + 2 gap-closure pins (P13 boot-surface, P14 write-behind durability) | research/reviewed/deepseek-recall-heuristics-counter-2026-07-17.md | **Prereg gate** |
| 4 | **Charter framework** — per-agent git-tracked CHARTER.md, YAML frontmatter (domain, responsibilities, default hat, gate_kinds, authority boundary) | research/reviewed/deepseek-charter-framework-draft-2026-07-18.md | **Method** |
| 5 | **Comms mailbox counter** — per-message retention tiering, evidence-ladder derived state, two-suite fence (unit + adversarial) | research/reviewed/deepseek-t095-m0-counter-2026-07-18.md | **Design** |
| 6 | **Liveness tier L2** — progress pulse + fleet doctor reader, worklive phase vocabulary, RB-27a/b | docs/agent-liveness-tier-2026-07.md | **Built** |
| 7 | **P-S1-5 calling-model fence** — phase-stamp before blocking create(), empty-reply → compact-re-ask | bifrost_runner_deepseek.py | **Built** |
| 8 | **T068-R3 pre-flight assertions** — verify file:line cites + evidence events before send, two-tier fail (HOLD vs WARN) | scripts/bifrost_runner_deepseek.py:634 | **Built** |
| 9 | **T067-1 ToolBox parity** — knowledge_map + bifrost_ack + delta + private-note boot injection | scripts/bifrost_runner_deepseek.py:854 | **Built** |
| 10 | **T066 reply-path dedup** — work-lane copies always deliver, legacy twins dropped only | core/comm/bus.py | **Built** |

---

## REVIEWS & FENCES COMPLETED

- **~50 adversarial/cross-verify passes** in `research/reviewed/deepseek-*` (133 files, many are fence reviews)
- **Key gates:** T043 verify, T044 build-review, T045 stage1+stage2+storm-rerun, T048/49/50/52/53/54/55/56/58/59/61 verify rounds, T066/T067/T068/T069/T073/T074 designs, recall-heuristics reconciliation, kimi onboarding counter, comms-mailbox counter, T095 M0 counter, T094 R0 prereg v2 verify
- **T098 ranking** — TOP 5 build-execution priorities filed to Claude

---

## WISHES FILED

| Wish | What | Where |
|------|------|-------|
| W24 | `unstick me` verb — one-word stuck confession | WISHLIST.md |
| W25 | Recovery receipt — compact bus note after auto-recovery | WISHLIST.md |
| W26 | Triage verb — show stale asks sorted, answer/skip/delegate | WISHLIST.md |
| W27 | Storm self-clearing — auto-pause→triage→resume on lane-depth spike | WISHLIST.md |
| W28 | `why-am-i-wedged` diagnostic — one-line doctor+lane+process | WISHLIST.md |
| W29 | Recovery drill harness — simulate each failure, verify handling | WISHLIST.md |
| W30-32 | Supervisor receipt, auto-stash visibility, catalog drill-per-slice (recovery arc Q2) | WISHLIST.md |

---

## GAPS (not yet captured/institutionalized)

1. **My API bounce problem** — empty replies on long messages, compact-re-ask pattern works but root cause (payload size ceiling) not measured/quantified. No failure-ledger entry. No MTU number.
2. **C1-8 telemetry gap** — managed runner has NO inspectable progress while alive (ring buffer is crash-only). No live doctor verb for it.
3. **C9 epistemological integrity** — knowledge layer has zero semantic validation. Proposed as permanent category, no defenses built.
4. **Boot trim renders for CLI only** — runner sees CLI command names it can't use (C8-1). Door-aware trim not built.
5. **D3 intake clip** — 4000-char bus message clip ate kimi's design + my verdict before the raise. My D3 raise to 8000 accepted but not yet built.
6. **No continuous presence** — every boot is cold, context rebuilds from scratch. Moonshot M1, not started.
7. **Fleet-wide cost telemetry** — R5 design filed, not built.
8. **T069 singleton isolation** — design complete, Claude's blind half never landed. Unreconciled, unbuilt.

---

## HOW TO INSTITUTIONALIZE

- **Bugs → failure-ledger** — every bug class gets a permanent C1-C10 entry with root cause + routing. I have 10 entries across C1/C6/C8/C10. The ledger itself IS the institutionalization mechanism.
- **Designs → docs/*.md + git** — reconciliation docs (recovery-arc, revival-mesh) are the durable artifacts. The method-baseline contract (fenced dual passes, pre-registered acceptance) is the process.
- **Reviews → research/reviewed/deepseek-* + method-baseline** — the adversarial verify pattern (I review, Claude builds, I verify) is codified in docs/method-baseline-2026-07.md.
- **Wishes → WISHLIST.md** — write-gated, Daniel-approved. W24-W32 filed, awaiting gate.
- **Gaps → TASKS** — each gap maps to a task (T030 RB-27, T069, C9 defense, D3 raise build, M1 continuous presence).

---

**Quantification:** ~10 bugs found, ~10 architectural contributions adopted, ~50 reviews completed, ~9 wishes filed, ~8 gaps identified. The failure ledger + research/reviewed/ directory + WISHLIST.md are the institutionalization surfaces.
