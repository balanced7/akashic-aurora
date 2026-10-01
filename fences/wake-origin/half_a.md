# wake-origin — half_a (Heimdall/deepseek, blind drill)

Blind drill D1–D6. **Order disclosure (honest):** I read `fences/wake-origin/brief.md`
and `tests/test_stop_wake_origin.py` BEFORE running; both are declared INPUTS
(the brief names the test as the source of the `_run_hook` subprocess form). I did
NOT read the diff (`claude_stop.py`, `wake_seat.py`, `bifrost_wake.py`,
`bifrost_daemon.py`) before running D1–D3. I read `wake_seat.py` source only AFTER
D1–D3 were recorded. I ran everything against a **throwaway agent id `torigin2`**
for D1–D3 and invoked the REAL hook subprocess (`agent/harness/hooks/claude_stop.py`)
with the test's exact env form; Vandor's harness listener (`--agent claude --session
bb86400e`, pid 51680) was never touched.

All shell output was written to `state/_drill_wake_origin*.txt` and read back, because
this runner's `python -c` stdout is swallowed by the MCP shell wrapper (my own prior
lesson). Scratch script: `state/_drill_wake_origin.py`.

---

## D1 — daemon-only seat blocks

OBSERVED (real subprocess, throwaway agent `torigin2`, seat origin `daemon`):

```
origin: ('daemon', 44636)
STDOUT: '{"decision": "block", "reason": "Your wake watcher is the DAEMON\'s child
(presence and consume only -- a detached process can start no turn) -- this session is
not wakeable from idle (DeepSeek/Daniel can\'t reach you). Re-launch it ONCE:
`BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py E:/AI-Setup/agent_cli.py
bifrost-standby torigin2 --session wake3285397e42` as a Bash run_in_background task
(harness-tracked; its completion re-invokes you). It stays armed for HOURS -- this
backstop should be rare. Then stop."}'
```

VERDICT: **HOLDS.** `"decision": "block"` present; reason contains "presence" and a
`bifrost-standby` line; the arm line names the absolute `agent_cli.py` path
(`E:/AI-Setup/agent_cli.py`), NOT `scripts/bifrost_wake.py`.
FALSE-IF (pass / names scripts/bifrost_wake.py): neither occurred.

## D2 — harness seat passes

OBSERVED (same form, origin `harness`):

```
origin: ('harness', 6024)
STDOUT: ''   (empty — no block JSON)
STDERR: '[stop-hook] draft keepalive: wrote=False (disabled (AKASHIC_DRAFT_KEEPALIVE=0))\n'
```

VERDICT: **HOLDS.** No `"decision": "block"`; no A1 line at all. The harness-origin
seat passes cleanly.
FALSE-IF (a block, or an A1 daemon claim without the BUT clause): neither occurred.

## D3 — no sidecar blocks

OBSERVED (seat pid alive, no `.origin` written):

```
origin: ('none', None)
STDOUT: '{"decision": "block", "reason": "Your wake watcher holds the seat with no
origin record (not wakeable by evidence) -- this session is not wakeable from idle
(DeepSeek/Daniel can\'t reach you). Re-launch it ONCE:
`.../agent_cli.py bifrost-standby torigin2 --session wakef87145aee1` ..."}'
```

VERDICT: **HOLDS.** Block, reason begins "no origin record". A bare seat (no sidecar)
is reported as `('none', None)` and BLOCKED — never silently passed.
FALSE-IF (pass): did not occur.

## D4 — the running daemon stamps

OBSERVED (`%TEMP%` = `C:\Users\L5\AppData\Local\Temp`):

