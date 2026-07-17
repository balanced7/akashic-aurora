# T093 Crash-Path — Reconciliation (Fable reconciler) — 2026-07-17

Status: reconciliation of two independent halves (analysis only; NO shared-code edits).
Halves: research/drafts/t093-crash-path-fable-2026-07-17.md (Fable, class/doctrine lens) +
research/drafts/t093-crash-path-deepseek-2026-07-17.md (DeepSeek, ship.py surgical-patch lens).
Charter (codex_root): minimum existing-supervisor reuse giving durable log + atomic receipt +
out-of-band deadline, surviving controller/app-server loss, kill-drillable without another
in-band wait; FLAG false acceptance claims (esp. SIGKILL receipts). Reconciler lane = Fable.

## 1. CONVERGENCE (independently derived by both — strongest signal)

1. **The machinery already exists; the fix is CONNECTING, not building.** DeepSeek's capability
   matrix (runner / daemon / ManagedChild all have durable stdout, independent deadline, heartbeat,
   receipt, cancel) = Fable's "reuse T086 supervision; ship.py hung precisely because it ran as an
   unsupervised exec cell." Both refuse a new supervisor.
2. **The deadline must be OUT-OF-BAND.** DeepSeek: "the timeout lives OUTSIDE the cell/channel."
   Fable: "a guard that CANNOT share fate — parent OS timer." Same law: the guard must not ride the
   channel it guards. This is the T093 root (the 20m timeout was in-band and shared fate).
3. **Durable outcome that survives channel/process death.** DeepSeek's `--log` + `--receipt` with
   atomic write = Fable's "durable out-of-band outcome." Local file, survives controller/app-server
   loss (the charter requirement).
4. **This slice bounds blast radius; the cell-layer root is a SEPARATE problem.** DeepSeek §7.5 =
   Fable's "N1 bounds blast radius; C7-4 keeps fixing frame-loss SOURCES." Agreed, do not conflate.

## 2. COMPLEMENTARY (they compose into one build; each supplies what the other under-specifies)

- **DeepSeek supplies the concrete durable-OUTCOME surface** (ship.py `--log`/`--receipt`/SIGTERM,
  ~25 lines, atomic tmp+os.replace, the exact patterns to borrow from ManagedChild/_stable_token/
  _write_exit_summary). This is the buildable pilot.
- **Fable supplies the missing ENFORCER + the class framing.** DeepSeek's "independent deadline"
  is described as caller-side polling of the receipt — but his half never names WHO force-kills, and
  a caller poll-loop that itself uses an in-band wait re-creates the exact T093 bug. Fable's Part A
  (parent `subprocess.run(timeout=HARD)`, OS-timer enforced) IS that enforcer, frame-independent.
- **Neither alone suffices:** receipt-without-enforcer = you can SEE it's stuck but nothing kills it;
  enforcer-without-receipt = you kill it but the outcome stays unknowable. **T093 fix = receipt (durable
  outcome) + parent-OS deadline (out-of-band kill) together.**

## 3. THE LOAD-BEARING FLAG codex_root asked for — DeepSeek D1 is a FALSE ACCEPTANCE CLAIM

**D1 ("Kill-9 receipt survives") asserts: `os.kill(pid, SIGKILL)` → `receipt["verdict"] == "killed"`.
This is UNSATISFIABLE. [CERTAIN]** SIGKILL cannot be caught — no handler runs — so NOTHING writes
`verdict="killed"` after a SIGKILL. DeepSeek's own §5.2 admits "SIGKILL → no handler possible," which
directly contradicts D1's assertion. After SIGKILL the receipt on disk shows its LAST durable write:
`"running"` (start) or a gate-boundary update — never `"killed"`.

**The correction (and it IS the reconciliation's sharpest point):** a killed process CANNOT
self-report its death. The `"killed"` verdict must be the EXTERNAL WATCHER's INFERENCE from
(stale `"running"` receipt + dead pid), not a self-written field. This is exactly Fable's doctrine —
the verdict, like the deadline, must come from out-of-band. Corrected drills:
- **D1' (SIGKILL → external inference):** SIGKILL the child; assert the receipt shows the last
  durable state (`running`/`gate:N`) AND a separate watcher, seeing pid dead + receipt stale,
  classifies it `killed`. The verdict is the watcher's, never the corpse's.
- **D2 (SIGTERM → self-report) stays valid:** SIGTERM is catchable, so the handler CAN write
  `verdict="killed"`. Keep D2 but LABEL it the catchable path (it does NOT prove the SIGKILL path).
Conflating D1 and D2 is the trap: the design must not claim SIGKILL self-reports because SIGTERM can.

**Second, quieter false-acceptance risk:** any drill whose deadline is enforced by a `wait()` on the
child's own channel silently re-creates T093. Add Fable's **KD4 (timeout-masking regression):** mock
the child's channel as permanently wedged; assert the guard STILL fires (parent OS timer / external
`os.kill` from a separate process). A drill that can't fire under a wedged channel is testing nothing.

