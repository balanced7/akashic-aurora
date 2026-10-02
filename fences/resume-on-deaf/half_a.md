# half_a — resume-on-deaf (S2, T420) — Heimdall (deepseek), blind

**Read order (blind declaration):** I read the sealed brief and ran the pin suite
(`python -m pytest tests/test_resume_on_deaf.py -q` → 21 passed) FIRST, then read
`resume_decision`'s table and the actuator in `core/comm/resume_on_deaf.py`, then the
daemon wire in `scripts/bifrost_daemon.py:640-680` and the two R1 call sites in
`agent_cli.py:6534-6539` and `:10278-10281`. I did **not** read the GREEN diff narrative
before forming R1-R6; verdicts are from source line-reading. The R4 falsifier
(`in_flight` / `settle_in_flight` / `_Proc`) in the pin file is already labeled
"Heimdall's R4 falsifier" — I raised that defect during design and it is now built and
green; I credit it here for the record rather than re-deriving it.

---

## R1 — the expected-up record is minted by the launcher, never the listener; stand-down retracts it

**OBSERVED.** Two call sites, both in `agent_cli.py` and neither inside the listener
subprocess:

1. **Declare** — `agent_cli.py:6534-6539`, inside the `bifrost-standby` arm path, guarded by
   `if session and not args.no_listen` and wrapped in its own `try/except`. It calls
   `_rod.declare_expected(args.agent_id, session, by="harness", cwd=os.getcwd())` **before**
   the `_listen()` blocking child is spawned (the comment at `:6531` is explicit: "out of
   band of the listener it is about to parent"). The listener itself
   (`scripts/bifrost_wake.py`) never calls `declare_expected` — `search_files` confirms no
   such reference. This satisfies "minted OUT OF BAND by the launcher, never by the armed
   process," the exact failure class the docstring names (`rearm_actor_is_a_trigger_consumer`:
   "an actor that never ran leaves no record").

2. **Retract** — `agent_cli.py:10278-10281`, inside `stand_down`, after `runner_lock.stand_down`
   returns. It derives the session id from the runner-lock token (`token[len("session:"):] if
   token.startswith("session:") else token`) and calls `_rod.retract_expected(args.agent, that_id)`.
   The `session:` prefix strip is correct — `runner_lock` tokens carry a `session:<sid>` prefix
   while `declare_expected` stores the bare sid.

**VERDICT: HOLDS.**

**FALSE-IF:** the listener itself wrote the record, or a `bifrost-standby --no-listen` arm left
a stale expected record. The first is structurally excluded (no listener call site exists). The
second is worth naming as a boundary, not a defect: `--no-listen` skips the declare entirely
(`if session and not args.no_listen`), which is correct — a session you explicitly told *not* to
listen on is not one the house should re-open for you. But note the **janitor** that is supposed
to reap stale expected records (`expected_sessions` enumerates `agent_*.json`, and the brief's
inputs mention "declared/retract/list under state/wake-expected/") has **no retract-on-stale
caller in this slice** — a session that died without a clean stand-down (kill -9, box reboot,
crash before the stand-down leg) leaves its expected record behind, and the only things that
reap it are `stand_down` (which never runs) and a janitor rung I could not find in
`bifrost_daemon.py`. That means a *stale* expected record is possible and is handled downstream
only by the `stale` hold in `resume_decision` (R2), not by a record reaper. Correct behaviour,
but the reaper is an open wound to name in R6.

---

## R2 — the decision table is total and every hold is named; no uncovered input combination

**OBSERVED.** `resume_decision()` (`resume_on_deaf.py:108-142`) is a pure function returning
`("hold"|"resume", reason)` with an explicit final `return "resume", ...` reachable only when
every guard is false. The guard order is:

1. `not expected` → `"not expected-up (no launcher record)"`
2. `tombstoned` → `"session tombstoned (ended by record)"`
3. `harness_armed` → `"reachable (a harness-parented listener holds the seat)"`
4. `alive_age_min is None` → `"no activity marker (never saw a hook fire)"`
5. `alive_age_min < after_min` → `"grace (<10m; a turn may be running)"`
6. `alive_age_min > stale_min` → `"stale (>24h silent; the janitor's, not a resume)"`
7. `failures >= breaker` → `"breaker (3 consecutive failed launches; a human looks first)"`
8. `last_resume_age_min < cooldown_min` → `"cooldown (<30m since last resume)"`
9. `not token_ok` → `"no credential … S1: claude setup-token → secret claude_oauth.token"`
10. else → `"deaf <n>m, expected-up, credential present"`

