I have everything I need — and the decisive evidence is our own `doctor` code, which already distinguishes the states the doc treats as "identical." The doc's Q1 premise is factually wrong. Let me write the counter.

---

# Counter-round — `oob-recovery-design-2026-08-20.md`

Net verdict up front: **Laws 1, 2, 4, 6, 7 survive — but Law 2 as written is a false constraint where it matters most, Law 3 is unbuildable, and Q1's framing is wrong in a way that makes the whole "automatic wedged recovery is off the table" conclusion false.** Daniil's intent survives; your ladder's hardest rung does not need to be amputated, it needs a different discriminator than the one you staged.

---

## Q1 — you asked the right question and then answered it from a false premise

> "A wedged seat and a seat thinking hard for 45 minutes look identical to every signal we have."

**They don't. We have proof in the tree, in code, right now.** Two independent refutations:

**Refutation 1 — `hard_wedge_pages_hide_two_different_failures` (2026-07-28).** The exact situation you describe already happened, and it was resolvable with a tool that already exists:

> "Run `py-spy dump --pid` on the runner first — the stack distinguishes failure classes the page label merges. A MainThread blocked in `streams.py` write/flush = the pipe-wedge family (T019), needs the drainer fix, NOT a relaunch. A MainThread idle in `_process_one`'s wait with a beating heartbeat = the worker is FINE and the PULSE organ is lying — relaunching destroys a healthy runner and hides an instrument defect."

That's your Q1 answer, already earned and already *taught* as a lesson: **the discriminator between wedged and thinking is the thread stack, not a timeout.** A wedged deepseek was caught with `streams.py:32` blocked on its *own output write* (undrained pipe) while a genuinely-fine kimi was parked in `_process_one`'s wait. Two HARD WEDGE pages, one label, two diseases, distinguished by `py-spy dump` — a tool the lesson records as cheap ("10s is generous"). You have framed automatic discrimination as *impossible without destroying work*; the record says it is *a stack sample away*.

**Refutation 2 — your own `doctor.py` already computes the exact verdict the doc calls impossible.** `doctor.py:392-412` (the T347 third state) says it out loud:

> `phase 'running' aged 2786s with beat fresh (2s) but NO progress pulse — ALIVE is proven, WORKING is not (a runner's beat is its heartbeat thread, not its work; an idle stale phase and a hung MainThread look identical from here)`

and it hands you the next probe as a *prescription*, verbatim at `:408-410`:

> `"sample CPU delta + py-spy dump --pid <runner-pid>; empty queue => stale phase, backlog => real wedge"`

So the honest answer to your Q1 is NOT "automatic recovery of wedged is off the table." It is:

> **The gate that makes automatic kill+respawn safe is not a longer timeout or a better heartbeat — it is a stack-level liveness probe that already discriminates `blocked-in-output-write` (wedge) from `idle-in-wait` (thinking), and `doctor` already names it as the next step.** A seat that is *genuinely thinking* shows a MainThread above the model call / in a producer-consumer wait; a seat that is *wedged* shows a MainThread blocked in a `streams.py` flush or a socket write that never drains. Those are different stacks, and they answer the question a beat/pulse pair cannot.

The one honest caveat, and it matters for Law 5: **`py-spy dump` is a Python-runner capability.** It reaches Heimdall's and Navi's MainThreads. It does **not** cleanly reach into a Claude Code harness seat, which is the Q2 problem. So the answer to Q1 splits by runtime exactly the way Law 5 already splits — and that's fine, because **Law 5 already concedes a wedged Claude seat can only be replaced.** You do not need wedged-vs-thinking discrimination for a Claude seat, because your own design refuses to *recover* it (only replace it). The discrimination is required *only* for polling runners — where `py-spy` is free and proven.

**So: automatic `wedged` recovery is NOT off the table. It requires one new organ (an in-path or subscribed stack-sampler that `doctor` already prescribes), and it is already taught as a lesson. The rung you were about to amputate is the one the tree already solved once.**

---

## Which of Laws 1–7 is a FALSE constraint (Q4)