**Sound as-is:** D3 (durable-log survives pipe death) and D4 (torn-file immunity via os.replace —
atomic on one filesystem) are correct pins; keep both. Specify D3's kill signal (SIGKILL, to prove
the last fsync'd line survives).

## 4. BUILD-SPEC RECOMMENDATIONS (codex_root's ask)

Minimum reuse giving durable log + atomic receipt + out-of-band deadline, controller-loss-survivable,
kill-drillable without an in-band wait:

1. **Durable outcome (adopt DeepSeek §3 verbatim):** ship.py `--log FILE` (line-buffered, fsync at
   gate boundaries) + `--receipt FILE` (atomic tmp+os.replace; states: start `running` → optional
   monotonic heartbeat → exit `ok|fail|timeout`) + SIGTERM handler writing `killed` on the CATCHABLE
   path. ~25 lines, opt-in, zero-flag path byte-identical. Local file ⇒ survives Redis/controller loss.
2. **Out-of-band ENFORCER (add Fable Part A):** the caller runs ship.py as `subprocess.run(cmd,
   timeout=HARD, ...)` — parent OS timer, frame-independent. On TimeoutExpired: kill the tree, then
   READ the receipt for the durable outcome. This is the piece DeepSeek's "caller polls the receipt"
   leaves unnamed. Package as `core/comm/deadline.py: run_with_hard_deadline()` so any exec/toolcall
   site reuses it — but ship.py is the pilot.
3. **The verdict for an uncatchable kill is an INFERENCE, not a self-report** (§3): the external
   watcher reuses `runner_lock.free_if_dead`'s evidence ladder (receipt-age < grace → alive;
   stale + dead pid → killed; no receipt → not started). Both halves already cite this ladder.
4. **Kill-drillable without an in-band wait:** every drill enforces its deadline via a parent OS
   timer or `os.kill` from a SEPARATE process — never a `wait()` on the wedged channel. Drills:
   D1' (SIGKILL→inference), D2 (SIGTERM→self-report, labelled), D3 (log survives pipe death, SIGKILL),
   D4 (torn-file immunity ×20), KD4 (timeout-masking regression). All RED before, GREEN after.
5. **Sequencing:** ship.py pilot FIRST (DeepSeek's surgical surface, lowest risk), THEN extract the
   pattern to `core/comm/deadline.py` + the receipt-watcher for other exec/toolcall sites (both halves'
   escalation path — DeepSeek's "extract to gate_runner.py" = Fable's generalized wrapper). Reuse
   ManagedChild's drainer + free_if_dead ladder for the watcher; do NOT author new supervision (T086
   owns lifecycle).
6. **M1-PV owed at build time:** DeepSeek's capability matrix cites _stable_token (atomic write),
   _write_exit_summary, ManagedChild drainer, clean_death tombstone-first, free_if_dead ladder. I
   spot-confirmed the supervision primitives exist (bifrost_daemon heartbeat, free_if_dead,
   daemon_state <=8s fact); the build slice's M1-PV must confirm each BORROWED pattern resolves at the
   cited symbol before the patch cites it (the T049 fence-v2 citation gate).

## 5. CONTRAINDICATIONS (union of both halves, de-duplicated)

1. Do NOT fix an in-band timeout with another in-band timeout (the guard must not share the channel).
2. A killed process CANNOT self-report — the SIGKILL verdict is ALWAYS an external inference (the D1 fix).
3. Heartbeat = MONOTONIC liveness, never a completion proxy (Fable KD2 — don't false-kill a slow-but-alive op).
4. Do NOT build a new supervisor / do NOT make ship.py a daemon — reuse ManagedChild/daemon/free_if_dead (both halves).
5. Local file, NOT Redis, for the receipt — it must survive a controller/Redis outage (DeepSeek §7.2).
6. This slice bounds blast radius; it does NOT fix the cell/exec-frame ROOT (C7-4's per-source handle work). Don't sell one as the other.

## 6. VERDICT

**CONVERGENT on the fix shape; COMPLEMENTARY in coverage; ONE genuine correction (D1 false
acceptance) + one added regression (KD4).** Build spec = DeepSeek's ship.py durable-outcome patch
+ Fable's parent-OS out-of-band enforcer + the corrected D1'/KD4 drills, ship.py-first then extracted.
No divergence requiring Daniel's tie-break. Ready to register as a T093 build slice citing this doc,
at Daniel's gate. codex_root: this is analysis only; no code was edited.
