# resume-on-deaf — half_a (blind half) — Heimdall (deepseek)

**Blind discipline honored.** Per the rules of engagement I read the 18 pins and
`resume_decision()`'s table BEFORE the daemon wire. Order actually executed:
(1) `tests/test_resume_on_deaf.py` in full, (2) `core/comm/resume_on_deaf.py` in full,
(3) only then `scripts/bifrost_daemon.py`'s listener poll, `agent_cli.py` bifrost-standby
and stand-down, `daemon_state.write_rearm_trigger`, `wake_seat.harness_armed` /
`activity_age_min` / `is_tombstoned`. The pins ran 18/18 GREEN on the first pass.
No live resume was attempted against any seat (S1 not landed; the ~16 s failed-receipt
breaker trip is a real cost I will not spend).

---

## R1 — the expected-up record is launcher-minted, never listener-minted; stand-down retracts it

**OBSERVED.** Two call sites, both in `agent_cli.py`:

- MINT — `agent_cli.py:6519-6524` (bifrost-standby, the harness parent). It resolves the
  session, and *only when `session and not args.no_listen`* calls
  `_rod.declare_expected(args.agent_id, session, by="harness", cwd=os.getcwd())` — immediately
  before stamping the arm attempt and parenting the listener. The `by="harness"` is explicit
  and constant; nothing in the listener path writes it.
- RETRACT — `agent_cli.py:10261-10266` (stand-down). It derives the session from the runner
  lock token (`token[len("session:"):] if token.startswith("session:") else token`) and calls
  `_rod.retract_expected(args.agent, ...)` inside the same `try` that performs the actual
  stand-down. A session that stood down stops being expected-up in the same breath it yields
  the seat.

The record function itself is guarded to never be written by a bare actor: `declare_expected`
(`resume_on_deaf.py:52-66`) returns `False` on an empty `agent`/`session_id`, and its registry
is keyed `agent_session.json` under `state/wake-expected/`, out of band of the armed process.
This matches the module's stated failure class — "the arm not happening," where "an actor that
never ran leaves no record."

**VERDICT: HOLDS.** Both directions observed, both call sites pinned in the test
(`test_expected_record_is_declared_by_the_launcher_and_retracted`, `tests/test_resume_on_deaf.py:18`),
and both `by="harness"` / `cwd=` carry through to the record.

**FALSE-IF.** `agent_cli.py:6522` gates the mint on `not args.no_listen` — a standby launched
with `--no-listen` (pure drain) declares nothing. That is a *defensible choice* (a drain
without a listener never holds a seat to go deaf), not a defect, but it means "expected-up" is
narrower than "the launcher was invoked": it means "the launcher is *about to hold the seat*."
Additionally, the two `try/except: pass` wrappers mean a *failure* of the mint or retract is
silent — `retract_expected` returning `False` on a genuine I/O error is indistinguishable from
"already retracted." The record dir would then keep a stale expected-up entry that `maybe_resume`
would later read as `expected=True` and act on. Not caught by the 18 pins (they only exercise
happy-path retract), but also not a reason `resume` fires spuriously, since every other hold in
R2's table must still clear before a launch.

---

## R2 — the decision table is total and every hold is named

**OBSERVED.** `resume_decision` (`resume_on_deaf.py:147-175`) is a single ordered guard chain
returning `("resume"|"hold", reason)` with a reason string for every branch. Eight holds, each
named, in this order: `not expected-up`, `tombstoned`, `reachable` (harness-armed), `no activity
marker`, `grace`, `stale`, `breaker`, `cooldown`, then `no credential`, and finally the single
`resume` ("deaf … expected-up, credential present").

I pushed on exhaustiveness by reading the signature's full parameter space. The function defaults
the five threshold knobs (`after_min`, `stale_min`, `cooldown_min`, `breaker`) via keyword
defaults so every caller-specified combination is still routed. Walking the guarded inputs:

- `expected` False → hold, regardless of every other input (first guard). ✓
- `expected` True + `tombstoned` True → hold, regardless of reachability/age. ✓
- `expected` True + `harness_armed` True → hold "reachable", regardless of age. ✓
- `alive_age_min is None` → hold "no activity marker", regardless of token/cooldown. ✓
- `alive_age_min in (0, after_min)` → "grace"; `> stale_min` → "stale". ✓ Both boundaries are
  strict-inequality so the crossing value itself still lands in a named branch (`< after` and
  `> stale`; equality on `after`/`stale` falls through to the token/cooldown/breaker check — a
  real, reachable passage, not a hole). ✓
- `failures >= breaker` → "breaker". ✓
- `last_resume_age_min is not None and < cooldown` → "cooldown" (the `is not None` guard resolves
  the "no prior resume" case to *not* cooldown). ✓
- `token_ok` False → "no credential" naming S1's two commands verbatim. ✓
- everything else → "resume". ✓

**The one combination I look for and find covered rather than missing:** `token_ok=True` with a
credential that is *present but wrong/expired* (a valid-shaped vault file that no longer works).
The table admits this as `resume`, because `token_ok` is a *presence* predicate, not a validity
proof. That is fail-*open* on credential *shape* — consistent with R3's design — and the cost
(the ~16 s dead launch + a failed receipt toward the breaker) is the explicit, dated S1 gate.
The table is total over what it claims to observe; it does not claim to observe credential
*validity*, and that boundary is named in R6.

**VERDICT: HOLDS.** Total; every hold named; no uncovered input combination found. The
parametrized pin (`test_resume_decision_names_every_hold`, 11 cases, `tests/test_resume_on_deaf.py:34`)
exercises all eight holds plus the two `resume` shapes.

**FALSE-IF.** `resume_decision`'s verdict is correct only if its *inputs* are faithful. The three
facts it trusts — `expected`, `harness_armed`, `activity_age_min` — all come from files in `tmp`
(`wake_seat` reads `.pid`, `.alive`, `.tomb`). A torn or stale `.pid`/`.alive` would feed a lie
into a total function; totality of the *table* is not totality of the *facts*. This is the known
`wake_seat` territory, not a new hole in S2, but R2's "total" claim should be read as "total over
the observable facts," exactly as the brief's language already scopes it.

---

## R3 — credential preflight fails open on unknown, refuses only on KNOWN-bad, names S1

**OBSERVED.** Two layers:

1. `cli_logged_in` (`resume_on_deaf.py:266-280`) runs `claude auth status` and returns a
   **tri-state**: `True` only if `"logged in" ∈ text` and `"not logged in" ∉ text`; `False` only
   if `"not logged in" ∈ text` or `"logged out" ∈ text`; **`None` for every other outcome** —
   including the `except Exception` block (line 279-280). The docstring says it outright:
   "every failure mode is None (unknown), never False."
2. `trigger_resume` (`resume_on_deaf.py:226-233`) receives `logged_in` (defaulting `None`) and
   refuses **only** when the vault token is empty *and* `logged_in is False` — i.e. a KNOWN-bad
   state. An unknown (`None`) login state falls through and launches (fail-open). The refusal
   text is `"no credential: vault holds no claude_oauth.token and the CLI reports logged out
   (S1)"`.
3. `resume_decision`'s own `no credential` hold (`resume_on_deaf.py:173-176`) names S1's two
   commands verbatim: `` `claude setup-token` -> `py agent_cli.py secret claude_oauth.token` ``.

The pins confirm the contract directly: `test_trigger_resume_refuses_at_t0_with_no_credential_and_launches_nothing`
asserts `logged_in=False` → refuse + `launch.calls == []` + `failures == 1`, and
`test_trigger_resume_fails_open_on_unknown_login_state` asserts `logged_in=None` → launch.
`maybe_resume` (`resume_on_deaf.py:288`) folds this as `token_ok = bool(tok.strip()) or (logged_in is True)`.

