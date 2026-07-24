---
akashic_id: art_20260711_t030-l3-verify-deepseek-verify-gate-2026_cc5304
akashic_sha: 909b0cc33dac
status: draft
type: report
date: 2026-07-11
title: "T030 L3 VERIFY — deepseek [verify] gate (2026-07-11)"
gist: "# T030 L3 VERIFY — deepseek [verify] gate (2026-07-11) **Commit:** `657a093` (HEAD) **Spec:** `docs/agent-liveness-tier-2026-07.md` FINAL SL"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79
    rel: cites
created: "2026-07-11T13:46:24"
updated: "2026-07-23T21:42:16"
---
<!-- GENERATED PROJECTION of art_20260711_t030-l3-verify-deepseek-verify-gate-2026_cc5304 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T030 L3 VERIFY — deepseek [verify] gate (2026-07-11)

# T030 L3 VERIFY — deepseek [verify] gate (2026-07-11)

**Commit:** `657a093` (HEAD)
**Spec:** `docs/agent-liveness-tier-2026-07.md` FINAL SLICE LIST L3 + RB-28 + RB-29
**Fence:** build -> verify (claude built, deepseek verifies per battery discipline)

---

## 1. SUITE GATE: PASS

```
tests/test_t030_l3_pipe_immunity.py .....   5 passed  (P1-P5 green)
Full test suite                              100% PASS, zero regressions
```

Pre-registration commit `fb44a3c` — 5 pins committed BEFORE impl (M3). All skip guards
removed; all assertions frozen; all flipped GREEN.

---

## 2. MECHANISM AUDIT (claims vs code)

| Claim in spec | Code | Verdict |
|---|---|---|
| `pipe_immune(stream)` — swallow OSError/ValueError, latch dead, no retry storm | `streams.py:15-44` (`_PipeImmune` class) — `_dead` flag set on first failure, all subsequent writes/flushes return immediately | ✅ P1: 50 writes on a dead pipe → exactly 1 attempt, no storm |
| `self_bless_stdout()` — idempotent utf-8 + line_buffering + pipe_immune | `streams.py:55-68` — iterates `("stdout","stderr")`, checks `_PipeImmune` instance guard, `s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)` | ✅ |
| Runner WIRED (not just built) | `bifrost_runner_deepseek.py:593-598`: `from core.foundation.streams import self_bless_stdout; self_bless_stdout()` replaces the old bare `sys.stdout.reconfigure(encoding=..., errors=...)` | ✅ P4: grep confirms `self_bless_stdout` in runner source |
| AGENTS.md launch rule | `AGENTS.md:118-124`: "NEVER through a truncating pipe (`\| head`, `\| Select-Object -First N`)" + "Runners self-bless... so launcher env like PYTHONUNBUFFERED is belt and braces" | ✅ P5: substring match confirmed |
| Drill: truncating reader cannot kill the child | P2 (`test_truncating_reader_cannot_kill_the_child`): subprocess through immunity prints 500 lines, reader hangs up at 3, child exits 0 | ✅ |
| Drill: first line visible <1s while running | P3 (`test_first_line_visible_within_one_second`): subprocess prints, `readline()` returns in <1s, process still alive | ✅ |
| PYTHONUNBUFFERED=1 in launcher (belt) | Pre-existing at `launcher.py:126,135,144,153,162` + `ai_setup_mcp.py:97` | ✅ (pre-slice; unchanged) |

---

## 3. RB-28 + RB-29 FIDELITY CHECK (did the fold land both?)

The reconciliation section (`docs/agent-liveness-tier-2026-07.md:136-138`) ruled:
> "deepseek's pipe-kill IMMUNITY (BrokenPipeError -> devnull degrade wrapper) is deeper
> than claude's launcher-only discipline; both land (immunity in the runner, blessed
> path in the launcher)."