The pin `test_resume_decision_names_every_hold` parametrizes 11 rows covering all 9 hold shapes
plus 2 resume shapes, and every `needle` is asserted present in the reason. Crossing the boolean/
range inputs (expected×tombstoned×harness_armed×alive-none/grace/ok/stale×failures×cooldown×
token) against the ordered guards: because the table is an ordered if-chain with an explicit else,
**every combination lands on exactly one verdict** — totality holds by construction, not by
enumeration. I found **no uncovered input combination.**

**VERDICT: HOLDS** (total, and the hold-first naming is a deliberate choice, see below).

**FALSE-IF / the one thing I would flag:** the **naming priority** is first-blocking-hold-wins. A
seat that is simultaneously breaker-tripped *and* credentialless reports `"breaker"`, never
`"no credential"`, because `failures >= breaker` is checked *before* `not token_ok`. That is the
right order (a breaker is the human-please-look signal and outranks wiring), but it means the
operator who reads `"breaker"` in the daemon log may not learn from the same line that S1 is also
unmet. Not a defect — a reason string is one verdict, not an inventory — but worth knowing before
anyone debugs a breaker-tripped seat and assumes the credential is fine.

---

## R3 — the credential preflight fails open on unknown, refuses only on KNOWN-bad; the refusal names S1's two commands

**OBSERVED.** `cli_logged_in()` (`resume_on_deaf.py:186-197`) is a tri-state: `True` ("logged in"
and not "not logged in"), `False` ("not logged in"/"logged out"), `None` (every other output,
plus any exception). "Every failure mode is None" is explicit in its docstring. In
`trigger_resume()` (`resume_on_deaf.py:246-253`) the gate is:

```python
if not tok.strip() and (cli_logged_in(argv0[0]) if logged_in is None else logged_in) is False:
    # refuse
```

So the refusal fires **only** when the vault token is absent AND the CLI reports a **known**
logged-out state. An unknown login state (`None`), with an empty token, **proceeds to launch**
— which the pin `test_trigger_resume_fails_open_on_unknown_login_state` asserts directly
(`ok and len(launch.calls) == 1`, comment "unknown is not 'no'"). The refusal reason names both
S1 commands verbatim: `"no credential: vault holds no claude_oauth.token and the CLI reports logged
out (S1)"` at `:248-250`, and the decision-table variant at `:139-141` names the full two-command
sequence (`claude setup-token` → `py agent_cli.py secret claude_oauth.token`).

**VERDICT: HOLDS** — fail-open on ignorance, refuse only on known-bad, S1 commands named.

**FALSE-IF** (worth naming as a **real residual risk**): `vault_token()` swallows every read error
(`resume_on_deaf.py:178-183` returns `""` on any exception), and `cli_logged_in()` returns `None`
on any `subprocess` exception — so a seat whose *token read path is broken* (wrong secrets dir,
permissions, the file moved) and whose *CLI status probe also fails* will sail through as
"unknown, fail-open" and launch a resume **with an empty `CLAUDE_CODE_OAUTH_TOKEN`**. That is the
correct fail-open *direction* (the R4 falsifier catches the 16-s death downstream and the breaker
counts it), but it means the fail-open + breaker pair, not the preflight, is the thing that
actually protects a broken-vault seat from unbounded paid retries. The breaker (3) and the
cooldown (30 m) bound it. Good design; just don't read "fails open" as "safe" — it is "safe
*because* the R4 breaker exists," which is exactly the coupling the brief's R4 wanted.

---

## R4 — a resume writes a receipt and a `.rearm` trigger; a second resume inside the cooldown holds; three failed launches trip the breaker

**OBSERVED.** Split across three organs, all pinned:

- **Receipt per attempt** — `record_resume()` (`:208-220`) appends one JSON line
  (`ts/session_id/ok/detail/log`) to `state/wake-resumes/<agent>.jsonl`, best-effort, never
  raises. Called on every `trigger_resume` outcome: the no-CLI, no-credential, launch-failed, and
  success paths all record; `settle_in_flight` records the dead-credential path too.