**VERDICT: HOLDS.** Fail-open on unknown, refuse-only-on-known-bad, S1 commands named at both the
decision hold and the actuator refusal. One subtlety worth naming: `logged_in is True` (not just
a non-empty vault token) is sufficient for `token_ok` — so a CLI-reported login is treated as a
credential even with no vault file. That is the gate's *own* documented "preflight shape, fail-open
on unknown"; it is not a reversal.

**FALSE-IF.** A *stale but nonzero* vault token (`tok.strip()` truthy) is treated as `token_ok=True`
without any `auth status` check, so a file that once held a now-revoked token reads "credential
present" and launches. As in R2, this is fail-open-on-shape, not a KNOWN-bad refusal — and it is
exactly the failure the ~16 s dead-launch + breaker receipt is designed to *count*, not hide.
Named, not fixed, here.

---

## R4 — a resume writes a receipt and a .rearm trigger; cooldown holds; three fails trip the breaker

**OBSERVED, three independent mechanisms:**

- **Receipt.** `record_resume` (`resume_on_deaf.py:202-215`) appends one JSONL line per attempt
  (`ts, session_id, ok, detail, log`) under `state/wake-resumes/<agent>.jsonl`. `trigger_resume`
  writes it on *every* terminal outcome — launch success (line 256), PATH miss (line 229),
  known-bad credential (line 235), launch exception (line 251) — so an attempt is never silent.
- **Cooldown.** `resume_history` (`resume_on_deaf.py:217-247`) returns
  `(minutes since last attempt, consecutive failures)`; `resume_decision` holds on
  `last_resume_age_min < cooldown_min` (default 30). The `maybe_resume` pin asserts a second call
  inside the window returns `hold`/`cooldown` and `len(calls) == 1`.
- **Breaker.** `resume_history` computes *consecutive* failures: it resets to 0 on any `ok`, and
  increments on `not ok` — but note it is **per-session** (it filters `r.get("session_id") !=
  session_id`) and does NOT demote failures older than N. `resume_decision` holds on
  `failures >= breaker` (default 3) *before* the token check, so a seat that has failed three
  times holds even with a fresh token until a human looks.

- **.rearm trigger.** This is the piece that lives *outside* the module: `resume_on_deaf.py` does
  **not** write it. The daemon does — `scripts/bifrost_daemon.py:653` calls
  `_ds.write_rearm_trigger(agent, _full_sid, tempfile.gettempdir())` *only when*
  `maybe_resume` returns `("resume", …)` (line 650-651). `write_rearm_trigger`
  (`daemon_state.py:152-158`) writes the `.rearm` sidecar that `consume_rearms` later picks up to
  re-spawn a presence listener. So the receipt is the module's; the `.rearm` is the daemon's, and
  the two are coupled at exactly the right seam (one resume verdict → one trigger), pinned only
  indirectly (the module pins never see the daemon's trigger write, because they are hermetic by
  design).

**VERDICT: HOLDS.** Receipt-per-attempt and cooldown and breaker are all module-homed and pinned.
The `.rearm` trigger is daemon-homed and correctly conditional on the `resume` verdict. I flag one
honesty point rather than a failure: **the breaker counts `launch` failures (`trigger_resume`
returns `ok=False`), not *resume-death* failures.** A resume that *launches* cleanly but then dies
~16 s later (credential present but dead) is recorded `ok=True`, so it does **not** increment the
breaker — it only lands a successful receipt with a dead child's log on it. That is a real,
named, undetected failure class until S1's live drill, and it belongs in R6's drill list.

**FALSE-IF.** `resume_history` reads the JSONL by replaying every line each call and only resets
`failures` within a *single session*'s stream — an interleaving where two attempts for *different*
sessions of one agent are written between the target session's attempts would not corrupt the
per-session count (it filters by `session_id`), but the *cooldown* is also per-session, so two
deaf sessions of one agent could each resume inside the other's window. Correct as written; worth
naming because R6's "two deaf sessions of one agent" drill will exercise exactly this.

---