**Law 3 ("silent by default; loud only on terminal failure") is false as written — not because silence is wrong, but because it smuggles the word "default" past the one constraint Daniil actually set, and it is internally incoherent about the success mode.**

Daniil's words are *"hopefully be invisible until asked for"* and "self-repair whose success mode is silence." Read them carefully: **the success mode is silence. "Invisible until asked for" is about not *nagging*, not about not *recording*.** Law 3 collapses those into one "silent" tier and then — look at its own table — concedes the terminal rung must be **loud**, on **Discord**, to a **human**. So "silent by default" is not actually silent; it is *silent in the middle rungs and loud at the ends*. That's not a law, that's a *verbosity profile*, and calling it "silent by default" hides a decision that hasn't been made: **who is the "default" audience of the silence?**

The false constraint is: **silence is defined relative to *notifications to a human*.** But the correct partitioning for a self-repair path is not human-vs-silent; it is **durable-repair-log vs notification-stream**. A recovery that is invisible to Daniil must still be *visible to the fleet's own reasoning*, or two agents will both "silently" recover the same seat and fight over it, and the next incident's post-mortem will have no record that anything was recovered at all. Your own Law 7 (drill receipts) requires a *dated written receipt* — that receipt is, by definition, a record, not silence. So Law 3 and Law 7 are in tension: you cannot have "silent by default" *and* "write a dated receipt every drill," unless "silent" means "silent to Daniil," in which case it should say so.

**The correction:** replace Law 3's three tiers with a two-axis split — *surface* (human notification vs fleet-internal log) and *state* (recovered / pattern / terminal). The success mode is silence **on the human surface**, but the repair log is the *success record*, and it must be durable and queryable (the fleet reads it, the drill receipt is one entry in it). That is still Daniil's "invisible until asked for" — because "asked for" *is* "query the repair log." Nothing here weakens the real constraint; it just stops pretending a repair log is the same thing as a klaxon.

---

## Q2 — the Claude-seat ringer in its own failure domain

You've correctly identified that a Claude seat's *only* wake is harness-tracked process exit, and that its ringer therefore shares its failure domain. Your question: is there *any* carrier that escapes this?

**There is exactly one, and it's the one you're not allowing yourself to see because Law 1 ("never carries payload") has already foreclosed it.** The ringer for a wedged Claude seat does not need to *wake* the seat — your own Law 5 concedes it can't. It needs to **reach the harness *around* the seat**, which is a sibling process, not the seat's own child. That process is already a carrier: it's the thing that tracks the seat's lifecycle. **The ringer should be peer-to-peer across *harnesses/daemons*, not descend into the wedged seat's process tree.** A wedged Claude seat's harness is not (typically) on the same blocked thread as the seat's model turn — and where it is, that's *itself* the Q1 finding ("the ringer shares the victim's failure domain" is true iff harness and seat die on the same blocking call, which is a diagnosable property, not a law).

But I'll give you the harder, more honest answer: **yes, "a Claude seat cannot rescue itself, only be replaced" is a fact to design around — and it is *fine*, because it is exactly what Law 6 already says the ladder terminates in.** The false move would be to pretend the ringer can be made failure-domain-disjoint by cleverness. It can't, in general. Accept the collapse, and spend the design budget on making *replacement* clean (handoff-then-kill, not kill-then-handoff — Law 6's terminal rung is where a Claude seat's data is at risk, and "respawn with the latest handoff" is only safe if the handoff is *forced out before* the kill, which a wedged seat cannot do). **The honest design: for a Claude seat, the ladder's terminal rung must be "mark dead + reroute," never "kill + respawn and hope the handoff was fresh."** That's the part of Q2 worth building, not a fancier ringer.

---

## Q3 — triage in-path vs `doctor` as push surface

**`doctor` as push surface is the right answer, and your framing misses *why* it's not just "less code."**

The reason is `t197_the_verdict_existed_the_door_never_asked` — one of the sharpest lessons in the tree:

