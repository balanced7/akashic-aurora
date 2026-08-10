# NEGATIVE RESULT: "generality predicts credit" is not supported by our own corpus

2026-08-10, claude (Opus 5). Measured over 841 lessons, 459 with >=5 impressions,
280 useful votes + 60 helped credits + 44 noise votes.

## What I claimed, and why it was weak

Hours before this measurement I told Daniil, in a message about how generalization works:

> "the top-credited lessons in today's hook traffic are ALL generals, not incident reports
>  ... Generality predicts credit."

That was three lessons, eyeballed from hook traffic that had surfaced during one session --
a sample selected BY the very mechanism whose output I was explaining. I generalized from
three examples inside an argument about the value of generalizing. The corpus caught it.

## Two proxies, both dead

**PROXY 1 -- specificity of the trigger clause.** Count incident markers (T-numbers, .py
paths, dates, shas, :line refs) in the `recommendation` field; fewer markers = more general.

| trigger clause | n | impressions | credit rate | noise rate |
|---|---|---|---|---|
| GENERAL (0 markers) | 354 | 4,674 | **4.21%** | 0.45% |
| SPECIFIC (>=2 markers) | 28 | 371 | **6.47%** | 1.08% |

Wrong direction, and by half again. CALIBRATION ALSO FAILED, which is the part that
matters: of five lessons known to be high-credit generals from live traffic, the proxy
placed them at the 33rd, 48th, 62nd, **89th** and **97th** percentiles of "generality".
An instrument that ranks two of its five known positives in the most-specific decile is not
measuring generality. Same failure as T214, where rarity x subsystem-spread ranked three of
four known-forked terms in the bottom quartile.

**PROXY 2 -- actionable vs conceptual.** Generated POST-HOC from the top/bottom lists, where
the pattern looked obvious: top credit went to operational rules
(`bifrost_send_always_text_file` 30.4%, `mirror_lock_identity_requires_agent_env` 53.8%,
`wmi_process_query_projection` 30.0%) while every 0%-credit lesson was conceptual
("Heuristic importance scoring is a Tier-0 baseline", "Salience promotion is the
reflection/consolidation layer", `semantic_naming_readability_impact`).

| recommendation shape | n | impressions | credit rate |
|---|---|---|---|
| ACTIONABLE (prescribes) | 271 | 3,524 | **5.08%** |
| CONCEPTUAL (describes) | 47 | 625 | **5.12%** |

A four-hundredths-of-a-percent difference. The pattern that was plainly visible in twenty
hand-read titles is absent at corpus scale. This is the eyeball-generalization failure
happening a SECOND time, in the same investigation, after I had just written up the first.

## What survives

The visible top/bottom split is real as an OBSERVATION and unexplained as a MECHANISM. My
current best untested hypothesis is that neither generality nor actionability is the axis --
it is TRIGGER RECURRENCE: a lesson earns credit when its situation actually happens again.
Bus, wake and lock lessons dominate the top because this fleet touches bus, wake and locks
every session; salience-theory and naming-philosophy lessons never fire because their moment
does not come back. That relocates Daniil's insight rather than refuting it -- "wide
applying patterns" would mean patterns whose TRIGGER recurs, not patterns that are abstract.

It is also a third post-hoc proxy fitted to the same data, and I am not going to pretend
otherwise. It needs fresh data, which means credit accrued AFTER a pre-registration.

## Consequence: the ascent rung is NOT built tonight

The plan was to build a rung that compresses incident-lessons into generals, justified by
"generality predicts credit". That justification is now measured false. Building it anyway
would be a cathedral on an assumption -- the exact structure kimi warned about, twice in one
night, in the same session where I ran a drill to avoid it.

What I would need before building it:
1. A PRE-REGISTERED definition of the ascent target, committed before the credit data that
   scores it exists. Post-hoc proxies have now failed twice on this corpus.
2. A calibration set of hand-labelled generals-that-paid and generals-that-did-not, so the
   instrument can be checked against known answers rather than against my intuition.
3. The recurrence hypothesis tested directly: bucket lessons by how often their trigger
   condition arises (measurable from recall-at firing counts, which we already log), and see
   whether that -- rather than any property of the lesson's text -- is what tracks credit.

The 5.0% corpus-wide value rate remains the standing number, unexplained. Whatever explains
it is worth more than the rung I was about to build on top of it.
