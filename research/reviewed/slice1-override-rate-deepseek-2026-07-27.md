# Slice 1 (override rate) -- deepseek counters VERBATIM

Status: current | 2026-07-27

Three counters. Short.

---

**a. No. Override requires an ACT, and no act exists today.** The impression ledger records what was SHOWN. The outcome loop records what was CREDITED on a flip. Neither records "the agent read this and dismissed it." You cannot harvest override from existing behavior because dismissal is invisible — the agent reads the item, does nothing, and the system cannot distinguish "read and dismissed" from "never read" from "read and will use later." Suppression IS the act. Without it, override rate is unmeasurable.

(3) is correct. Slice 1 and slice 2 are one slice. You cannot instrument what doesn't exist.

---

**b. Reflex-dismissal is real, and CDS's defense is what stops us reproducing it.**

CDS override rates are 49-96%. Clinicians dismiss severe drug-interaction alerts. The mechanism that partially mitigates this: **tiered suppression cost.** Dismissing a low-severity alert is one click. Dismissing a high-severity alert requires a reason ("patient is on this medication already," "dose is within protocol"). The reason is auditable and reviewable.

Applied to us: dismissing a lesson that fired on a file path you've seen 10 times this session is one character — cheap, reflexive, fine. Dismissing a lesson that fired on a file you've NEVER touched, with a recommendation that names a specific invariant you'd violate, requires a one-word reason ("known," "irrelevant," "later"). Still cheap. Still inline. But the friction differential makes reflex-dismissal of high-signal items slightly harder, and the reason is the audit trail.

The key: **don't make dismissal harder. Make dismissal of HIGH-STAKES items slightly more deliberate.** The stakeness signal is already computable: anchor verdict (MISSING vs RESOLVED), usefulness counter history, and whether this trigger domain is novel for this seat. A lesson with 3 prior HELPFUL credits that fires on a file you've never opened → ask for a reason. A STARVED lesson that fires on a path you've suppressed twice already → single character dismiss. The cost is proportional to the information you're throwing away.

The unit of accounting is the reason log, not the suppression count. CDS reviews override reasons to tune alert rules. We review dismiss reasons to tune what we surface.

---

**c. Trigger-domain, not lesson, not family.**

Per-lesson is too sparse (475 items, most firing rarely). Per-family is too coarse (all daemon lessons together). Trigger-domain is the right grain: `(source_file_extension, command_family)` or `(trigger_keyword, action_type)`. A lesson about `crash_path_review` dismissed on `bifrost_daemon.py` suppresses for the `(daemon_file, Python)` domain, not for all files. A lesson about `bifrost_send_always_text_file` dismissed on `bifrost-send --help` suppresses for the `(bifrost-send, CLI_inspect)` domain.

This is what your SOC contextual-suppression point demands: "this signature on this host is a known false positive, silence it" — not "silence this signature everywhere." The domain is the host. The suppression is contextual. The override rate is per-domain, and domains with high override rates get their items deprioritized for that domain.

The Tricorder break you named (dozens of analyzers, not hundreds of findings) applies here differently: Tricorder has FEW sources and MANY findings per source. We have MANY sources (475 lessons) and FEW findings per source. The accounting unit must aggregate across sources by domain, not across domains by source. Trigger-domain does that. Per-lesson doesn't. Per-family doesn't.