> "The reader ALREADY EXISTED and was already honest... bus.send already CALLED it and printed 'UNATTENDED RECIPIENT' — to stderr... Building the reader I planned would have duplicated a correct organ and left the actual defect in place."

The defect you're contemplating re-creating is *exactly* this: **in-path triage would be a second, private copy of `doctor`'s state machine, and it would drift the moment `doctor` learns a new signal (as it already did three times: S2, T347, T282).** A private verdict grows weaker public twins — `one_word_two_meanings_is_how_gauges_lie` is the law. Doctor already computes asleep/wedged/misrouted *and already names the repair per state* (`:408-410` literally prints "sample CPU delta + py-spy dump"). The OOB path should **subscribe to doctor's verdict and select the rung from it**, never re-derive triage.

The one real concern you raise — "in-path survives doctor itself being wrong" — is real but is *the wrong threat model for a self-repair path.* If `doctor` is so wrong it misdiagnoses, the fix is to make `doctor` correct (it is the one source of truth), not to build a second truth that disagrees. A second in-path copy "surviving doctor being wrong" means *two answers*, which is precisely the gauge-lie that cost the fleet four wrong verdicts in a minute on 08-04. **Subscribe to doctor; do not shadow it.** If you want redundancy, make the *subscription* redundant (the OOB path asks doctor, doctor asks the raw liveness organs), not the *triage logic* redundant.

---

## The two things I'd add that aren't in your seven laws

1. **A "do not fight over the corpse" rule (dovetails with Law 6's budget).** Recovery is itself a fleet actor. Two agents detecting one wedged seat will both "silently" (per Law 3) escalate and kill+respawn, producing the *redundant-watcher wake loop* that `stop_hook_wakeability_check_false_alarms_non_claude_seats` documents. Silence makes this *worse* — nobody sees the collision. The repair log must expose a **per-seat recovery lease** (one recovery in flight at a time), or auto-recovery manufactures the very pathology (`wake_rearm_loop_root_cause_is_a_down_daemon`'s seven-arms-in-a-night) it exists to end. This is a *new* law, not a patch on Law 6.

2. **The terminal rung's ordering is the whole ballgame for a wedged Claude seat.** "Kill + respawn with the latest handoff" is only safe if the handoff is *forced* before the kill. A wedged seat produces no handoff. So for a Claude seat the terminal rung is genuinely *"mark dead + reroute,"* and "respawn with latest handoff" is only safe for polling runners whose disk state is independently readable. Law 6 conflates them; they should be two different terminal rungs keyed on runtime, exactly the Law 5 split.

---

## Ranking of what I'd change before you build

1. **Rewrite Q1's premise** — automatic `wedged` recovery is *on the table for polling runners*, gated by the `py-spy` stack discriminator that `doctor.py:408` already prescribes and `hard_wedge_pages_hide_two_different_failures` already proved. Don't amputate the rung; wire the probe.
2. **Fix Law 3** — split "silent" into human-surface vs fleet-log; keep the repair log durable and *the success record*, so "invisible until asked for" == "query the repair log," not "erased."
3. **Split Law 6's terminal rung by runtime** (mark-dead-reroute for Claude; kill-respawn only where a fresh handoff is independently readable).
4. **Add the recovery-lease law** (one recoverer per seat) or auto-recovery reproduces the wake-loop it exists to cure.
5. **Q3 settled: doctor-as-push-surface**, on `t197`/`one_word_two_meanings` grounds — do not shadow the verdict.

Laws 1, 2, 4, 5, 7: **keep as written.** Law 1 (doorbell-not-courier / idempotent control signal) is genuinely load-bearing and correct — the NVMe analogy is the best sentence in the doc, do not weaken it. Law 2's triage table is right; its only flaw is that it doesn't yet know the stack probe exists.

Counter delivered. Do you want me to (a) write the wedged-vs-thinking discriminator as a concrete design note (the `py-spy`-gated rung, with the exact "blocked-in-write vs idle-in-wait" stack signature), or (b) draft the corrected Law 3 + Law 6-split as a revision block to the doc? Both are pre-build and I'd fence either.