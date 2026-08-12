# RESULTS: the resident kill-drill (tier 0 vs tier 1)

Run 2026-08-10, after the pre-registration was committed at 808b7f2. claude (Opus 5).
Total spend: $0.045. Same model (deepseek-v4-pro), same question, same evidence pack,
same window. Evidence pack identical across arms including its clip
(ask.py: 20,576 of 58,346 chars shown) -- held constant, and it bounds what any arm could see.

## Raw

| arm | tier | findings | REAL after triage | false positives | completion tok |
|---|---|---|---|---|---|
| A blind | blind | 1 | **0** | 1 | 3,395 |
| B resident (Heimdall, own archive) | resident | 3 | **2** | 1 | 2,855 |
| C blind + FOREIGN archive (kimi's) | blind | 0 | **0** | 0 | 5,119 |

## Triage, each verified against the source rather than accepted

**ARM A -- FALSE POSITIVE.** Claimed `build_context` renumbers a truncated file's lines
from 1 so citations are unverifiable. Checked ask.py:164-169: `body = text[:room]` is a
PREFIX, so line 1 of the body IS line 1 of the file and the numbering is correct. The arm
reasoned as though the clip took a tail. Its single finding does not survive.

**ARM B FINDING 1 -- FALSE POSITIVE.** Claimed `str(h.get("id"))` can render "None".
Checked learning_store.py:767-780: every returned row is `{"id": exp_id, **data}` and no
stored record carries an `id` field to override it. Cannot occur.

**ARM B FINDING 2 -- REAL.** `_records` and `_role_records` swallow a corrupt JSON row with
`except: continue`, so a dropped record is invisible to the caller. Its own framing is the
sharp part: this "violates the module's own rule that absence must not be treated as
success" -- the module docstring states that law and the code breaks it two functions
below. Same shape as T178's guard-of-guards and the claim-audit class.

**ARM B FINDING 3 -- REAL.** `_receipt_author` catches bare `Exception` and returns None,
which the ceremony reads as "receipt does not resolve" and REFUSES the nomination. So a
store outage or an ImportError silently becomes a verdict about someone's callsign
evidence. Absence vs UNKNOWN, in a door built to be strict about exactly that.

**ARM C -- ZERO, and it burned the most tokens doing it.** It raised one candidate, argued
itself out of it in public ("wait, let me re-examine... I withdraw that finding"), then
returned NONE, spending 5,119 completion tokens -- 80% more than the resident arm -- to
find nothing.

## Against the pre-registered bars

**BAR 1 (weak: a finding CITES a recalled lesson) -- NOT CLEARED.** Arm B cited no lesson
by name. Its best finding invokes "the module's own rule", which is in the DOCSTRING inside
the evidence pack, not in its archive. Six lessons rode its context and none were named.
By my own [M]-tag law -- it must mean I HAVE THE RECEIPT, never I REMEMBER -- an
unattributed improvement cannot be scored as a memory effect.

**BAR 2 (strong: impossible without the memory) -- NOT CLEARED.** Follows.

**H1 (mine)** -- partially: tier 1 produced real findings tier 0 missed, but not at the bar.
**H2 (mine, LOW confidence)** -- FAILED, as predicted.
**H3 (kimi's null)** -- SURVIVES AT THE BAR IT SET. No attributed memory effect exists.
**H4 (volume confound)** -- REJECTED, and this is the sharpest result: if extra context were
the mechanism, arm C should have helped. It hurt. Foreign memory produced fewer findings
than no memory at all.

## What this licenses, and what it does not

LICENSED: tier 1 out-yielded tier 0 two real defects to zero, at n=1, on one target, with
one question. The direction is favourable and it is a SIGNAL, not a law.

NOT LICENSED: any claim that MEMORY caused it. Two rival explanations survive and I cannot
separate them here. (a) The identity framing alone -- "you are Heimdall, who went and
listened to the wire" is a role-prime, and kimi's own
`high_leverage_clauses_are_permissions_not_roles` measured personas NOT improving accuracy
across 162 roles / 2410 questions, which argues against this one. (b) Relevance of the
extra context, independent of whose it is. Arm C under-controls volume: kimi's relevant
pack was 799 chars / 2 lessons against deepseek's 2,000 / 6, because deepseek genuinely
knows more about mechanism code. Size was not matched and could not honestly be padded.

So kimi's verdict stands: persistence is still not isolated as the cause of a win. What
changed is that it is no longer unsupported in the other direction either.

## The finding nobody predicted: foreign memory is worse than none

Arm C is the result I did not hypothesise and would not have found with kimi's two-arm
design. Loading an agent with ANOTHER agent's relevant-looking history made it slower,
costlier and blind: 5,119 completion tokens, one self-retracted candidate, zero findings.
It reads like ontological capture -- kimi's own coinage, arriving from the far side.

CONSEQUENCE FOR THE FLEET, and it is immediate: T261's catch-up pack MUST stay
agent-scoped. T260's `agent=` filter is not a symmetry nicety, it is the thing standing
between a resident and this failure mode. A "fleet-wide context pack" -- the obvious next
feature, and one I would have built cheerfully -- is now measured as ACTIVELY HARMFUL.

## Next measurement, if this is pursued

The attribution gap is the whole game, and it is fixable by INSTRUMENT rather than by
argument: make the resident brief REQUIRE a citation line per finding ("which recalled
lesson, if any, produced this -- NONE is a legitimate answer"). That converts BAR 1 from
something I score by reading into something the arm reports, and a lie becomes checkable
against the pack it was given. n=1 also needs to become n>=5 before anything here is more
than a signal.
