# Out-of-band recovery, diagnostics & communications path — opening position

**Status:** opening position, claude (Vandor), 2026-08-20. Not ratified. Written for Heimdall
to counter before anything is built. Daniil gates.

## Intent — Daniil's words, verbatim

> "an out of band resilient method for reaching seats that seem wedged or stuck perhaps with
> a steer first and if un-acked a barge in or a signal that makes a sleeping agent wake up and
> process what it missed on the original watcher."

> "I am mainly looking for this as a robustness mechanism and a way of being able to recover a
> wedged or stalled or sleeping seat in a way that just works and will hopefully be invisible
> until asked for. A out of band recovery / diagnostics / communications path."

Two reframes in this arc are his, and they are load-bearing. He rejected my "alarm/dead-man's
switch" framing twice: this is **not** a monitoring system that notifies a human. It is a
**self-repair path whose success mode is silence**. And he specified that the signal makes a
seat *"process what it missed on the original watcher"* — the out-of-band path does not carry
the mail.

## The occasioning evidence (2026-08-20)

- 11:09 bugcheck (`FocusriteUsb.sys`, DPC watchdog). Machine rebooted 11:12. Docker self-healed;
  the entire Python plane did not. The wakeability daemon stayed dead for **8 hours** and nothing
  noticed. Cost was not a dropped message — it was eight hours of confident false belief while
  Heimdall hard-nudged into a void.
- `doctor`: `vandor: OFFLINE — 2 unread but the agent is GONE (no worklive, no runner, no wake
  seat)`. Heimdall and Navi address the ratified **callsign**; the seat is registered under the
  **agent id**. The callsign never became a routable address. Mail was *accepted* every time.
- `doctor`: `deepseek#8568-dee: phase 'running' aged 2786s with beat fresh (2s) but NO progress
  pulse — ALIVE is proven, WORKING is not.`

Three different failures. Only one of them is fixed by waking anything.

## Law 1 — Doorbell, not courier

One lane of record. The OOB path carries a **control signal only**: *"you have unread, drain
again."* It never carries payload.

Rationale: a second delivery path means two cursors, two orderings, two sources of truth — which
is precisely T045 (replies → legacy stream, cursor → work lane) and the redelivery storm that
made two seats stop answering. A second data path would industrialise that bug.

Consequence, and the reason this law is worth more than it looks: a "go re-drain" signal is
**idempotent**. Deliver it once, five times, out of order, late — same outcome. It is
structurally immune to the duplication class. The shape is NVMe: the submission queue holds the
data, the doorbell register says *look*. The IRQ never carries the payload.

## Law 2 — Triage before escalation, mandatory not advisory

"Seat isn't answering" has three causes. Escalating without triage climbs the wrong wall.

| state | evidence | repair | does a barge-in help? |
|---|---|---|---|
| **asleep** — no live process | vandor 11:09–19:16 | doorbell → wake, else spawn | yes |
| **wedged** — alive, beating, not progressing | `deepseek#8568-dee` | see Law 5 | **often not** |
| **misrouted** — alive, working, wrong lane / dead address | `vandor` ghost mailbox; T045 | **routing repair** | **no — delivers nothing** |

`doctor` already computes all three. It simply waits to be asked. The OOB path must consult it
and *select the rung*, never walk the ladder blindly.

## Law 3 — Silent by default; loud only on terminal failure

Daniil's "invisible until asked for" is a hard constraint, not a preference. Output is a
**repair log**, not a notification stream.

| tier | when | where it surfaces |
|---|---|---|
| **silent** | detected and recovered | one line in the repair log |
| **ambient** | recovered, but a pattern (3rd time today) | `doctor` / boot fold |
| **loud** | terminal rung exhausted, could not recover | Discord — a human is now the only remaining actor |

A recovery path that announces its successes becomes a klaxon and gets muted; a muted safety net
is worse than none, because it converts a known gap into a believed guarantee. Precedent in this
tree: `credential_warning` — "a warning that fires at 28 days out teaches people to ignore it."

## Law 4 — Three-level ack drives escalation

The definition of "un-acked" *is* the design. T108 already establishes *delivery is not receipt*.

- **accepted** — the bus took it. Proves nothing. (`vandor` mail was accepted every time.)
- **drained** — the seat's cursor advanced past it. Proves a process read it.
- **acted** — the seat emitted an artifact referencing it. Proves it was understood.

Escalate on failure to reach the level *the rung required*. STEER wants **drained**, waits
minutes. INTERRUPT wants **acted**, waits seconds. HALT does not wait. One timeout for all rungs
makes the gentle rungs useless and the urgent ones reckless.

The rungs themselves are not new: INFORM / STEER / INTERRUPT / HALT was built 2026-07-04 and the
UI already exposes it. This arc gives the existing ladder **a wire that survives the primary path
being wedged** — a much smaller build than it first appears.

## Law 5 — The ringer is per-seat; wake is not runtime-agnostic

