# U1 BRIEF — codex — does the seat-stream path actually execute?

Status: current (2026-08-02, claude#30e6af5c). Convener brief. Netcode arc, board rev 5.

## INTENT FIRST

The whole netcode build sits on U1. It is opus-engineer's least confident verdict and the
item every other slice depends on. **It has never once executed in this Redis lifetime** —
0 `bifrost:cursor:seat:*`, 0 `bifrost:seat_seen:*`. Every claim about it is code review,
not observation. No further reading settles it. Somebody has to RUN it.

You volunteered for exactly this, and you have exec. You run it. That is the whole lens.

DANIIL, verbatim, 2026-08-02: *"I like your plan lets execute, lets keep it tight and work
with just deepseek, I'm trying to conserve tokens with the other models, I have codex on a
plan so we can spin him up too"*

B2 is ruled: you and deepseek are the fleet for this arc.

## SCOPE — ONE LENS

**RUN IT. Do not audit it.** Do not re-verify the 37-mechanism audit, do not re-read the
vision doc, do not grade anyone's design. Produce OBSERVATIONS with receipts.

## WHAT WE ALREADY KNOW — do not rediscover this, it cost us a round

deepseek settled U2 tonight. Take these as given:

1. `core/comm/bus.py:267-270` — `_my_sid8()` is a `@staticmethod` reading **only**
   `os.environ` (`BIFROST_INCARNATION`, then `CLAUDE_CODE_SESSION_ID`). It never consults
   `self._incarnation`. **This is WHY U1 never executed:** nothing in production sets
   `BIFROST_INCARNATION`, and only the Claude Code harness exports `CLAUDE_CODE_SESSION_ID`.
2. `scripts/bifrost_runner_deepseek.py:1127` — a `--session` flag IS already wired and
   feeds `incarnation=` at line 1134. The door exists. Nobody passes it.
3. `Bus(incarnation=…)` sets `self._incarnation`, consumed by exactly ONE path:
   `lane_cursor_key()` at `bus.py:1182-1183`. It does NOT open the seat stream.
4. U3 is live and coupled: `mailbox.py:330` reads the **unsuffixed** lane cursor while
   `bus.py:1182-1183` writes the **suffixed** one.

## THE QUESTION THAT MATTERS MOST

`core/comm/bus.py:806` gates the seat-stream read:

```python
if sid8 and since is None and streams is None:
```

Two conditions beyond sid8. **Lane consumption passes `streams`.** If that is right, the
seat-stream read is DISABLED under the exact configuration we run in production
(`BIFROST_CONSUME_LANE=work`) — which would make T108's per-incarnation delivery
unreachable in our real config, and would reorder the entire build.

kimi flagged this shape independently as the ORDERING TRAP. **Settling it is the single
highest-value thing you can produce.** If you only answer one thing, answer this.

## THE RUNS

Namespaced drill only — **never against the live bus.** Use a `test-*` namespace
(precedent: 7097b5e namespace isolation; drills are always namespaced).

1. **Baseline** — confirm the seat keys are absent before you touch anything.
2. **Arm an incarnation on a NON-claude seat** — set `BIFROST_INCARNATION` explicitly.
   Does `_my_sid8()` now return non-empty for that process?
3. **Directed send** — send with `to_incarnation`. Does it land on
   `{ns}:inbox:{agent}#{sid8}`? Does `{ns}:cursor:seat:{agent}#{sid8}` get created?
4. **THE ORDERING TRAP** — repeat step 3 under `BIFROST_CONSUME_LANE=work`. Does the seat
   read still happen, or does the `streams is None` condition disable it? This is the one.
5. **Theft test** — two incarnations of one agent live. Can B consume a message directed
   at A? T108 claims this is structurally impossible. Prove or break it.

## OUTPUT SHAPE

- Every claim carries a RECEIPT: the actual key name and value you observed, or the command
  and its output. "The code says" is not an observation.
- State what you did NOT run and why. A bounded run that declares its bounds beats a
  complete-sounding one that hides them.
- UNKNOWN is a legal verdict. Guessing is not.
- If a run contradicts anything in "what we already know" above, **say so** — that section
  is deepseek's work verified by me, and either of us can be wrong.

**File durably at:** `research/in-flight/netcode-u1-seat-stream-live-codex-2026-08-02.md`
**Reply to claude with `kind=reply`** — a `kind=chat` answer does NOT settle the
expectation and will trigger three redrives and a false DEAD while you have already answered.

## ONE MORE THING

`bifrost-send` bodies must go through `--text-file`. A long `--text` body misparses as a
filename and the send SILENTLY DOES NOT HAPPEN.

Red is a gem. If this brief is wrong about the gate, that finding is worth more than a
clean confirmation.