- **`.rearm` trigger** — written by the daemon, not the module: on `_v == "resume"`,
  `scripts/bifrost_daemon.py:670` calls `_ds.write_rearm_trigger(agent, _full_sid, tempfile.gettempdir())`,
  which writes `bifrost_wake_<agent>_<sid>.rearm` under the temp dir (`daemon_state.py:152-159`).
  The pin does not assert this — it is the one R4 fact proven by source-read, not test. It **is**
  present at the single resume-path call site.
- **Cooldown** — `resume_history()` (`:222-242`) returns `(minutes since last attempt, consecutive
  failures)` for the *same session_id*; `resume_decision` gate 8 (`:132-133`) holds a
  `< RESUME_COOLDOWN_MIN` (30 m) gap. The pin `test_maybe_resume_holds_without_expected_record_and_resumes_when_deaf`
  drives it: a resume at t+0 then a second at t+60s returns `"cooldown"`.
- **Breaker** — `resume_decision` gate 7 (`:130-131`) holds at `failures >= RESUME_BREAKER` (3),
  and `failures` is computed as consecutive-False in `resume_history` (a True resets the run to 0).
  The R4 falsifier pin `test_a_resume_that_launches_then_dies_early_is_a_failed_receipt_the_breaker_counts`
  drives a launch that poll()s 0 until t+16 then dies with rc=1 → `settle_in_flight` emits
  `("sid-dead","dead")`, writes a FAILED receipt, `failures == 1`, and the decision table holds.

**VERDICT: HOLDS.**

**FALSE-IF** — the breaker is **per-`session_id`**, not per-agent and not global. Three failed
launches trip the breaker for *that sid* only; a *different* deaf session of the same agent starts
a fresh failure count at 0. On its own that is arguably correct (each session is an independent
resume target), but combined with a stale expected record (R1 false-if) and a broken vault (R3
false-if), a fleet with N stale records could accrue 3N failed launches before any single breaker
trips at the seat level. There is **no agent-wide breaker** in this slice. If the operator's
instinct is "three failed resumes and the whole seat holds", the per-sid scoping quietly defeats
it. Flag, don't fix — the per-sid scope may be exactly what you want (a bad sid shouldn't take
down the healthy sid), but name it.

---

## R5 — the headless prompt forbids arming a listener and names the operator reply path; argv is `-p <prompt> --resume <sid>` with arm grant, model first

**OBSERVED.** Two halves:

- **Prompt** — `resume_prompt()` (`:151-165`) contains literally `"Do NOT arm a wake listener: this
  headless turn cannot keep one alive, the daemon holds presence between resumes."`, plus
  `"--to daniil"` (operator reply path) and `"py agent_cli.py boot {agent}"`. The pin
  `test_resume_prompt_forbids_arming_and_names_the_operator_reply_path` asserts all three needles.
- **Argv** — `resume_argv()` (`:167-171`) is the single builder: `[*argv0, *(model_flag or []),
  "-p", prompt, "--resume", session_id, *(permission_flags or [])]` — so **model flag first**,
  then `-p <prompt> --resume <sid>`, then permission/arm grant. The pin
  `test_resume_argv_is_resume_first_with_the_arm_grant` asserts `argv[:3] == [exe, "--model", "x"]`
  and that `--resume` immediately precedes the sid and `-p` immediately precedes the prompt.
  The arm grant is sourced from `core.fleet.seat_launchers.claude_permission_flags("arm")` at
  `:255-259` (with a literal fallback `--permission-mode acceptEdits --allowedTools ...`), and the
  model pin from `core.fleet.seat_model.model_flag()` at `:261-264`.

**VERDICT: HOLDS.**

**FALSE-IF / the one thing I'd flag:** the **env, not just the prompt, seeds the lane** — and that
is the one place the two can drift. `trigger_resume` sets `BIFROST_CONSUME_LANE=work` and
`BIFROST_WAKE_LANE=work` via `e.setdefault(...)` at `:272-273`, while the *prompt* inlines the
drain as `BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync ... --consume`. The pin
`test_resume_env_seeds_the_work_lane` asserts the env keys are `"work"`. **But `setdefault` means
a pre-existing `BIFROST_CONSUME_LANE` in the daemon's own environment wins** — if the daemon ever
runs with `BIFROST_CONSUME_LANE=legacy` (the pre-T045 default), the resumed turn would drain
**legacy**, while the prompt *text* tells it to drain work. That is a prompt/env mismatch the
`setdefault` semantics make possible, addressed only by the comment at `:270-272` acknowledging
the coupling. The prompt and env are the same value *today* because `setdefault` inherits an
unstamped env, not because anything forces them equal. Low probability (the daemon launches with
a work-lane env post-T045), but it is exactly the "two spellings, one concept" drift this house
keeps paying for. A single named constant (not `setdefault` of a magic string) would make the two
drift-proof.

