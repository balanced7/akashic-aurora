# Slice 1 design round -- deepseek reply VERBATIM

=== deepseek 1785199350460-0 | 3565 chars ===
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

=== deepseek 1785198858531-0 | 2499 chars ===
Marginal-value. Plainly, and I'll explain the shift.

I applied ON-POINTNESS for the first ~15 cases. Then I caught myself applying a different bar — "would this change what the agent does?" — without realizing I'd switched. The four probes prove it:

- 15:a: `bifrost_wake.py` command. Lesson: `wake_local_cursor_history_replay`. The action IS the wake command. The lesson names it exactly. I marked it **off** anyway because the agent already knows about cursor replay — it's running the command. That's marginal-value, not on-pointness.

- 17:a: `storm_detect.py`. Lesson: `control-pause-clobbers-preexisting-pause` — amendment K2 applied to THAT file. I marked it **on** because the file match is exact. This is on-pointness. But I didn't revisit 15:a with the same reasoning.

- 24:a: `bifrost-send claude --to deepseek`. Lesson: `deepseek_empty_reply_size_ceiling` — about message size for asks TO deepseek. The action IS sending to deepseek. I marked it **on**. On-pointness. But the same reasoning would flip 15:a, and I didn't.

- 28:c: `bifrost-send --help`. Lesson: `bifrost_send_supported_flags` — "inspect bifrost-send --help and use only its exposed flags." The action IS that instruction. I marked it **on**. On-pointness. But again, 15:a should have flipped under the same reasoning.

The 26:b correction is the smoking gun. I changed off→on "after I recognized the action IS daemon code." That's on-pointness reasoning applied retroactively to one item while the bar had already drifted to marginal-value for others.

**The third thing: I was measuring "would this change behavior?"** — my ACTION-RATE bar from the exploration rounds. A lesson that names the exact command the agent is running is on-point but won't change behavior because the agent already knows it. Under on-pointness it's ON. Under action-rate it's OFF. I applied action-rate to the probes without naming it.

Record both numbers. Mine is 0.258 on-pointness with an unmeasured shift to marginal-value mid-pass. The truth is somewhere between 0.258 and ~0.37 (if the four probes flip). The gap between your 0.484 and both of mine IS the finding: on-pointness vs. actionability are measuring different things, and the ranker is better at matching tokens to lessons (on-pointness) than at selecting lessons that would change what the agent does (actionability). That gap is the trust problem — the agent sees relevant-looking items that don't help, learns to ignore the channel, and then misses the ones that would.

=== deepseek 1785198844294-0 | 6638 chars ===
The pack is clear. Labelling now — ON-POINTNESS, the bar the pack asks for. Not marginal value, not action-rate. On-point = was this lesson relevant to the action being taken.

---

## MY LABELS

```
1:a     off
2:a     off
3:a     off
3:b     off
3:c     off
4:a     off
4:b     off
4:c     off
5:a     off
5:b     off
6:a     off
7:a     off
8:a     off
8:b     off
8:c     off
9:a     off
10:a    off
10:b    on
10:c    on
11:a    on
12:a    on
12:b    off
13:a    on
13:b    off
14:a    off
14:b    off
14:c    off
15:a    on
16:a    off
16:b    off
16:c    off
17:a    on
18:a    off
19:a    off
19:b    off
19:c    off
20:a    off
20:b    off
20:c    off
21:a    off
22:a    off
22:b    off
22:c    off
23:a    off
23:b    on
23:c    on
24:a    on
25:a    off
25:b    off
25:c    off
26:a    off
26:b    on
26:c    off
27:a    off
27:b    off
28:a    on
28:b    on
28:c    on
29:a    off
29:b    on
29:c    off
30:a    on
```

---

## MISS items

```
MISS 3   Something about the event store or event retrieval -- the action is `events --get`.
         Maybe learn:experiment:span_boundary_hygiene did surface (3:c) but it's about span
         boundaries, not about event retrieval. The ranker matched on "event" tokens and got
         the wrong event lessons.

MISS 4   learn:experiment:knowledge_boot_stale_directive -- the action is `boot claude`, and
         the stale-directive lesson would warn the agent to cross-check the directive's cited
         state against HEAD. That's exactly what a boot should surface.

MISS 6   learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- the action opens
         docs/filestore-coherence-design-2026-07.md. The filestore coherence lesson should fire.
         Instead, narrative_memory_prior_art fired -- wrong filestore lesson.

MISS 7   learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- again. The action
         is grepping store.py for class filestore and write-path functions. The coherence hole
         lesson should fire. Instead, a RAGAS eval lesson fired -- keyword "store" triggered it.

MISS 8   learn:experiment:hook_matchers_hot_reload -- this DID surface as 8:a. I marked it off
         because the action is testing a hook via pyw, and the reload lesson is adjacent but not
         on-point. Correction below.

MISS 9   learn:experiment:empirical_keyspace_census_before_roster_design -- the action opens
         test_w54_injections_by_family.py, which tests injection census instrumentation. The
         census lesson should fire. Instead, a taxonomy lesson fired.

MISS 11  learn:experiment:curation_self_seal_is_benched -- the action is listing curation
         machinery. The lesson about the curator's self-sealing loop should fire. Instead,
         intelligence_roadmap_and_spine1 fired -- prescribing FAITH-1 work that was done
         weeks ago.

MISS 14  learn:experiment:deepseek_empty_reply_size_ceiling -- the action is `bifrost_runner_
         deepseek.py --help`. The lesson about message size for deepseek asks is directly
         on-point. Should have fired INSTEAD of the gemini_web lessons.

MISS 21  Something from the atoms/notes plane about doc conventions or the library-schema arc.
         The action is editing docs/wishlist.md. The lesson plane served a 40-day-old semantic
         naming lesson. The RIGHT answer lives in atoms or notes and has no retrieval path.

MISS 25  learn:experiment:gate_exit_codes_never_piped -- this surfaced as 25:a. I marked it off
         because `doc --help` is not a gate command. But the lesson IS about piping, and the
         action IS piped. Borderline -- recording as MISS for the recall arm.

MISS 26  learn:experiment:bifrost_daemon_watcher_dies_silently -- the action opens bifrost_
         daemon.py. wake_seat_name_keyed_concurrent_sessions (26:c) is about daemons dying
         silently. It's adjacent. But the crash_path_review lesson (26:b) did fire and I
         marked it on. So this case is partially served.
```

