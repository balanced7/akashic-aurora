---
name: plan-with-the-corpus
description: Use when designing an implementation plan, scoping a slice, starting any multi-step task, or before writing significant code — and use it BEFORE the first Edit, not after. Planning is the highest-leverage review point: a bad plan line becomes hundreds of bad code lines.
---

# Plan with the corpus

Review leverage runs research > plan > code. Lessons that arrive while you are editing
can only save the line in front of you; lessons pulled while PLANNING save the whole
approach. So pull first, plan small, review the plan, then code.

## 1. Pull before you plan
```
py agent_cli.py boot <id> --task "<the slice>"     # ranked against the task
py agent_cli.py recall "<topic keywords>"           # targeted corpus search
```
Check for: prior attempts at this exact thing, anti-patterns on the components you'll
touch, open blockers/notes that change the premise. (Plan-time recall also arrives
automatically on your prompt when the hook is wired — treat it as a starting set,
not the whole corpus.)

## 2. Plan in verifiable steps
- Steps sized minutes-not-hours, each with its own check (a test, a command, a render).
- **No placeholders.** "TBD", "similar to step 3", "handle errors properly" are plan
  failures — resolve them now, while it's cheap.
- State contraindications: what would make this plan WRONG ("don't do this if X").
- Name the verification for the whole slice up front (which suite, which dogfood command).

## 3. Review the plan before the code
Read the plan adversarially once: which step hides the risk? which assumption is
untested? A minute here outweighs a review cycle later. For irreversible or
outward-facing steps, confirm with the human first.

## 4. Execution hygiene
- Keep context lean: hand file PATHS to subagents, never paste bodies ("everything you
  paste stays resident for the rest of the session").
- Fresh context per phase where natural (research → plan → implement), carrying only
  the distilled artifact forward.
- When a step's assumption breaks, go back to the plan — don't improvise the
  architecture mid-edit (see root-cause-before-fixes for the 3-strikes rule).

## 5. Close the loop
The plan's surprises are lessons: what the corpus SHOULD have told you before you started
is exactly what you record when you finish (`learn` with a trigger-phrased recommendation),
so the next plan starts smarter than this one did.