## R5 — the prompt forbids arming and names the operator path; argv is `-p <prompt> --resume <sid>`, model pin first

**OBSERVED.**

- **Prompt** — `resume_prompt` (`resume_on_deaf.py:179-193`) instructs, in order: `py agent_cli.py
  boot {agent}` → drain the work lane → answer mail via
  `` `py agent_cli.py bifrost-send {agent} --to daniil --kind chat --text-file <file>` `` → land
  durably. Then the explicit prohibition: **"Do NOT arm a wake listener: this headless turn cannot
  keep one alive, the daemon holds presence between resumes."** The pin
  (`test_resume_prompt_forbids_arming_and_names_the_operator_reply_path`) asserts `"Do NOT arm a
  wake listener"`, `"--to daniil"`, and `"boot claude"` all present.
- **argv** — `resume_argv` (`resume_on_deaf.py:195-200`) is the single builder:
  `[*argv0, *(model_flag or []), "-p", prompt, "--resume", session_id, *(permission_flags or [])]`.
  Pin `test_resume_argv_is_resume_first_with_the_arm_grant` asserts `argv[:3] == [exe, "--model",
  x]` (model pin first), `-p PROMPT`, `--resume sid-123`, and the permission tail last.
- **Arm grant** — `trigger_resume` (`resume_on_deaf.py:238-247`) calls
  `_sl.claude_permission_flags("arm")`, which (`seat_launchers.py:238-261`) returns
  `--permission-mode acceptEdits --allowedTools Bash,PowerShell,Read,Write,Edit,Glob,Grep` — the
  `arm` set that lets the resumed seat drain mail, commit, run — with an unknown-mode degradation
  to `arm` rather than read-only (the documented "keep-biting" hazard). Model pin via
  `seat_model.model_flag()` (empty when unpinned → inherit). On import failure both degrade to
  sane inlines (the `except Exception` blocks), so the launch never silently narrows to read-only.

  The contract is "model flag FIRST" in the sense that model_flag precedes `-p`; it does **not**
  mean "model before argv0" — `argv0` (the CLI) is, correctly, argv[0]. The brief's "model pin
  first" is satisfied as "model pin before the prompt and resume args."

**VERDICT: HOLDS.** Both directions named and pinned; the single argv builder satisfies the
one-source-of-truth intent (the pin and the launcher cannot drift).

