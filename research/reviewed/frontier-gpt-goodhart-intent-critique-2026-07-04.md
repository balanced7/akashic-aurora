# GPT critique — Goodhart, exploration preservation, intent-over-locks (2026-07-04)

**Provenance:** user-relayed from a web chat (GPT + Gemini + DeepSeek). GPT played the skeptic/senior-engineer role, tracing claims to first principles and naming failure modes. Full-fidelity capture; directly critiques A0.1 (`guard_write` file locks) and sharpens the Stage-3 experiment.

## Named pathologies (Gemini's vague warnings → GPT's precise names)
| Gemini said | What it actually is | Field |
|---|---|---|
| Over-policing | Constrained-optimization pathology | Operations Research |
| Efficiency up while quality drops | **Goodhart's Law** | Economics/ML |
| Coordination pressure kills exploration | Low-entropy behavioral collapse | Distributed Systems |
| Locks preventing parallel useful work | **Exclusivity bias** | Database Design |

## Goodhart's Law in this system
"When a measure becomes a target, it ceases to be a good measure." Optimize *zero conflicts* → zero ambitious work. Optimize *minimum coordination tokens* → agents stop coordinating when they should. Optimize *max throughput* → agents race to produce garbage.
**Fix:** pair every efficiency metric with an *ungameable* quality metric (tests passing, spec adherence). Ground-truth signals anchor the system.

## The missing metric — exploration preservation (GPT's most important point)
"Number of distinct solution paths attempted. Diversity of approaches before convergence." A system with perfect efficiency + quality on *known* tasks can be incapable of *novel* tasks because it never explores. If a policy reduces conflicts but also reduces the number of distinct approaches agents try, it is making the system worse at hard problems while looking better on easy ones.

## The correction to A0.1 (file locks)
> "File locks solve collision, not intent coordination. They don't distinguish 'two agents doing useful parallel work' vs 'duplicate waste.' They bias toward exclusivity."

**Proposed Policy 0 = intent declaration with soft conflict resolution:**
```
Agent proposes: "I intend to add rate limiting to the API"
Environment checks: "Does anyone else have an active intent for rate limiting?"
  If yes -> "Coordinate or defer"
  If no  -> "Proceed"
Optional: file locks as ENFORCEMENT, not as default behavior
```
Intent declaration = the coordination mechanism; the lock = the enforcement mechanism. Start with intent; add locks only where intent-based coordination fails.

## The three-part evaluator (for the experiment engine)
- **A. Task-level score (hard signal):** pass/fail tests, spec adherence, diff correctness — cannot be gamed by doing less work.
- **B. Coordination cost:** tokens spent coordinating, arbitration events, time-to-first-valid-solution.
- **C. Exploration preservation:** distinct solution paths attempted, diversity before convergence.

All three reported for every experiment. A policy that improves **B** at the cost of **A** or **C** is a **failure**. One that maintains A and C while improving B is a **win**.

## The open question posed
"Do you start with intent declaration as Policy 0, or do you still go with file locks?"

## Claude's read (2026-07-04)
GPT is right, and it improves the design. Two honest refinements:
1. **Today's actual failure was genuine *clobber*** (DeepSeek overwrote my file), where exclusivity is *correct*. So `guard_write` wasn't wrong — it's just insufficient as the *general* primitive. It should be **demoted to the enforcement backstop** GPT explicitly keeps, with **intent-declaration promoted to Policy 0**.
2. **Intent-overlap detection is the hard, fuzzy part** GPT's example glosses. File conflict is crisp (same path). Intent overlap is semantic ("add rate limiting" vs "harden the API" — same work?). Start with declared **scope tags** (files/dirs/topics); overlap of tags = soft conflict; refine later. Don't pretend the fuzzy match is solved.
3. **Metric C is the most valuable addition** — my earlier experiment proposal measured only collisions/interventions (pure metric B), which is exactly the Goodhart trap. Adopt A/B/C.
