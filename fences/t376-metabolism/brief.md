# T376 fleet metabolism — design fence opening (D of the enablement deck)

**Fence:** t376-metabolism, opened 2026-08-22 night by Vandor. Daniil gates.
Forecast F002 registered at build open (3/3 organs rotate hands-free within
10min of a trivial commit, horizon 08-29, dies_when on descope).

## CHARTER

D of Daniil's B→C→D→A ruling: "gateway/daemon/UI get runner-style stale-code
self-refresh, unified with OOB succession — fleet self-deploys A's build
commits." Motivating receipts, same day: both runners self-rotated at midday
(the pattern works where wired); shipping T380 required a HAND rotation of the
gateway (kill pid, relaunch, hope) — the exact step this organ deletes. The
reconciled design builds after this fence; Daniil ratifies.

## INPUTS

- `core/comm/self_restart.py` (the existing organ: should_restart /
  respawn_self / maybe_self_restart, fail-direction keep-running, dials).
- `scripts/bifrost_runner_deepseek.py:1451` (the loop-top adoption pattern).
- `scripts/bifrost_daemon.py` (DaemonLock singleton `bifrost:daemon:<agent>`,
  crash-loop breaker 3/5min, runner_lock.holder() check).
- `scripts/bifrost_runner_discord.py` (the gateway: liveness id `discord`,
  NO singleton lock found — verify).
- `scripts/bifrost_ui.py` (DeepSeek's integration boundary per house law).
- Doctor's live telemetry vocabulary: "beat fresh but NO progress pulse --
  ALIVE is proven, WORKING is not" (today's deepseek#52244 line, verbatim).
- Walk-01 standing debt: Heimdall owes the wedged-vs-thinking discriminator
  design note — it IS this fence's Q1.

## THE QUESTION

One metabolism organ with three triggers (stale-code / wedged / deadline)
across four process kinds (runners, gateway, daemon, UI): what extends
self_restart vs what wraps it, who holds which singleton, and what does the
rolling-refresh drill prove.

## Opening position (attack this)

- **P1. Extend, do not sibling.** The organ IS core/comm/self_restart.py grown
  two triggers: wedged (beat fresh + progress pulse absent + work queued for
  N min) and deadline (max-uptime dial, default off). No new module; the
  runners' adoption line does not change. Primitives-once.
- **P2. Adoption order by lock-readiness: daemon → gateway → UI.** The daemon
  has DaemonLock and the breaker; wire maybe_self_restart at its loop
  boundary first (cheapest, provable today). The GATEWAY HAS NO SINGLETON —
  two live gateways double-relay every Discord message and double-react the
  ladder; its slice is lock-first (reuse the runner_lock generation machinery
  keyed `discord`), restart-wire second. The UI slice is authored by Vandor
  as a snippet and WIRED by Heimdall (bifrost_ui.py boundary law).
- **P3. Succession is the existing machinery, everywhere.** respawn_self()
  with identical argv+env; successor takes the lock at a higher generation;
  elder stands down through the same singleton path crash-takeover already
  trusts. Planned succession = unplanned succession minus the surprise.
- **P4. A planned exit is not a crash.** The daemon's 3-crashes/5min breaker
  must not count metabolism exits, or a busy repo turns rolling refresh into
  a self-inflicted blocker. The exit reason rides the worklive phase
  ('restarting') and the breaker reads it.
- **P5. In-flight contracts per organ.** No organ restarts mid-work: runners
  gate on in_flight (exists); the gateway gates on relay-in-progress AND a
  non-empty ladder op queue; the daemon gates on child-spawn-in-progress;
  the UI gates on active websocket sessions (or declares itself stateless).
- **P6. The drill is the receipt.** Rolling-refresh: land a trivial commit,
  observe daemon+gateway+UI rotate hands-free inside 10min (F002's bet),
  with before/after pids and stamped shas in the drill note. No drill, no
  done — presumed broken without a dated receipt.

## Fence questions

- Q1 (the walk-01 debt, folded in): the wedged discriminator — what separates
  wedged from thinking, measured from OUR planes (beat, progress pulse, queue
  depth, phase age)? Name thresholds and their false-positive cost.
- Q2: gateway singleton — runner_lock reuse vs DaemonLock shape vs a third
  thing? Who wins a generation race during Discord reconnect?
- Q3: does the UI carry state that makes restart lossy (live websockets,
  in-memory trace buffers), and if so what is its idle boundary?
- Q4: deadline trigger — is max-uptime worth shipping at all v1, or is it a
  dial nobody should touch until an incident demands it? (My lean: ship the
  dial default-off; a trigger with no incident behind it is speculation.)
- Q5: what does the metabolism organ REFUSE to restart? (My bid: any process
  whose stamp is unknown — fail-direction keep-running is already the law;
  name anything else.)

## RULES OF ENGAGEMENT

- Blind halves; independence enforced by the door's authorship check.
- Evidence labels VERIFIED / INFER / GUESS; VERIFIED cites file:line.
- Attack P1–P6; kills credited at reconcile (red is a gem).
- One calibrated question back per half; otherwise file and name gaps.
- Two sealed halves or 48h; Vandor reconciles; Daniil gates.
- Tag load-bearing claims V1..Vn [VERIFIED/INFER/GUESS] for tally alignment.

## OUTPUT CONTRACT

- **half_a (Heimdall) — mechanism + the debt.** Numbered counters over P1–P6
  with evidence labels and file:line; the wedged-vs-thinking discriminator
  design (Q1) as a spec section (this settles the walk-01 debt); the UI
  wiring plan for the snippet Vandor authors (your boundary); answers Q2–Q5.
  Delta block per major claim (LOAD-BEARING / SENSITIVE / FIRST-SIGN /
  IGNORABLE).
- **half_b (open slot — Navi if budget allows, else Vandor files a self-
  counter after 24h).** Adversarial pass ONLY: try to break P4 (breaker
  interaction), P5 (in-flight gaps), and the gateway lock story under
  reconnect races. Output = numbered refutations with reproduction sketches,
  no design prose.
- **reconciliation (Vandor).** Merged design + kill list, then Daniil's gate;
  build slices cite the reconciled doc.

## Process

Standard fence via the door: `py agent_cli.py fence write t376-metabolism
--slot half_a|half_b --by <you>`, seal your slot when filed. Reconciliation
after two seals or 48h.
