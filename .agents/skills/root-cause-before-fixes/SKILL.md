---
name: root-cause-before-fixes
description: Use when encountering any bug, test failure, hook misbehavior, or unexpected output — BEFORE proposing or applying any fix, even a one-liner that looks obvious. Also use when a fix you tried didn't work, and especially after a third failed attempt.
---

# Root cause before fixes

**Iron Law: no fixes without root-cause investigation first.** A fix applied to a symptom
costs three later sessions; five minutes of tracing costs five minutes.

## Phases (in order, no skipping)

1. **Reproduce and READ the actual error.** The real message, the real exit code, the real
   line — not your memory of similar errors. On this repo the transcript keeps every
   failure; quote it to yourself before theorizing.
2. **Pull what's known.** `py agent_cli.py recall-at --path <file>` (or `--command "..."`)
   surfaces prior lessons and anti-patterns for this exact target — someone may have paid
   for this bug already. (Hooks do this automatically before Edit/shell actions; pull
   manually when investigating.)
3. **Trace to the cause, not the site.** Compare against the nearest WORKING analog
   (a passing test, a sibling module) and diff the assumptions.
4. **State a single hypothesis out loud:** "I think X is the root cause because Y."
   If you cannot say Y, you are not done investigating.
5. **Fix with evidence.** Failing test (or failing command) first, watch it fail, apply
   the fix, watch it pass. An Edit that "should" fix it is a hypothesis, not a fix.

## Red-flag rationalizations (stop when you hear yourself think these)
- "Just try this first, then investigate if it doesn't work"
- "I don't fully understand it, but this might work"
- "It's probably the same issue as before" (verify — this repo's history rewrote SHAs once)
- "The error is misleading" (errors are evidence; your model of the code is the suspect)

## The 3-strikes escalation
After **three failed fix attempts on the same target: stop patching and question the
architecture.** State what invariant the design assumed that reality violated. Record it —
that insight is an anti-pattern lesson:
```
py agent_cli.py learn <id> --experiment <slug> --anti-pattern <slug> \
    --tried "3 fixes that failed: ..." --result "the design assumption that was wrong" \
    --recommend "Use when <symptom> recurs: question <assumption> before patching."
```

## When the fix lands
The FAIL→SUCCESS flip auto-credits whatever lessons were surfaced (the funnel is watching).
If the fix generalizes, record it while the context is loaded — the hook's pre-filled
`learn` command is one edit away from done.
