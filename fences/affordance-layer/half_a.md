# affordance-layer — half_a (Heimdall / deepseek) — THE ARCHITECTURE

**Blind-state:** I did not read `half_b` (Navi) or any sibling half before sealing this one. I
read `brief.md` in full, then the cited sources. Read-only on the repo; no commits, no edits, no
bus sends.

**Method note (read this before the verdicts):** the brief already *tells* me the answer it
wants attacked, so a pass-first pass would be compliance. I went looking for the places where the
brief's own examples are falsified by the code it cites, and found three. Those are where my
verdicts come from; everything else is subtracted.

---

V1. [INFERRED] — The "one builder per action" registry does not remove duplication: it relocates it, and the brief's own crown-jewel example is already duplicated today. Resolving citations: `core/comm/wake_seat.py:143-186` (`arm_command`) vs
`scripts/hooks/claude_stop.py:456-463` vs `agent/harness/hooks/claude_stop.py:456-463`.

The brief holds up `arm_command()` as the proof that "one builder" works: "a function that cannot
emit a non-pasteable form." It is real and it is good. But read the *consumer*: the stop hook
carries a hand-built **fallback** twin of `arm_command`:

```python
try:
    from core.comm import wake_seat as _ws2
    arm_cmd = _ws2.arm_command(AGENT, session_id or None)
except Exception:
    _cli = os.path.join(...)
    arm_cmd = f"py {_cli} bifrost-standby {AGENT}" + (f" --session {session_id}" if session_id else "")
```

`claude_stop.py:457-463` (and the identical twin in `agent/harness/hooks/claude_stop.py`). So "one
builder" is *already* two builders for one action, in the file the brief calls clean. The fallback
is not optional sloppiness — it is *correctly* reasoned: a fallback that imports the thing it is
falling back from is not a fallback (`tests/test_every_draining_door_names_its_lane.py:135-167`
says exactly this, and pins that the fallback must AGREE with the canonical string).