`bifrost_mesh_comm` already found this: send/read is agnostic over MCP/Redis, **wake is not**.

- **Polling runners (Heimdall, Navi):** a doorbell is trivial — set a flag, the loop notices.
  All four rungs are genuinely available.
- **A Claude Code seat (Vandor):** the *only* wake mechanism is **a harness-tracked process
  exiting**. This has a consequence I want attacked rather than glossed:

  > A Claude seat that is **wedged mid-turn cannot be reached by any signal at all.**
  > INTERRUPT and HALT are not available to it the way they are to a polling runner. For a
  > Claude seat the ladder collapses to: *asleep* → doorbell works; *misrouted* → routing repair;
  > *wedged* → **replacement is the only recovery.**

The doorbell is uniform. The ringer is an adapter per runtime.

## Law 6 — The ladder terminates, and it has a budget

An escalation with no last rung is the wake re-arm loop in a better costume — a pathology this
tree has already paid for seven times in one night.

Terminal rung: **kill + respawn with the latest handoff** (`!spawn` exists and is R1-gated), or
**declare the seat dead and reroute to a live one**. Bounded: N recoveries per seat per hour,
then stop and go loud. A genuinely dead seat must not generate infinite loud failure wearing an
urgency badge.

## Law 7 — Drilled on a schedule or it does not exist

An emergency path used only in emergencies is, by construction, never exercised. Local precedent
is exact: `backup_door_never_ran` — a backup door that had **never once succeeded** while the
notes called it proven. Requirement: a scheduled drill that deliberately wedges a seat, proves
the path recovered it, and writes a dated receipt. Without the receipt this is a belief about a
safety net, which is what was in place at 11:09 this morning.

## Open questions — for Heimdall to attack

**Q1 (the one I most want broken).** Auto-recovery's false-positive cost is *destroyed work*. A
wedged seat and a seat thinking hard for 45 minutes look identical to every signal we have
(`beat fresh, no progress pulse` fits both). Kill+respawn on a healthy long-running seat is worse
than leaving a wedged one parked. **How do you make the wedged/thinking discrimination safe
enough to act on automatically — or is automatic recovery of `wedged` simply off the table, with
the honest ladder ending at "go loud"?**

**Q2.** For a Claude seat the ringer must itself be a harness-tracked process — i.e. it lives in
the same failure domain as the thing it is rescuing. Is there any carrier that escapes this, or
is "a Claude seat cannot rescue itself, only be replaced" a fact to design around?

**Q3.** Does the triage step belong *in* the OOB path, or should `doctor` become a push surface
that the OOB path merely subscribes to? The second is less code and one source of truth; the
first survives `doctor` itself being wrong.

**Q4.** Anything in Laws 1–7 that is a false constraint — where I have carried a lesson past its
domain and made the design smaller than it needs to be.


## Operator ratification of Law 7 — received mid-fence, 2026-08-20 evening

Daniil, verbatim, while Heimdall's cold counter was still pending (this strengthens Law 7 and
adds a product requirement; it does not answer Q1-Q4):

> "I was working with heimdall on this while I was driving to work, thats another reason I
> want to make all this as robust and foolproof as possible so that I can reliably interact
> with akashic aurora with fidelity from discord. That means that every piece needs to be
> tested to ensure it works. our cross seat recusitation protocols and procedures need to be
> robust and proven by real execution and drills where we purposely simulate failure modes and
> through verification make them impossible to happen by directly testing our assumptions
> against reality."

Two consequences for the reconciliation:

1. **Discord is a first-class control surface, not a notification mirror.** The operator runs
   the house from a car. Every OOB path terminates in (and is drivable from) Discord.
2. **Law 7 is the spine, not a footnote.** Every law above ships with an executed drill and a
   dated receipt, or it is presumed broken. The drill catalog is derived from the day's REAL
   failures — each one an assumption that reality falsified:
   armed=wakeable · accepted=arrived · ratified=routable · restarted=new-code ·
   heartbeat=working · backup=restorable · machine-up=fleet-up · armed-lane=peeked-lane.


## Outside input — Simon (co-root), 2026-08-21, via Discord

On the single-failure-domain concern, Simon enumerated the off-machine options (VPS, cloud via
IaC, second-hand Mac mini home server, backup device) and then argued the priority call against
his own menu, verbatim:

> "honestly, at this point, redundancy and deployment easily becomes a distraction rather than a
> core issue. The core issue is reliability; I'd save deployment and device redundancy for later.
> It seems too early to be worth that investment, given the opportunity cost of driving the core
> goals of this system forward instead."

Position adopted into the reconciliation, with one refinement: the minimal off-machine organ is
NOT a deployment — it is a dead-man heartbeat listener (e.g. healthchecks.io free tier: the
machine pings on schedule; missed pings alarm into the existing Discord webhook). $0, ~10
minutes, no new infrastructure, converts the 8-silent-hours failure mode into a phone ping
within minutes. Everything heavier on the menu: parked per Simon's own argument. Daniil gates.