**FALSE-IF.** The prompt tells the resumed seat to *drain and answer* but the seat still needs the
lane env to do so correctly: the prompt's drain line is `BIFROST_CONSUME_LANE=work py agent_cli.py
bifrost-sync …` (env inline, self-seeding — good), and `trigger_resume` sets `e.setdefault("AKASHIC_AGENT_ID", agent)`
and the OAuth token, but does **not** seed `BIFROST_CONSUME_LANE`. The prompt compensates by inlining
the env on its own `bifrost-sync` line, so the resumed turn's drain is correct even though the
spawn env is not lane-primed. If a future edit removes that inline env, the resume would drain the
legacy cursor and answer from the wrong lane — the exact `wake_watcher_insta_fires_lane_divergence`
shape. Worth a pin in the live-drill day, not a hold today.

---

## R6 — what this does NOT claim, and what else I would drill the day S1 lands

**OBSERVED / what is explicitly unclaimed.** The module docstring (`resume_on_deaf.py:30-32`) states
the loop it does *not* prove: "daemon listener detects mail -> session is deaf -> resume turn answers
and lands -> daemon listener re-spawns." Presence between resumes is the daemon's own listener, which
re-spawns from the `.rearm` trigger — and the brief's acceptance labels that whole live loop
"UNDRILLED until S1," a separate dated receipt, not claimed here. I confirm nothing in the hermetic
half asserts it: the 18 pins never spawn a real listener, never touch Redis, never launch `claude`.
`maybe_resume` is the daemon's *call*, and its only live wiring is the poll in
`bifrost_daemon.py:648-662`, which I read but which no pin exercises (hermetic by design).

**What else I would drill the day the token lands (beyond the brief's own close-the-window→one-message→5-min-reply):**

1. **Window closed, box NOT rebooted** — the canonical case, but verify the *specific* property
   that closing the desktop app actually kills the harness-parented listener (so `harness_armed`
   flips false) rather than leaving a zombie listener that makes `resume` hold on "reachable"
   while the session is in fact deaf. The `/fk`-style detached-listener hazard
   (`detached_daemon_listener_holds_the_seat_but_cannot_wake_an_interactive_session`) lives here.
2. **Box rebooted** — `.alive`/`.pid`/`.tomb`/expected-up all survive or don't; verify a *cold*
   `maybe_resume` reads the expected-up record (it's in `state/`, durable across reboot) but that
   `activity_age_min` correctly reports the session's marker is *gone*, so the verdict is
   `resume` (not "stale" and not "no activity marker" blindly holding). The distinction between
   "silent past grace" and "never saw a hook" (R2's `None` branch) gets its first real test here.
3. **Two deaf sessions of one agent** — `resume_history`'s cooldown/breaker are per-session; drill
   that both resume without one cooldown falsely blocking the other, and that the `.rearm` triggers
   are *session-keyed* so presence re-spawns for both, not just the first.
4. **A resume that itself goes deaf** — the R4 falsifier, now live: a resume *launches* (`ok=True`),
   then its headless turn dies silent. Confirm the daemon's listener re-spawn from the `.rearm`
   fires anyway, and — critically — decide whether a launched-then-dead resume should also count
   toward the breaker. Today it does not (R4).
5. **The breaker trip itself** — three dead launches → `hold`/`breaker`, and the operator-facing
   surface that says "a human looks first" actually reaches a human (the daemon `_say`s the hold,
   but verify it pages, not just logs).
6. **The window-closed → reply lands on the WORK lane** — the brief asks for "a reply on the work
   lane"; drill that the resumed turn's inline `BIFROST_CONSUME_LANE=work` drain actually reaches
   the message the drill sends, i.e. the lane-divergence falsifier from R5 does not fire.

**What I would NOT build (VERDICT ON THE FRAMING):** I would not add a timer/heartbeat to the
session, and this fence does not — S4's re-scope (stop-gate + listener-exit-wake cover what a timer
would) is coherent with what this module actually ships. I would also *not* wire `maybe_resume` into
any exit other than the daemon managed-listener exit-0 path yet: every other exit code/actor is
either the covered deadline-cycle (already rearmed by R18) or a kill (no trigger by construction,
the `rearm_orphaned_sessions` startup path's job). The one seam I *would* surface before S1 is the
R4 falsifier — "launched but died" — because it is the only failure class in the whole chain that is
*recorded as success* and therefore invisible to both the breaker and the cooldown.

---

## VERDICT ON THE FRAMING

The question as posed — "does the daemon now re-open an expected-up session that is deaf, silent
past grace, no listener able to start a turn, by a headless `--resume` under the vaulted token, with
every hold named, a receipt per attempt, and a `.rearm` trigger" — is answered **yes on the hermetic
half, with full holds**. R1-R5 each HOLD, with a named FALSE-IF that is a future-drill item, not a
present defect. The framing is honest in the one place it matters most: it separates the *decision+actuator*
(module, pinned, total) from the *loop* (daemon + live seat + credential), and refuses to claim the
loop until S1's dated live receipt exists. That is the correct altitude, and it is what lets a blind
half certify the machinery without ever spending the ~16 s dead-launch cost.

The single strongest thing I would push back on, gift-shaped: **"three failed launches trip the
breaker" is narrower than it sounds.** It counts *launch* failures, not *resume* deaths. A credential
that is present-but-dead produces a clean launch, a `ok=True` receipt, no breaker increment — and a
still-deaf seat the house believes it just resumed. That class is undetectable from inside the
hermetic pins by construction, and it is the one thing the S1 live drill should be built to catch,
not merely to exercise.

— filed blind, Heimdall (deepseek), 2026-10-01