That is the answer to the brief's question "what breaks when two surfaces want the same action
with different context." It already broke, and the remedy is not a registry — it is a **pin that
asserts agreement** (see the same test file's `test_the_stop_hook_and_boot_do_not_disagree`). The
house learned this on 2026-10-02 with the exact same action (arm), and its own test suite encodes
the lesson as "the fallback must agree with the canonical," NOT "there must be only one builder."

A registry generalising this to *every* action would do the opposite of what `arm_command` did:
`arm_command` works because it is **one string, one job, one seam** — the arm is offered at boot
and at a stop gate and both must be *identical* because the seam (a watcher that is consumed on
fire) is a single atomic state transition. Most notifications do not have that property. The re-arm
offered at a **stop gate** needs `--session <pid>`; the re-arm offered in a **Discord cold-seat
notice** needs no session (the seat is dead — `discord_inbound.py:453` correctly hands Daniel
`!spawn vandor --harness | --headless`, a *different verb entirely*, not a re-arm). The same
"action" (get a listener live) has three *different affordances at three different seams*, and a
per-action builder registry — keyed on "arm" — cannot express that without acquiring exactly the
context-sensitivity that a plain function already has via its parameters.

**So:** the registry is not wrong-shaped, it is *unnecessary indirection*. The thing that actually
prevents the 2026-10-02 class of failure is (a) one canonical function for the genuinely-single
seam, and (b) a pin that two surfaces agree. Both already exist for the arm. Generalising (a) to a
registry buys nothing that (b) does not already buy, and costs a new abstraction nobody is asking
the notifications to share.

---

V2. [CERTAIN] — A paste-test checker cannot decide "runnable," and its two failure modes are not a corner of the problem, they are the problem. Resolving citations: `core/recall/at_action.py:2084-2086`, `tests/test_t048_recall_surfaces.py:46-58`,
`agent_cli.py:8745`, `core/comm/toolbox.py:63`.

The brief's two paste-test failures are instructive because they are *opposite* errors rooted in
the same fact the brief's model misses:

1. **False-negative by launcher, not by content.** `recall-at --limit 21` fails only because it
   lacks `py agent_cli.py`. But `recall-at` *is* a real subcommand (`agent_cli.py:8745`), so
   `py agent_cli.py recall-at --limit 21` runs fine. A checker that "asserts each starts with a
   real launcher" would pass this string — **it is a pasteable command, just not for the reader
   the surface is talking to.**

2. **The reader isn't fixed.** `core/recall/at_action.py:2079-2086` renders TWO different hints
   for the SAME surface, keyed on `hint_style`: the "tool" style emits
   `call recall_at(limit={total})` (an MCP-*tool* invocation, not a shell command), and the
   "cli" style emits `recall-at --limit {total}`. `tests/test_t048_recall_surfaces.py:46` pins
   that the tool style "must not render CLI verbs" because "a tool-loop agent cannot run CLI
   verbs." So a paste-test that demands a shell launcher would flag the tool-style hint as a
   false positive *while it is the only correct rendering for that reader*.

This is the decisive architectural insight, and it refutes the brief's checker premise directly:
**"runnable" is not a property of the string — it is a property of the string *and the reader's
execution surface*.** This house has three execution surfaces (CLI seed under `py`, MCP tool loop,
Discord operator typing into a chat). A string that is runnable on one is a dead letter on the
other two. The paste-test as specified ("extract command-shaped strings, assert launcher, assert
no placeholder, assert resolves") can only ever be correct for one of the three, and it will
*actively mis-flag* the other two as defective.

The `wish` case is the same disease, third reader: `core/learning/learning_store.py:239` emits
`py agent_cli.py wish %s --text-file %s` — pasteable for a CLI seat *if* `%s` (draft_path) names a
real file. The brief's Rill test #3 shows the *literal* `<path>` placeholder leaking to the reader,
which is the "emitter holds the value, prints the placeholder" genus — but that is a *different*
failure (the value never got substituted at the point where the affordance crossed the interface),
and a launcher-checker cannot see it at all because `<path>` is not `<sha>`-shaped.

**So:** the checker is fixable only by becoming a *reader-aware* checker, i.e. it must know whether
the emitting surface targets a CLI seat, a tool-loop seat, or Daniel-in-Discord before it can
classify "runnable." At that point it is not a paste-test; it is a routing test, and the correct
shape is to *render the affordance per-reader at emit time* (which `hint_style` already does for
recall-at), not to lint the rendered string after the fact.

---

V3. [DESIGN] — FACT / PAYLOAD / AFFORDANCE is a useful *descriptive* taxonomy but a wrong
*prescriptive* carve, because it omits the fourth thing every one of the brief's own worked
examples depends on. Resolving citations: `agent/harness/context.py:187-233` (the four-state
`_reach_line`), `claude_stop.py:471-484` (the four-state backstop), `core/comm/wake_seat.py:143-186`.

The brief's three layers are ordered by what they buy the *reader*: FACT forces a round trip,
PAYLOAD lets the reader compose, AFFORDANCE lets the reader act. Clean. But the brief's own two
"surfaces that get it right" get it right by a property that is **not on that axis at all**: they
discriminate **four states** rather than a boolean, so "I could not tell" never renders as "you
are fine" (`context.py:203-233`, `claude_stop.py:471`). The brief quotes this and then files it
under "why they earn it identically" — but it is a *separate* axis.

That axis is **EPISTEMIC STATE** — is the affordance being offered *safe to act on right now*, or
is its precondition unverified? `_reach_line` has `armed` / `unarmed` / `dead-seat` / `unknown`
before it ever gets to the command. The arm command is *only* offered in the states where arming
is the correct next act; in `unknown` it says "assume the operator cannot reach you until you
check." A FACT/PAYLOAD/AFFORDANCE notch does not capture this, and if you build an affordance
registry that keys on "arm" without keying on *the precondition state*, you get exactly the
2026-10-02 bug back: an affordance that is syntactically pasteable but semantically wrong for the
state the reader is actually in.

The three layers answer "how much does the reader have to do." The missing fourth answers "is the
action this affordance names the *right* action given what the emitter actually knows." The
brief's own most expensive round trips — the mistyped arm command five times, the mangled session
id that armed two listeners — were not FACT-only failures. They were failures of *acting on an
affordance whose precondition the emitter had not distinguished*. The notch that matters is not
"did I give him the command" but "did I give him the command *and tell him which of four
preconditions he is in*."

**So:** keep FACT/PAYLOAD/AFFORDANCE as a *description* of what a notice currently carries (it
measures the 56%-present / 30%-working split honestly). Do not build the registry to it. Build to
the *state-discrimination* property, which is the actual thing `arm_command` plus its two
consumers share and which the three-layer model cannot see.

---

V4. [INFERRED] — The cheapest change that removes the most round trips is not a registry and not
a checker. It is: stop emitting placeholders for values the emitter already holds, at the 11 gate
sites — and if the scheduled-task finding is true, fix THAT first, because it destroys the FACT
layer at launch and outranks every ergonomics refinement in the brief. Resolving citations: `core/comm/doctor.py:473` (live `--by <you>` placeholder
inside a pasteable verb), `agent/harness/context.py:262` (live `--state <sha> | --open <sha>`),
`core/learning/learning_store.py:239` (`%s` resolved-at-call, `<path>` leaks to Rill's reader);
UNCONFIRMED scheduled-task finding (brief §2 MARKED UNVERIFIED — I did not re-derive it).

The brief's census says the defect is "the emitter holds the real value in a local variable and
prints a placeholder" in **eleven gate-plane places**. I found three of that genus live with zero
search effort:

- `doctor.py:473` — `py agent_cli.py bifrost-skip-to-now {agent} --by <you> --reason ...`. The
  emitter *has* the operator's agent id or knows how to get it; it prints `<you>`.
- `context.py:262` — `py agent_cli.py mailbox {agent_id} --state <sha> | --open <sha>`. The
  emitter is iterating mailbox entries and *holds the sha per entry*; it prints `<sha>`.
- `learning_store.py:239` — `wish %s --text-file %s` is resolved at the call site (good), but the
  `draft_path` crosses into the notice as `<path>` for the interface that saw it (Rill test #3).

Each of those is a round trip the reader must spend to *ask for a value the writer already had*.
That is the cheapest axis: it needs **no new abstraction, no checker, no ratchet**, just "when you
f-string a command, put the real value in the f-string, not `<thing>`." It is a one-line fix per
site, it is exactly the 2026-10-02 lesson generalised (the instruction was wrong, not the
discipline), and it removes the round trips the brief's FACT layer is *actually* costing — not the
ones its AFFORDANCE layer is (which, per V2, can only be fixed per-reader anyway).

And the scheduled-task finding, if true, is strictly higher priority than all of it: 7 of 13
AkashicAurora scheduled tasks launching `pythonw.exe` with `sys.stdout is None` would mean the
weekly secret scan, the memory black box, the daemon watchdog and both transcript-archive jobs
print into a void — the FACT layer destroyed at launch, before FACT/PAYLOAD/AFFORDANCE even exists.
The brief says it tried to verify and failed, and so do I here (no scheduled-task introspection in
a read-only pass). If I were ordering the work I would put that probe *first*, because a
notification system whose own background jobs cannot emit is a carriage with no horses.

**So, the cheapest-highest-return change, in order:** (1) verify the pythonw/stdout finding — one
probe, and if true it is the headline; (2) the eleven placeholder-for-held-value sites, one-line
each; (3) *then* the per-reader affordance rendering that `hint_style` already prototypes, and
only then a light agreement-pin like the arm-command one — not a registry, not a paste-test.

---

## BOUNDS — what I did NOT check

- **Every census number in the brief is unverified by me.** I did not re-derive 187/105/67/15,
  97/29/42/26, 35-lines/7045-chars, or "eleven places." I confirmed *three* placeholder sites
  exist by direct read (`doctor.py:473`, `context.py:262`, the `wish` path). The rest I take as
  claude's single-agent count, flagged as such in the brief's own MARKED UNVERIFIED.
- **The scheduled-task / `pythonw` / `sys.stdout is None` finding.** Not probed. It is the highest
  stakes claim in the brief and I could neither confirm nor refute it read-only. Treat it as open.
- **I did not run any command** (no `py agent_cli.py ...`, no paste-tests). All my "runnable"
  judgments are from reading `add_parser` registrations and the emitting code, not execution.
- **I did not verify the recall-volume numbers** (595 injections / 952,570 chars, 489-in-168h,
  ~476 kchars-per-credited-lesson). Those are Navi's lane (half_b) and I left them alone.
- **The dirty tree.** `git_status` shows `master ahead 114` with a large uncommitted working set.
  The census may describe a tree that differs from what I read. I read the current working files;
  I did not diff them against any commit the census might have been run over.
- **I did not audit the other eight gate-plane placeholder sites** beyond the three I cite. If the
  brief's "eleven" is right, my claim "one-line each" extends to eight I have not looked at.

---

*This half is sealed by design, not exhaustion: the four verdicts each stand on a citation I read
directly, and the bounds name the gap between those citations and the brief's full numerical
claim.*
