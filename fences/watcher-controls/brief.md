# HOUSE FENCE — watcher-controls: which control-room mechanisms do we build into mail/wake, and in what order?

**Opened** 2026-09-29 by Vandor (claude), conducting, at Daniel's ask. **Sub-fence** of the open house
round `fences/watcher-reliability/` (brief + halves from Heimdall and Navi; sol / rill / codex_root
pending). This one is two-party through the door — claude ↔ deepseek/Heimdall — because the round's
five-seat shape has no door slots, and because the last loose directory (prod-reconcile) bounced a
blind grade for five days.

## Daniel's ask, verbatim

> "I wonder how similar the issue we are solving is to industrial controls logic? What are some areas
> of controls we could learn from?" (2026-09-28)
> "Lets build the controls lens into the watcher round with Heimdall." (2026-09-29)

## THE QUESTION

Nine control-room mechanisms were mapped onto our substrate in
`research/in-flight/watcher-reliability-controls-lens-2026-09-28.md`:
(1) the ISA-18.2 alarm state machine, rationalization, and the EEMUA KPIs;
(2) PLC edge-from-level (`R_TRIG`), the first-scan bit, the seal-in latch, RETAIN;
(3) SIS de-energize-to-trip, PFD vs spurious-trip as two numbers, 1oo2/2oo2 voting, proof-test
    intervals, bypass management;
(4) CIP change-of-state with a cyclic heartbeat; PROFIsafe consecutive numbers and watchdog;
(5) a standard seat state model (PackML: Idle / Execute / Held / Suspended / Aborted);
(6) OPC quality codes on every liveness read;
(7) the ISA-101 alarm summary as the boot header;
(8) permit-to-work as the obligation record;
(9) anti-windup for the pager.

For each: does it map onto a seam we ACTUALLY have (file:line), what would it cost, in what order
should it be built, and which of the nine would teach something FALSE about our system if built as
described? Then: if we could build only one this week, which removes the most of the measured pain?

## CHARTER

Turn a lens into a build order without laundering an analogy into a mechanism. The round already
holds the measured pain — three arms that fired within seconds, 30 twins on the third fire, eight
operator chats drowned, 22 identical breaker pages in 2.5 h from one daemon, 157 items / 857 h
behind a page whose remedy is not a verb, a live seat paged UNMANNED across two liveness planes — and
two positions (Heimdall: wake on existence, a rate limit is a dismissal counter's cousin; Navi: five
axes collapse to two, three planes, obligation facts stateful and unnamed). The lens claims each of
those has a forty-year-old name and a standard remedy. This fence decides which claims survive
contact with our code.

## INPUTS

- `fences/watcher-reliability/brief.md` — the measured state, plus the evidence appended 2026-09-28
  20:20 (the kimi daemon: presence held, child blocked, 22 pages, seat live under a bare successor)
- `fences/watcher-reliability/half-heimdall.md`, `half-navi.md`
- `research/in-flight/watcher-reliability-controls-lens-2026-09-28.md` — the lens; every mapping
  cites our files
- the deck https://claude.ai/artifact/BXBNSPefZBYnqBmZX9oFEU, slides 11–15 and 21 (planes, smear,
  verbs, page, build order)
- code seams: `scripts/bifrost_wake.py:404` (the KNOWN SEAM); `scripts/bifrost_daemon.py:386-425`
  (W102 idle path at boot; the breaker broadcast); `core/comm/wake_tiers.py` (`admits(tier, floor)`);
  `core/comm/liveness.py` (the two worklive keys); `core/comm/mailbox.py:50` (INTENTS =
  act/decline/delegate/defer); the bench (park, never drop); `core/toolbelt/registry.py:83` (the
  sugar-only refusal — the rationalization law we already own)

## RULES OF ENGAGEMENT

Blind: half_a (Heimdall) and half_b (claude) are written without each other in view; both may read
every input. A mapping is CERTAIN only with a file:line on OUR side and a named standard on theirs;
an analogy with no seam is INFERRED at best. "Teaches something false" is a first-class verdict, not
a footnote. Disagreements re-open with a command or a drill, never a defence. The round's constraints
stand: detect-as-non-consuming stays; watchers harness-tracked; nothing quietly converts unhandled
into handled; a dismissal counter from day one. The fence closes on `fence pv`.

## OUTPUT CONTRACT

One verdict line per mechanism, in the order above, one physical line each:
`V<n>. [CERTAIN|DESIGN|INFERRED|UNCERTAIN] <mechanism> -- maps to <file:line | NONE> / cost <small|medium|large> / order <n> / false-if <what would be false, or none>`
V10 = the one-this-week pick, naming the measured pain it removes. Then prose as needed.
The reconciliation becomes the BUILD SPEC for the round's build half; every item in it ships
claude+Heimdall fenced at each stage, with an executed drill and a dated receipt before it is
called done.
