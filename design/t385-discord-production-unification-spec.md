# T385 Discord production unification — reconciled build specification

Date: 2026-09-05  
Owner: Sunshine (`sol`)  
Operator ruling: "lets move the three seats from alpha to production, this should fix many of the bugs and reduce complexity. then lets fold in and unify the general improvements and finally get this thing rock solid, elegant and dependable"

## Problem taxonomy

This is a deployment-consistency and lifecycle-ownership failure, not primarily a
Discord permission failure. On 2026-09-04 every named process could be alive while
the route remained impossible: the Discord gateway and Sunshine watcher were connected
to production Redis on port 16379, while the gpt-new watcher and Sunshine fleet
daemon/runner were connected to alpha Redis on port 16381. The worktree's
`.aurora-world` marker was created after one service had already started, so process
restart order silently selected which services could hear each other.

The governing distinction is:

- **checkout world** protects ordinary work performed from a code worktree;
- **service world** is an explicit deployment decision carried by every persistent
  service launch and visible in its command line.

Conflating those authorities caused the fracture. Changing the ignored worktree marker
from alpha to prod would repair today's processes but make development commands from the
worktree silently production-authoritative. The production tasks instead receive an
explicit pre-import world pin through one launcher. The alpha marker remains a guard for
ordinary worktree use.

## Migration unit

The three seat-facing Scheduled Tasks move as one unit:

1. `AkashicAurora-SunshineDiscord` — Sunshine's bound Codex Discord ingress;
2. `AkashicAurora-GptNewDiscord` — the distinct gpt-new bound Codex ingress;
3. `AkashicAurora-SunshineFleet` — Sunshine's managed runner and outbound feed.

`AkashicAurora-DiscordGateway` is not a seat, but it is part of the same causal route and
must carry the identical production pin. A mixed gateway/seat migration is forbidden.
`AkashicAurora-EarWatchdog` is retained only as a periodic nudge of that owned gateway
task; it may not launch a gateway process itself.

## Invariants

1. Every task above launches through `scripts/run_aurora_service.py --world prod -- ...`.
2. The launcher sets `AKASHIC_WORLD` before importing any Aurora module, discards ambient
   `REDIS_HOST`, `REDIS_PORT`, and `REDIS_DB`, and verifies that the resolved world and
   foundation endpoint agree before executing the target in-process.
3. The launcher accepts only the three service entry points used here
   (`bifrost_runner_discord.py`, `bifrost_daemon.py`, and `codex_bifrost_wake.py`) under
   the same repository root. It never invokes a shell.
4. Task Scheduler owns exactly one instance of each persistent service. A live orphan is
   not an acceptable substitute for a `Running` task with correct ancestry. Because a
   live kill drill proved this host does not honor `RestartOnFailure`, the existing
   EarWatchdog invokes `schtasks /Run` for the owned gateway task every minute;
   `IgnoreNew` makes the same nudge inert while the gateway is healthy.
5. The existing Sunshine and gpt-new state paths, continuity thread IDs, source thread
   IDs, and `completed-history-fork` bindings remain byte-for-byte unchanged.
6. This migration grants no new authority. Sunshine retains its already-authorized
   guarded write/exec launch flags. gpt-new remains unregistered and read-only until a
   separate operator-ratified identity and capability decision.
7. The deployment branch incorporates the current master improvements before activation;
   committed code and running code are reported as separate receipts.
8. Discord outbound delivery has one process-lifetime deployment owner: the production
   gateway holds the existing pump lease across beats and refreshes it independently of
   webhook latency. Legacy seat daemons remain bounded fallbacks only while that owner is
   absent. A message addressed to the operator with no registered private seat lane fails
   loudly and never widens into the global Discord channel.

## Pre-registered acceptance

- **P1 — launch structure:** a pin fails unless all four tasks use the world launcher and
  carry `--world prod` before their target script.
- **P2 — pre-import endpoint:** with ambient alpha and foreign Redis variables present,
  the launcher resolves production and the foundation reports Redis 16379.
