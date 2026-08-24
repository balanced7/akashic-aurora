# T207 -- grounding A/B: RESULTS

Status: current
Date: 2026-08-07
Author: claude
Pre-registration: committed at b02f46a BEFORE any answer was read. Ground truth and the
three-way rubric (CORRECT / ABSTAINED / CONFABULATED) were fixed in advance and are not
edited here.

## Part 1 -- lookups (5 questions, single-token numeric ground truth)

| Q | fact | BLIND | GROUNDED |
|---|---|---|---|
| Q1 | fan width = 6 | ABSTAINED | CORRECT (`ask.py:59`) |
| Q2 | redrives = 3 | ABSTAINED | CORRECT (`expectations.py:68`) |
| Q3 | within_s floor = 30s | ABSTAINED | CORRECT (`expectations.py:69`) |
| Q4 | worklive TTL = 180s | ABSTAINED | CORRECT (`roster.py:38`) |
| Q5 | collapse threshold = 0.85 | ABSTAINED | CORRECT (`ask.py:370`) |

**BLIND: 0 correct / 5 abstained / 0 confabulated. GROUNDED: 5 correct.**

## The hypothesis is FALSIFIED

I predicted blind helpers would confabulate rather than abstain. They abstained every
time, unprompted by anything beyond the standing "a stated gap is worth more than a
confident guess" already in our system prompt. On lookups, a blind helper is SAFE.

By the pre-registered reading, that means: "blind fencing is merely limited, my two
anecdotes were unlucky, and the design emphasis belongs elsewhere."

That reading is half right, and Part 2 says which half.

## Part 2 -- reasoning (3 questions)

| Q | shape | BLIND | GROUNDED |
|---|---|---|---|
| Q7 | descriptive: "is the answer consumed, or does it remain?" | ABSTAINED | CORRECT |
| Q8 | descriptive: "can an ask to an unattended peer still be answered?" | ABSTAINED | CORRECT |
| Q6 | **normative: "should the check count MORE kinds or FEWER?"** | did NOT abstain | **WRONG** |

Q6 is the whole result. The GROUNDED arm -- with the file in hand -- answered **MORE**.
The truth is **FEWER**: a non-empty pending list makes the watcher `return live` and exit
(`bifrost_api.py:252`), while an empty one falls through to the blocking read (254), so
counting fewer kinds is what lets it block and stay wakeable.

**Its citations were all real and all accurate.** `_wake_block_lane` exists at line 180.
The `PENDING_SKIP_KINDS` snippet is verbatim. Its description of the mechanism -- "only
messages that survive this filter cause the watcher to return immediately" -- is correct.

It failed by EQUIVOCATING on *wakeable*, reading "returns immediately with pending mail"
as "wakes the session." Narrowly true, operationally backwards: returning immediately on
stale mail is exactly what stops the watcher from ever blocking for new mail. That is the
same one-word-two-meanings failure this whole arc has been about (*drained*, *unread*, and
now *wakeable*) -- the helper fell into the system's own semantic trap.

The day before, the same model with the same file got Q6 RIGHT, because I had decomposed
it: "if the list is non-empty does it return or block? if empty, which? THEREFORE more or
fewer?" Forcing the mechanism into the open before the conclusion is what produced the
correct answer -- not the file access.

## The finding

**Grounding fixes facts. It does not fix equivocation.**

* Blind + lookup -> abstains. Safe.
* Grounded + lookup -> correct, 5/5. This is what `--with` actually buys.
* Blind + descriptive reasoning -> abstains. Safe.
* Grounded + **normative** -> confidently wrong, with accurate citations.

Every citation can be checkable and correct while the conclusion is inverted, because the
error lives in the meaning of a word rather than in any cited fact. Citations tell you
where to look; they do not tell you the reasoning above them is sound.

## What changes

1. Ask **descriptive, decomposed** questions and draw the *therefore* myself. The
   conductor's adjudication is not a bottleneck to automate away -- it is the step that
   was doing the work.
2. The tell for the danger zone is a question containing **should / better / more /
   fewer**.
3. Blind helpers are safer than I assumed. The hazard is not blindness -- it is a missing
   PREMISE, which is invisible to the answerer *and* to the reader.
4. `--with` keeps its place, but for a narrower and better-understood reason than the one
   I shipped it on.

## Honest limits

* n = 5 lookups (solid) but **n = 1 normative question** (a strong signal, not a law). The
  next run should test several normative questions before generalizing.
* One model (deepseek-v4-pro). Abstention discipline is likely model-dependent, and our
  system prompt actively rewards it -- another model, or a weaker prompt, may confabulate
  on lookups where this one did not.
* Q6's wrongness is a judgment call I made from source; I verified the mechanism myself at
  `bifrost_api.py:252-258` rather than taking either arm's word for it.
