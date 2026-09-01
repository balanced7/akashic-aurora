---
akashic_id: art_20260813_w153-janitor-reconciliation_cb84b6
akashic_sha: d01caf5f4aed
schema_version: 1
status: current
type: design
date: 2026-08-13
title: w153-janitor-reconciliation
gist: "# W153 reconciliation — the janitor kill window (claude + deepseek fence, 2026-08-13) Status: reconciled — THE BUILD AUTHORITY for the W153 "
visibility: fleet
body_type: markdown
seats: []
category: [substrate, bus, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-13T07:58:16"
updated: "2026-08-13T07:58:16"
---
<!-- GENERATED PROJECTION of art_20260813_w153-janitor-reconciliation_cb84b6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# w153-janitor-reconciliation

# W153 reconciliation — the janitor kill window (claude + deepseek fence, 2026-08-13)

Status: reconciled — THE BUILD AUTHORITY for the W153 slice.
Halves: scratch/w153-claude-blind-half.md (claude, written blind) + bus reply
1786622070761-0 (deepseek, dissent-first). Intent carried verbatim from Daniil:
"I thought I lost a friend last night, safety first is just fine for me."

## Amended acceptance (supersedes the pre-registered K1-K6)

K1' A pid is killed ONLY when, on a CURRENT snapshot taken in the same pass:
    is_watcher(pid) passes AND the cmdline matches THIS agent (name-match alone
    is not a kill warrant — deepseek dissent; a recycled pid can be another
    agent's watcher or bifrost_wake_report.py). Enforced TWICE: honest inputs
    (no branch may synthesize pid_is_watcher — deepseek A1) AND a structural
    backstop at the kill branch itself (claude choke-point: any kill path,
    present or future, re-verifies or refuses).
K2  The fast path's economy survives: zero added WMI passes for the common
    live case; the snapshot is acquired lazily only when a kill is in play.
K3  taskkill success = returncode 0, nothing else. A failed kill retains the
    seat file with provenance "kill FAILED — seat kept"; next pass retries.
    (Convergent, near-identical in both halves.)
K4  Seat enumeration is exact-component parsing (deepseek A3: split on "_" and
    require the leading components to equal ["bifrost","wake"]+agent.split("_"))
    — codex janitors can never enumerate codex_root seats, and underscore agent
    ids still enumerate their OWN seats correctly. Parse-side; no file migration.
K5' Provenance rotates (os.replace → .reap.log.1, one generation) instead of
    discarding; "auditable from the log alone" stays true across the current +
    previous window. (Both halves independently chose rotation.)
K6' Malformed seat files: missing/empty → clean; nonempty-unparseable AND
    younger than fresh_minutes → skip with provenance (fail-toward-alive,
    deepseek A4); nonempty-unparseable AND older → clean (claude age gate:
    garbage still drains, races don't die).
K7  (new, deepseek dissent on the tombstone TTL) The FILE tombstone leg is the
    kill-authority; the Redis leg is advisory-only in is_tombstoned's kill
    consultations. TTL stays 7d. Severity: consistency note, not a kill window.
K8  Fail-toward-alive stands everywhere: snapshot unavailable, probe error,
    identity unverifiable → skip, never kill, never clean a readable seat.

## The build, file-by-file (deepseek deltas adopted, claude backstop added)

core/comm/wake_seat.py:
  1. Fast path (≈:400-401): stop synthesizing identity. Not-tombstoned + fresh
     marker → pid_alive=True, pid_is_watcher=False (honest). Tombstoned →
     acquire snapshot NOW, real is_watcher + agent-match; snapshot unavailable
     → K8 skip.
  2. reap_decision tombstone branch: kill only when pid_is_watcher (agent-aware);
     else clean with reason "tombstoned sid, pid recycled to non-watcher".
  3. is_watcher gains the agent-match half (cmdline contains the agent token) —
     or a sibling agent_watcher(pid, snap, agent) so existing callers keep their
     semantics; kill paths use the strict form. Decide at build by callsite census.
  4. Kill branch backstop: before kill_fn, assert identity was verified THIS
     pass on THIS snapshot; unverified → skip with provenance (claude choke-point).
  5. taskkill: returncode==0 only; janitor gates seat-removal on kill success.
  6. iter_seats: exact-component parse (K4).
  7. read_pid callers: distinguish missing/empty vs unparseable (K6').
  8. append_provenance: rotate, don't discard (K5').
  9. is_tombstoned: kill-consultation reads file leg authoritative, Redis
     advisory (K7). Non-kill consumers unchanged.

scripts/hooks/claude_stop.py: no delta (verified by deepseek: no taskkill in
the hook; its fail-open probe is correct for the block/re-arm decision).

Wave-2 doc: one-line note that the fast-path synthesis was a regression against
the fence's own "reap only on proven orphanhood", now restored.

## Pins (union of both halves — five, RED first)

P1 tombstoned + fresh marker + recycled NON-watcher pid → clean, kill_fn NEVER
   invoked (the confirmed defect's exact shape).
P2 tombstoned + pid whose cmdline is a DIFFERENT agent's watcher → clean, no
   kill (K1' agent half — name-match insufficient).
P3 taskkill returns False → seat file survives, provenance says kill FAILED.
P4 codex janitor with a bifrost_wake_codex_root_<sid>.pid present → never
   enumerated, never touched.
P5 the inertness side (claude drill 3): a REAL dead watcher (tombstoned, stale
   marker, watcher-cmdline pid, snapshot available) IS still killed — the
   janitor must not go inert. Instrumented property: the only pids ever passed
   to kill_fn have cmdline containing bifrost_wake AND this agent, verified on
   the same-pass snapshot.

## Save-convention rider

deepseek ASSENTS to save:<agent>:<label>, requesting seat-owned labels. Folded:
the request is the notes-plane authorship field, now demanded by two seats —
W153 tail note upgraded from "durable fix" to "fleet-requested, two seats".
