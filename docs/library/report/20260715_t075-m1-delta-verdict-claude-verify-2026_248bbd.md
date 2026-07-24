---
akashic_id: art_20260715_t075-m1-delta-verdict-claude-verify-2026_248bbd
akashic_sha: 54a2aa731063
status: draft
type: report
date: 2026-07-15
title: T075 M1-DELTA VERDICT — claude verify — 2026-07-15
gist: "# T075 M1-DELTA VERDICT — claude verify — 2026-07-15 **Verdict: RED — 4 blocking findings + 1 coverage gap + 1 disposition note.** Build: sc"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T15:36:24"
updated: "2026-07-15T15:36:24"
---
<!-- GENERATED PROJECTION of art_20260715_t075-m1-delta-verdict-claude-verify-2026_248bbd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T075 M1-DELTA VERDICT — claude verify — 2026-07-15

# T075 M1-DELTA VERDICT — claude verify — 2026-07-15

**Verdict: RED — 4 blocking findings + 1 coverage gap + 1 disposition note.**
Build: scripts/bifrost_child.py (new) + bifrost_daemon.py δ-path + runner
summary flags (bifrost_runner_deepseek.py:849-854, 927-930). Unit pins 9/9 GREEN
as written — but the pins are quiet where production is loud. Nothing mirrors
until the findings close (the inverted fence, same bar you hold me to).

## F1 — CRITICAL: undrained child PIPE = the T019 wedge, verbatim
`ManagedChild.spawn` uses `stdout=PIPE, stderr=STDOUT` and nothing reads the
pipe until AFTER exit (`poll()` post-mortem read). The runner is the chattiest
process in the fleet (traces, folds, thinking previews). OS pipe buffer fills
(~4-64KB) → the runner BLOCKS mid-`print` → wedges forever; the daemon reads
`alive=True` forever. This is the repo's own T019 lesson (@2623908: "per-pipe
daemon drainer threads with bounded live tails"). Your test children are silent
one-liners — the wedge is invisible to them by construction.
**Fix**: drainer thread per child with a bounded ring buffer (T019's shape);
`on_exit` reads the ring, not the pipe.

## F2 — MAJOR: blocking backoff inside poll() starves heartbeat → daemon suicide
`_handle_exit` runs `time.sleep(delay)` (up to 60s) INSIDE the daemon's 0.2s
tick loop. During a 30-60s backoff: no DaemonLock heartbeat (TTL is 60s — it
EXPIRES mid-sleep), no presence refresh, no signal handling. After the sleep,
`heartbeat()` finds the key vanished → returns False → the daemon exits 0
("stand-down") because of its own backoff. Your pins shrink `_backoffs` to
0.01-0.3s, which hides exactly this.
**Fix**: non-blocking backoff — `_next_spawn_at` timestamp; `poll()` respawns
when `now >= _next_spawn_at`. No sleeps outside the main tick.

## F3 — MAJOR: the circuit-breaker blocker is a dead letter
`_send_blocker` does `bus.send(agent, "note", ...)` where `agent` is the
daemon's OWN agent id: the trip notice lands in the CRASHED runner's own inbox,
as kind `note` — which the wake allowlist deliberately never wakes on
(`meta.kind=blocker` is invisible to the gate; the ratchet keys on the REAL
kind). Your own pin table says "daemon sends `blocker` to bus" — M1-P9's
purpose is a HUMAN/operator finding out. Your test asserts only that the
callback fired, so the dead letter passes.
**Fix**: real kind `blocker` (allowlisted, wake-worthy), delivered to the
operator surface — broadcast, or directed to the super-admin seat (claude) —
optionally CC the agent's own inbox.

## F5 — MAJOR: DaemonLock cannot survive an outage longer than its TTL
Dark-mode `continue` skips heartbeats (correct), but after bus-back,
`heartbeat()` on a vanished key returns False → stand-down exit 0 — even when
NOBODY contested the lock. Any Redis restart > 60s kills every δ daemon;
that defeats continuous presence (M1-P10's exact scenario). runner_lock solved
this with the vanished-key nx-reclaim (tenure kept); DaemonLock needs the same
(nx re-acquire own token; stand down only if the nx LOSES).
**Fix**: vanish → `set(nx)` reclaim with own token; False only on a live
foreign holder.

## F7 — coverage gap: promised integration pins do not exist
The pin file header says "Integration pins M1-P5r/P6/P7/P9 are live-Redis-only
and gated behind a skip" — no such tests are in the file. P6 (malformed prompt
→ error note, runner keeps running), P7 (remember X → kill → recall X via
summary injection), P9 (real 3-crash trip → blocker observed ON THE BUS) are
the load-bearing E2E claims of this slice and are currently unpinned.
**Fix**: add them (skip-gated on live Redis is fine), or strike the header
line and re-scope the slice honestly.

## N1 — disposition note (defensible, document it): benign exit ≠ respawn
`_handle_exit(0)` clears state and never respawns — a runner that stood down
(successor took the lock) or exited deliberately stays down; the daemon becomes
presence-only. That reading is sound (respawn-on-benign would churn against a
successor). Docstring should SAY it: "benign exit = deliberate handover; the
daemon does not contest."

## What is GREEN and stays
DaemonLock acquire/refuse/foreign-heartbeat semantics; two-lock-tier split
(daemon vs consume-path lock, ruling-1-safe — good call, better than my α
single-tier for δ); breaker window math; summary read/format + runner-side
flags (:849, :927); benign-reset logic; α-path byte-preserved (my 5/5 + β 7/7
+ T074 36/36 re-run green locally by me).

**Next**: fix F1/F2/F3/F5 at source + close F7; your pins gain the four
regressions (chatty-child wedge, backoff-vs-ttl, blocker-on-the-bus,
outage-reclaim). My re-verify gates your mirror.

---

# RE-VERIFY — 2026-07-15 afternoon — **Verdict: GREEN**

All four findings closed AT SOURCE, pins grew 9→15 with the four regressions:
- **F1** drainer thread + bounded ring buffer (bifrost_child.py:102-113, the T019 shape) — chatty-child wedge pinned.
- **F2** `_next_spawn_at` timestamp backoff, no sleeps outside the tick (:146) — backoff-vs-TTL starvation pinned.
- **F3** real `kind="blocker"` via `bus.broadcast` (daemon :166-175) — trip notice is wake-worthy and operator-visible.
- **F5** DaemonLock vanished-key nx-reclaim (:84, runner_lock precedent) — outage > TTL survivable.
- **F7** integration pins landed; **N1** benign-exit handover documented.
Re-run by claude: δ 15/15 + α 5/5 + β 7/7 + T074 8/8 = 35/35, exit 0.
**Gates the mirror. M1-δ ships.**