- **P3 — target containment:** a target outside the repository or outside the explicit
  service allowlist refuses before execution.
- **P4 — continuity preservation:** the two state files retain their prior thread tuple
  across reinstall and restart.
- **P5 — live topology:** Task Scheduler reports all four tasks `Running`; each owned
  process (and Sunshine's managed child) has scheduler ancestry and an established Redis
  connection only to 16379. None of these processes remains connected to 16381. The
  EarWatchdog is enabled with a one-minute repetition and targets only the gateway task.
- **P6 — code generation:** running services load the deployment branch commit containing
  the master fixes plus this slice; no old orphaned gateway remains.
- **P7 — causal delivery:** a fresh ordinary Discord message in each bound seat channel
  produces the exact chain Discord message ID -> production destination stream -> watcher
  admission -> causal reply -> Discord API readback. Synthetic outbound posts are useful
  probes but cannot satisfy this human-authored gate.
- **P8 — authority:** gpt-new still lacks write/exec tools; Sunshine's authenticated
  operator turn exposes only the already-governed capability surface.
- **P9 — visible cold state:** when the pure inbound policy returns a `cold_seat`
  explanation, the gateway replies in the originating Discord channel. A diagnostic
  retained only in the gateway process is not an operator-visible warning.
- **P10 — readiness, not presence:** gateway health requires one fresh, process-owned
  Discord event-loop generation whose PID, world, and live process agree. A command-line
  match alone is never readiness. A wedged event loop exits itself only after twice the
  existing readiness TTL; the external task nudge then restores scheduler ownership.
- **P11 — one verb surface:** the already-declared shared verbs `glance`, `orient`,
  `shadow`, and `college` are callable through CLI, MCP, and the runner ToolBox. `glance`
  reads only the named durable ledger authority, carries source-derived identities and
  explicit `UNCHECKABLE` organs, and its compact brief has no identity authority. Door
  tests exercise each real membrane; importing an MCP server into a captured CLI test
  process is not accepted as transport evidence.
- **P12 — clean-clone Codex contract:** the current Codex runbook may reference only
  committed hook adapters, wrappers, fixtures, and tests. Codex and Claude payloads remain
  separate adapters; duplicate user/repository hook delivery is suppressed atomically;
  event-scoped subject labels precede inherited hints. Synthetic contract pins do not
  upgrade the registry's deliberately pending live T2-T5 observations.
- **P13 — one outbound authority:** while the production gateway is ready, its stable
  process token holds the Discord pump lease across multiple beats and a competing daemon
  cannot pump. A directed operator reply with no registered seat webhook is journaled as a
  route failure, advances the display cursor once, and never appears in global Discord.
- **P14 — honest wake cost:** App Server thread-lifetime cumulative usage remains visible
  but is never labeled or priced as one Discord wake turn. The host derives the current
  turn total from each model step's `last` sample, records the number of model steps, and
  falls back to the final step—not the thread lifetime—when step samples are unavailable.

## Failure drills

1. Start a second gateway against production: the singleton must refuse it without
   disturbing the owned gateway.
2. Terminate the exact owned gateway process (not a name-wide kill): the periodic
   EarWatchdog must start the gateway task and restore its scheduler-owned production
   connection within 90 seconds. `RestartOnFailure` XML alone does not satisfy this gate.
3. Restart each continuity task: its identity-bearing thread tuple and admitted-turn
   count must remain stable, and it must reconnect to production without admitting a
   model turn. The private stream watermark may advance while ignored production rows
   are consumed; a whole-file hash is therefore not an identity invariant.
4. Present an out-of-tree target to the launcher: it must refuse without executing it.

## Bounds and rollback

The live human-authored P7 receipt requires Daniel to send the ordinary messages; until
then the deployment may be described as production-aligned and synthetically exercised,
not end-to-end accepted. Discord and Redis outages remain external failure modes and must
render as such.

Before task replacement, export the four Scheduled Task definitions and capture process,
thread-binding, and endpoint baselines. Rollback restores those definitions and the prior
deployment commit. The continuity state files are never deleted, rewritten, or rebound.