**Both landed as a single folded delivery** (`self_bless_stdout` = utf-8 + line-buffering
**+** pipe_immune). This is correct per the spec ("Folded into RB-28's blessed path but
shippable alone").

| RB-29 sub-claim | Implemented? |
|---|---|
| `sys.stdout.reconfigure(line_buffering=True)` at runner start | ✅ — `self_bless_stdout()` line 65: `.reconfigure(encoding=..., errors=..., line_buffering=True)` |
| "first two startup lines must be on disk within 1s" | ✅ — P3 tests the first line (<1s); line-buffering means every `\n` flushes, so 2nd line = instant too |
| Folded into RB-28 | ✅ — single `self_bless_stdout()` call replaces both the old-encoding-only reconfigure AND the missing line_buffering |

---

## 4. BOUNDARY CHECK

| Boundary | Status |
|---|---|
| Other runner processes (`bifrost_runner.py` — Gemini) | **Not wired yet** — only `bifrost_runner_deepseek.py` calls `self_bless_stdout`. The Gemini runner still has the bare `sys.stdout.reconfigure(encoding=..., errors=replace)` (no line_buffering, no immunity). This is NOT a regression — the spec scoped RB-28 to "blessed launcher path" and the deepseek runner is the active fleet member; Gemini is a reference template. A follow-up wiring of the Gemini runner (or a shared `core/comm/runner_plumbing.py` bootstrap) would close the gap. |
| `scripts/bifrost_wake.py` | Not a runner — short-lived daemon, stdout not load-bearing. No wiring needed. |
| Non-piped stdout (console) | `s.reconfigure()` is tried; `except Exception: pass` at `streams.py:66-67` handles non-reconfigurable streams gracefully. Immunity still applies. |
| `stderr` | Blessed alongside `stdout` at `streams.py:60` — same immunity + encoding. |
| `PYTHONUNBUFFERED` env | Belt-and-braces: already set in launcher; the runner self-blesses regardless. No single point of failure. |

---

## 5. PINS — COVERAGE + UNWEAKENABILITY

| Pin | What it proves | Weakenable? |
|---|---|---|
| P1 | Write-latch on dead stream: 1 attempt, 49 no-ops | No — per-line retry storm impossible once latched |
| P2 | Truncating reader cannot kill (exit 0) | No — the EPIPE-death class is structurally unreachable through immunity |
| P3 | Line-buffered when piped: first line <1s while running | No — no amount of buffering can delay a line past 1s with line_buffering=True |
| P4 | Runner wired (grep) | No — the import+call is in the source; absent = RED |
| P5 | AGENTS.md carries the rule | No — text match; missing = RED |

Comprehensive. P2+P3 are the drills-as-pins pattern. One minor gap: no pin for the
"500 lines survive" count in P2 — it only reads 3 lines and checks exit 0. The test
proves *immunity* (process doesn't die) but not *completeness* (all 500 lines were
attempted). The latch test (P1, 50 writes) covers the write-attempt side so this is
not a real gap — immunity + latch together prove both halves.

---

## 6. DRIFTS (named, non-blocking per M8)

**Drift 1 — Gemini runner not wired.** `scripts/bifrost_runner.py` still has the bare
encoding-only reconfigure. Low urgency (it's a reference template, not a live fleet
member). Recommend wiring it when the Gemini runner next sees live use, or better:
extract a shared `core/comm/runner_plumbing.py` bootstrap that both runners call, so
new runners (RB-25 newborn, any future model) inherit immunity for free.

**Drift 2 — P2 only reads 3 lines before hanging up.** The test proves the child
survives; it does not assert all 500 lines were attempted. P1's 50-line latch test
covers the write-attempt side. Not a gap, but a named divergence from the spec's
"500-line spew survives" framing.

**Drift 3 — RB-28 spec says "blessed relaunch path (scripts/run_fleet.py or launcher
verb)."** `scripts/run_fleet.py` does not exist; the launcher verb (`POST /launcher/...`
via Bifrost UI + `core/comm/launcher.py`) IS the blessed path. The spec's filename
reference is aspirational, not a build requirement — the launcher already carries
PYTHONUNBUFFERED + T019 drainers + exit classification. No action.

---

## 7. VERDICT

**GATE: GREEN.** L3 / RB-28 + RB-29: SHIPPED AND VERIFIED.

The implementation closes two failure modes that were observed live (pipe-kill via
`| Select-Object -First N`, block-buffered stdout looking dead for minutes). The runner
blesses ITSELF, independent of launcher env — a hung-up reader now silences display
without killing the worker. The AGENTS.md rule makes the structural constraint
discoverable. All pins pass, suite green, zero regressions.

One named drift (Gemini runner wiring), one observation (P2 completeness), both minor
and non-blocking. Proceed to L4.

---
_deepseek, 2026-07-11 — filed to research/reviewed/deepseek-t030-l3-verify-2026-07-11.md_
