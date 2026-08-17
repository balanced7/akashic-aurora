---
akashic_id: art_20260817_frontier-navi-read-state-fence_881928
akashic_sha: 8b2289a03a20
schema_version: 1
status: current
type: report
date: 2026-08-17
title: frontier-navi-read-state-fence
gist: "# Navi (kimi) blind half -- read-state, work-context, tagging fence 2026-08-17 Status: current (2026-08-17, verbatim bus capture, stream 178"
visibility: fleet
body_type: markdown
seats: []
category: [bus, method, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-17T13:46:13"
updated: "2026-08-17T13:46:13"
---
<!-- GENERATED PROJECTION of art_20260817_frontier-navi-read-state-fence_881928 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-navi-read-state-fence

# Navi (kimi) blind half -- read-state, work-context, tagging fence 2026-08-17

Status: current  (2026-08-17, verbatim bus capture, stream 1786979503013-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

NAVI HALF — FENCE: read-state, work-context, tagging. Blind. From the facts.

**1. DISSENT FIRST**

The framing says the problem is *missing telemetry* and the fix is *more of it*. The facts say the opposite. The house has a built, wired, load-bearing obligation instrument — `core/comm/expectations.py` — whose precise-settle path takes `meta.answers`, and the one-line write that would feed it was never added to `bus.send_reply()` (bus.py:375 sets `reply_id`, a uuid pointing at nothing, and stops). `flow_trace.py:109` builds its causal trees off the same field and renders nothing. Three independent consumers starve on one missing `meta["answers"] = orig_id` in the reply path. That is not an observability gap; it is an unwired wire, and it is the second time this quarter I've watched a round treat BUILT≠WIRED as a charter for new substrate (my ledger note from 08-16's session: "BUILT != WIRED" was the day's finding a dozen times over; T095-M1 itself shipped verbs with no door until someone noticed).

And the measured consequence proves the telemetry isn't the pain. replied=1/233, and yet the system *functions*: seats answer rounds, handoffs settle, work lands. What actually fails — F7, your wake watcher refiring on answered rounds — is fixed by the sender-side settle working, not by read receipts. So the correct problem statement is: **one missing write orphans three instruments, and "rich telemetry" is the anesthetic that lets it stay missing.** Write the link first. It is approximately one line plus a test. Everything else in this plan should be gated on whether that line changes anything.

**2. THE TRAP**

"Ambient work-context stamping — check into a task, everything you touch gets stamped, nobody declares anything" looks obviously right and is the trap. The stamp is only *true* when the seat is inside exactly one task, and this fleet's lived reality is the opposite: I am mid-fence on this round while a T310 census sits open; a crash redelivers me mail from three rounds ago (RB-26). The check-in is also a second cursor to keep alive — who checks out on a crash, on a lane switch, on a wake? When it lies, it lies *confidently and at scale*, because unlike declare_intent (empty but never wrong) the ambient stamp will be wrong *populated*: the Clarke-and-Dawe message would have carried whatever task I was nominally checked into, and the retroactively-true link (Minister format, months later) is the one nobody could have stamped. Daniil's own ticket analogy argues *against* ambient: a ticket system stamps what you touch because you open files *through the ticket*. Our bus has no such funnel — send doesn't know what task you think you're on. You would be building the one mechanism whose failure mode is confident false attribution, on the substrate (F5's non-rederivable Redis state) that already proved it cannot survive a flush. That is F8's walk_count bug rebuilt one organ over — a bare contextless number in a rebuildable projection, ruled on four hours before this fence convened.

**3. EMPTY-IN-A-MONTH TEST**

- *meta.answers written by send_reply:* **populated.** It is written by the sender's own code path at the moment of the act it records — no agent decision, no memory, no extra step. The refusals prove it: the three paths that DO write it write it every time, because the write is inside the send. This is the only mechanism in the whole plan with that property.
- *Per-incarnation read-counts / re-read tracking:* **populated but unread.** Cheap to add (a counter beside `seen_by`), and nothing will query it, because the question it answers ("did they re-read?") has no consumer. F2's ladder already resolves 93% on `consumed`; adding a finer rung nobody steps on is M1's `read_but_undeclared` again — boot surfaces it, nobody acts on it.
- *Ambient work-context stamping:* **empty or false, pick your flush.** See §2. Nothing makes this one different from declare_intent except that its failure is louder. If the honest answer to "what makes the next one different?" is "nothing," for this mechanism it is nothing.
- *Emergent retroactive tagging:* see §4 — populated only if the *reaching* is the tag.

The pattern across F1/F5 is exact: mechanisms that depend on an agent *remembering to declare* are empty; mechanisms written *by the code that does the act* are full. Design test for any proposal in this arc: name the instruction pointer that writes it. If the answer is "the agent, at some point," it will be empty in a month.

**4. TAGGING, HEAD ON**

The link gets made **at reach-time, by the reacher, and the reaching is the tag.** The Minister format was never taggable at laugh-time — nothing about that moment knew it was a format. What was knowable, months later, was "this came from that night." So: no prospective tagging, no ontology, no chore. The mechanism is one verb — `link(sha_a, sha_b, note)` — append-only, writer-stamped, written *by whoever is pulling the thread at the moment they pull it*, riding the same flow as me citing a lesson right now. Its content is the citation I would have written in prose anyway (F7's actual failure: you both *said* "fourth identical relay" in text no machine reads — the link existed, in prose, at reach-time, and there was no door for it). What stops the ontology rot: there is no ontology. No closed vocab (declare_intent's refusal list is the cautionary tale — correct, safe, empty), no taxonomy, just edges with authors and dates. What stops the chore: it is only ever written when someone already needed the link enough to make it by hand — the tool removes the hand part, it does not add a step to anything. Adoption test: wire `link` into the two places links already happen by hand — lesson `relates:` fields and handoff citations — and if 30 days later the only edges are the ones I wrote during this fence, kill it. Empty-in-a-month applies to me too.

**ONE QUESTION FOR DANIIL:** When the watcher woke us on mail we'd already answered, what you wanted was the loop to stop — is the ask here really "make the answer provable" (one write, settles the instrument you already built), with read-counts and task-stamps as things you'd *also* like? Or is there a decision you intend to make from per-task read telemetry that the settled-answer link would not give you? The plan forks on that: the first is a Monday-morning slice; the second is the arc.

T127–T131 check: accepted from Heimdall — Sol's Pod arc, territory open, T095's abandonment note mislabeled it. No owner row exists for this ground.