- `.origin` files present: `bifrost_wake_claude_pin-ephemeral-0000.origin -> daemon:34808`
  (the daemon's listener, pid 34808, parent = daemon pid 53996), plus my two throwaway
  torigin2 stamps. **The daemon-spawned listener IS stamped `daemon:<pid>`.** ✓
- pid 34808 command line: `pythonw.exe ... scripts/bifrost_wake.py --agent claude
  --session pin-ephemeral-0000`, parent pid **53996** = `bifrost_daemon.py --agent claude
  --manage-listener` (created 12:08:31 local). Daemon restart → child stamps `daemon`. ✓

VERDICT: **HOLDS with one loud caveat.** Every *daemon-spawned* listener observed is
stamped `daemon`. BUT the **live harness listener does not carry a sidecar at all** —
see D6 (a) and D5. The brief's D4 false-if ("any listener seated with no sidecar after
the restart") is TRUE for the daemon's own child but FALSE for the pre-existing harness
listener, which the restart could not retro-stamp.

## D5 — end to end (the receipt Daniel asked for)

OBSERVED: I sent one directed `request` to `claude` from my seat at bus id
`1790871094272-0` (~12:11 local), while claude's session `bb86400e` was idle
(last `.alive` touch 11:59:08). At the time of filing (12:12 local) the reply was
pending; his `.alive` had not yet freshened.

VERDICT: **UNCHECKABLE-within-window at filing time** — the round-trip timestamp on
claude's side cannot be recorded until he wakes and answers. The prediction is
falsifiable on his side: the reply arrives on the work lane with
`expectation_settled_answered`, and his next stop-hook stderr shows either the A1 pass
(origin harness) or block-then-rerearm. I flag a concrete reason to expect a
**block-then-rerearm** rather than a clean A1 pass: his currently-seated listener (51680)
was launched at **12:02:55**, BEFORE the origin-writing code landed in
`scripts/bifrost_wake.py` (file mtime **12:10:58**) — so it is running the OLD
`bifrost_wake.py`, which writes no sidecar. The stop hook will read "no origin record"
and prescribe a one-time re-arm. That is *correct*, not a defect, but it means the very
first stop after this fix on his live session is a block, then a fix-up.
(Will append the reply timestamp if it arrives before seal.)

## D6 — what the brief does not claim (additions)

(a) **A pre-fix harness listener holds the un-stamped wakeable seat.** The live wakeable
    listener (pid 51680, `bifrost_wake.py --agent claude --session bb86400e`, launcher =
    `bifrost-standby` → harness-parented) was started 12:02:55, before
    `scripts/bifrost_wake.py` gained origin-writing (mtime 12:10:58). It has seat
    `.pid` + `.alive` + `.arming` + `.seen` but **no `.origin`**. It is genuinely
    wakeable (harness-parented) yet reads as `armed-unknown` → the hook blocks and
    prescribes a re-arm for a listener that was already correct. **Cost: one spurious
    re-arm per pre-existing session, every time until it re-arms once through the new
    path.** The fix's stamping only binds to listeners launched *after* the code landed;
    nothing retro-stamps a live one. This is the "first stop is a block" shape D5
    predicts.

(b) **The daemon's OWN child (34808) is stamped `daemon`, but the daemon has no child
    for the real session id `bb86400e` — it pinned a synthetic `pin-ephemeral-0000`.**
    So the daemon listener and the harness listener occupy *different* seat files; the
    collision the fix addresses (daemon child holding the SAME seat file as the interactive
    session) is visible in the code path but was NOT observed live on this host — the two
    listeners are on distinct sessions. The D1/D3 block semantics are proven by synthetic
    seats, not by a live observed daemon/harness seat collision.

(c) **`direct` origin is wakeable but unstamped-by-launcher.** `bifrost_wake.py:702`
    defaults origin to `direct` when `BIFROST_WAKE_ORIGIN` is unset, and `direct ∈
    WAKEABLE_ORIGINS`. Any `bifrost_wake.py` launched by hand (not via `bifrost-standby`
    and not via the daemon) writes `direct:<pid>` and the hook PASSES it — yet a
    manually-launched `bifrost_wake.py` is a detached child with no harness parent, whose
    exit notifies nobody. That is exactly the deaf-session shape the fix exists to kill,
    re-admitted through the `direct` default. (The arm line the hook prints uses
    `bifrost-standby`, so the *prescription* is right; but a seat stamped `direct` still
    passes.) **This is the one thing I would not build as-is** — see the framing.

(d) **Signature of the two legacy seat-file twins persists.** The `.seen` files list an
    absurd count of old session ids (10+ `bifrost_wake_claude_<uuid>.seen` from 09-15
    through 09-28). Those are reading-side history; they do not block, but they show the
    janitor is not reaping old per-session records, so `iter_seats` and the boot render
    still enumerate many stale seats. Not a wake defect, a housekeeping debt the origin
    sidecar does not touch.

(e) **Twin hook parity is live-only.** `test_stop_hook_twins_in_parity_modulo_syspath_depth`
    pins `agent/harness/hooks/claude_stop.py` ≡ `scripts/hooks/claude_stop.py` modulo the
    sys.path chain, but the `.claude/worktrees/*` copies (`interesting-mahavira-3eb7ee`,
    `screenspace-step0`) carry their own divergent `claude_stop.py` / `wake_seat.py` /
    `bifrost_wake.py`. A session launched from a stale worktree runs a hook without the
    origin gate and silently passes a daemon seat. The parity pin covers only the two
    canonical twins, not the worktrees.

---

## VERDICT ON THE FRAMING

The mechanism's core claim **HOLDS**: a detached (daemon) listener cannot start a turn,
and only a harness-parented listener can; D1/D3 block and D2 passes as claimed, and the
reason strings + absolute arm line are exactly as the brief predicts. The commit shape
(RED pins first — I observed claude's trace committing `tests/test_stop_wake_origin.py`
by pathspec alone) is honored.

**What I would not build as-is:** the `direct` fallback default in
`bifrost_wake.py:702`. Defaulting an unstamped listener to a WAKEABLE origin re-opens the
exact hole (a hand-launched detached `bifrost_wake.py` passes) through a silent default.
Recommend: default unstamped to `unknown` (block) and reserve `direct` for an explicit,
named `--origin direct` arm where the operator deliberately asserts the harness parent.
The ergonomic goal ("just works") is met by the harness path; `direct`-by-default buys
nothing and costs deafness.

**Smallest follow-up rungs (not this fence):** (1) retro-stamp or re-arm-once semantics
for the pre-fix live listener so the first stop isn't a spurious block; (2) worktree hook
parity in the janitor; (3) stale per-session `.seen`/`.pid` reaping, which the origin
sidecar does not address.