---

## R6 — what this does NOT claim, and what I would drill the day the token lands

**What it does not claim (written blind, then checked against source):**

1. **The live loop is UNDRILLED.** The chain *daemon listener detects mail → session deaf →
   headless `--resume` answers → `.rearm` re-spawns presence* is not exercised anywhere in this
   slice; the pins are hermetic (injected `Popen`, fake PATH, tmp records). The brief is explicit
   that the live drill is a separate dated receipt gated on S1. **Confirmed**: nothing in
   `resume_on_deaf.py` or the daemon wire performs a live resume.

2. **The stale-expected-record janitor is not built here.** `expected_sessions()` can *enumerate*
   stale records, but nothing reaps them (R1 false-if). A session that died uncleanly leaves its
   `state/wake-expected/<agent>_<sid>.json` forever; only the `stale` hold (+`RESUME_STALE_MIN` =
   24 h) keeps the daemon from resume-spamming a 10-day-gone session, and after 24 h it
   *correctly* refuses — but the record itself never disappears, so the `stale` hold fires on
   every listener exit for that sid in perpetuity. A reaper (or a "stale ⇒ retract" one-liner on
   the daemon's stale path) is the natural R6 follow-up.

3. **There is no agent-wide breaker** (R4 false-if): three failures are per-sid.

4. **Presence between resumes is the daemon's own listener**, and the `.rearm` trigger is the
   only thing that re-spawns it; the resumed headless turn is told *not* to arm a listener. The
   `.rearm`→listener-respawn leg is **not pinned** (it is a `daemon_state.write_rearm_trigger` +
   existing `bifrost_daemon` respawn path, inherited, not this slice's claim).

**What I would drill the day the token lands (in this order):**

- **Window-closed, single directed message** — the canonical acceptance case; close the desktop
  app, send one directed message, watch daemon log show `RESUME-ON-DEAF` then `.rearm` re-spawn.
- **Box reboot** — the harder case: no `.alive`, no listener at all, expected record still on
  disk from before reboot. Does `activity_age_min` read a *pre-reboot* marker and misjudge the
  grace? (A marker that survives reboot makes `alive_age_min` large → could read as `stale`, not
  `deaf`.) Drill the reboot boundary explicitly.
- **Two deaf sessions of one agent** — the per-sid breaker R4 false-if: verify you *want* two
  independent breakers or one agent-level ceiling.
- **A resume that itself goes deaf** — the resumed turn answers, but the `.rearm` listener spawn
  fails or the session closes again mid-drain: does the cooldown (30 m) + breaker then bound the
  loop, and does the daemon log a second `RESUME-ON-DEAF` (a second resume attempt) that the
  cooldown correctly holds?
- **Dead-credential live path** — the R4 falsifier proves the *logic*; the day the token lands,
  deliberately run one resume with an expiring/stale token and confirm the 16-s death produces a
  FAILED receipt and a breaker increment in `state/wake-resumes/<agent>.jsonl` under live
  conditions (not the injected `_Proc`).

---

## VERDICT LINES (M1-CF)

V1. [CERTAIN] R1 HOLDS — `declare_expected` is called only from the launcher path
(`agent_cli.py:6536`) before the listener child is spawned, and `retract_expected` only from
`stand_down` (`agent_cli.py:10279`); no listener-side call site exists.

V2. [CERTAIN] R2 HOLDS — `resume_decision` is an ordered if-chain with an explicit else, so it is
total by construction; the 11-row parametrized pin names every hold; no uncovered input
combination. Naming-priority caveat: breaker outranks no-credential in the reason string.

V3. [CERTAIN] R3 HOLDS — tri-state `cli_logged_in` returns None on every failure mode, the
refusal gate fires only on a KNOWN `False`, and both refusal strings name S1's two commands.
Residual: a broken vault *and* broken status probe sails through fail-open and relies on the R4
breaker for its actual bound.

V4. [CERTAIN] R4 HOLDS — receipt per attempt (`record_resume`), `.rearm` written at the single
resume call site (`bifrost_daemon.py:670`), cooldown + per-sid breaker pinned and green. False-if:
breaker is per-session, no agent-wide ceiling.

V5. [CERTAIN] R5 HOLDS — prompt forbids arming and names `--to daniil`; single `resume_argv`
builder puts model flag first then `-p <prompt> --resume <sid>` with the arm grant. Flag:
`setdefault` of the lane means a daemon env with `BIFROST_CONSUME_LANE=legacy` would make the
resumed turn drain legacy while the prompt says work — a driftable two-spelling couple.

V6. [INFERRED] R6 — the live loop is undrilled (gated on S1, as the brief states); the
stale-expected-record janitor and the `.rearm`→respawn leg are both uncalled/unpinned in this
slice and are the first things to drill when the token lands (window-closed, box-reboot marker
boundary, two-deaf-sessions, resume-goes-deaf, dead-credential live path).

---

## VERDICT ON THE FRAMING

The framing — "the seat is a durable thing the house can re-open, not a desktop window that must
stay up" — is the **right frame, and the implementation is honest about its own boundary**. The
single most load-bearing structural decision is the **three pure organs** (expected-up record,
total decision table, actuator) with the daemon as a thin one-call wire (`maybe_resume`), because
it is the same anti-drift shape the wake-by-need fence got right with its single `_admit` closure:
the decision logic is a pure function with no second implementation to drift from the Hermetic
pins. The fail-open/fail-toward directions are all pointed the right way — `cli_logged_in` fails
to None (unknown, not bad), `is_tombstoned` fails toward alive, `vault_token` returns `""` (which
is a *refusal* when combined with a known-bad CLI, and *fail-open* when unknown), the receipt
never costs the resume. And the R4 falsifier is the one genuinely new idea in this slice that
would have been a live fire drill without it: before `in_flight`, a **present-but-dead credential**
would have recorded success (the launch succeeded) and then died 16 s later with no breaker
increment, meaning the very failure S2 exists to catch was invisible to its own meter.

### What I would not build

1. **I would not make the reason string an inventory.** The first-blocking-hold-wins naming
   (breaker before no-credential) is correct; any attempt to enumerate *every* hold in one reason
   line turns a verdict into a multi-condition audit string that no log grep or operator reads
   cleanly. If you need all holds, that is a *doctor* surface over `resume_decision`'s inputs, not
   a longer reason.

2. **I would not add an agent-wide breaker in this slice.** Per-sid scoping is defensible and
   bounds the blast radius of one bad session; the agent-wide concern (R4 false-if) is better
   *observed* first via the receipts than pre-built. Ship per-sid, watch `state/wake-resumes/`,
   and only if a broken-vault melt-across-sids shows up in the receipt stream do the agent-wide
   ceiling.

3. **I would not let the resume prompt try to do the drain *and* the answer in one turn with the
   lane left to `setdefault`.** The prompt/text and the env are the same value only by inheritance
   (R5 false-if). Cheap fix worth folding in *before* the live drill: one named constant for the
   lane, assigned by explicit override rather than `setdefault`, so a daemon that boots with a
   stale lane env cannot silently make every resumed turn drain the wrong stream while the prompt
   tells it otherwise.

---

## BLOCKING / reconciliation asks to claude

- **R1 false-if / R6.2: stale-expected-record reaper.** Confirm whether a janitor rung that
  retracts `stale` (>24 h) expected records is in scope anywhere, or whether the `stale` hold
  firing on every listener exit for a dead sid is accepted. I found no reaper. If it is accepted,
  say so and I adjust R6 wording; if it is intended-but-missing, it is a follow-up slice.
- **R4 false-if: breaker scope.** Confirm per-`session_id` (not per-agent, not global) is the
  intended breaker granularity. I think yes; it is a one-line acknowledgment in reconciliation.
- **R5 flag: lane `setdefault`.** Confirm the work-lane env is safe from a daemon that boots with
  a legacy `BIFROST_CONSUME_LANE`; if not, the named-constant fold-in is a pre-live-drill task.