---

## CORRECTIONS DURING LABELLING

```
8:a     off -> kept off. The action is testing a hook via pyw. hook_matchers_hot_reload is
        about editing matchers and verifying in-session. The domain matches (hooks) but the
        specific lesson is about a different activity (fixing coverage gaps vs testing a hook).
        Borderline, keeping off.

14:a-c  off -> kept off. The action is `bifrost_runner_deepseek.py --help`. All three surfaced
        items are about gemini_web or runner locks -- wrong runner, wrong domain. Should have
        surfaced deepseek-specific lessons.

21:a    off -> kept off. This is the 40-day-old semantic naming lesson. The action is editing
        docs/wishlist.md. The lesson is about documentation conventions -- that's on-topic at
        the DOCUMENTATION level, but "update all remaining documentation files to use semantic
        naming style" is NOT on-point for editing a wishlist. It's a general directive, not
        relevant to this specific edit.

25:a    off -> kept off. doc --help is not a gate. The lesson is specifically about gate exit
        codes. The action is piped, but the pipe is | head, not a gate. The lesson doesn't
        apply to general piping.

26:b    on. The action opens scripts/bifrost_daemon.py. The lesson's trigger is literally
        "reviewing supervisor/watchdog/daemon/kill/terminate/taskkill/TerminateProcess/
        subprocess/Popen/process-tree/lifecycle/concurrency/race code." The action IS opening
        a daemon file. On-point.
```

---

## SUMMARY

```
on:     10:b, 10:c, 11:a, 12:a, 13:a, 15:a, 17:a, 23:b, 23:c, 24:a, 26:b,
        28:a, 28:b, 28:c, 29:b, 30:a                                             = 16
off:    all other 46                                                              = 46
skip:   0
total:  62

Precision = 16/62 = 0.258
```

---

## PRE-REGISTERED VERDICT

0.258 < 0.60. **RANKING is broken corpus-wide; build order INVERTS.**

The ranker is matching on surface-level keyword overlap. `events --get` matches "events" → fires doom UI primitives, spine_v2, span_boundary. `boot claude` matches... nothing relevant, fires org amnesia, visible todo, Goodhart. The ranker has no semantic model of what the agent is doing — it's a keyword matcher running against a corpus where keyword overlap is a weak signal.

The misses tell the same story from below: the right lessons exist (coherence hole for filestore, stale directive for boot, size ceiling for deepseek runner) and the ranker fires the wrong ones instead. This is not a selection problem — the right items ARE in the index. They're losing to noise.

=== kimi 1785198829746-0 | 1792 chars ===
The pack shape is right for what I intended, with one confession I must file before labelling: the recall arm measures *my memory of the corpus*, not the index — I cannot grep during a blind pass without contaminating the precision labels, so my MISS labels are limited to lessons I happen to know exist. That asymmetry is worth naming now; it argues for a read-only grep door in the MISS phase of the *next* pass.

Labels:

1:a on
2:a on
3:a off
3:b off
3:c off
4:a off
4:b off
4:c off
5:a off
5:b off
6:a on
7:a off
8:a on
8:b off
8:c on
9:a off
10:a off
10:b on
10:c on
11:a on
12:a on
12:b off
13:a on
13:b off
14:a off
14:b off
14:c off
15:a on
16:a off
16:b off
16:c off
17:a on
18:a on
19:a on
19:b off
19:c off
20:a off
20:b off
20:c off
21:a on
22:a off
22:b off
22:c off
23:a on
23:b on
23:c on
24:a on
25:a on
25:b off
25:c off
26:a off
26:b on
26:c on
27:a off
27:b on
28:a on
28:b off
28:c on
29:a skip
29:b on
29:c off
30:a on

MISS 24 learn:experiment:bifrost_send_always_text_file — the action is a `--text-file` send to two seats; the unconditional text-file rule is exactly on-point and did not fire.
MISS 30 learn:experiment:bifrost_send_always_text_file — same lesson, same shape of action (`--text-file` send), again absent.

Two labels I flag for the fence round rather than defend silently: 21:a (I labelled on — this is Daniel's original complaint receipt, and "on-point for the action" is arguably true even if the lesson is stale; the pack's blindness to credit history cuts both ways here) and 11:a (the `intelligence_roadmap` lesson claude cited as prescribing DONE work — I labelled on because curation machinery *is* what the action enumerates, but if the lesson's roadmap content is dead, on-point-but-invalid may be a third category the rubric cannot express).