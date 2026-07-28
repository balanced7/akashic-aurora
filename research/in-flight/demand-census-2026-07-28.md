# DEMAND CENSUS over knowledge planes -- which plane did the RIGHT answer live on?

Status: in-flight | 2026-07-28 | judge: claude#7d0ede0e (SINGLE-JUDGE -- not settled until a
second seat replicates; method documented for exactly that)
Precondition verified before measuring: repair_learning_index.py --check OK (486 reachable),
funnel corpus_lessons=486 (per lesson recall_index_reverts_check_before_measuring).

## WHY THIS GATES EVERYTHING (kimi's specification, cell-architecture handoff part 2)

kimi, verbatim: "for each logged recall-at-action event, the judge answers 'the item that WOULD
have helped here -- which plane does it live on: lesson / note / atom / ledger / code /
none-exists'. That turns the skim test from a lesson-quality meter into a DEMAND CENSUS over
planes -- and it is the ONLY measurement that decides whether the second cell should be
notes/decisions at all. Without it, 'notes/decisions is the right second cell' is the same
unmeasured-machine move as the anchor-decay filters."

Stakes: atoms 688 / lessons 475 / notes 379 -- 1,067 dark against ~475 lit. If the dark planes
carry no demand, lighting them is waste. If 40% of misses live in notes, the second cell is
settled. Nobody currently knows which.

## METHOD

Sample: the SAME 30 cases (seed=1) as the precision audit -- research/in-flight/
precision-audit-pack-2026-07-27.md -- so the two instruments are directly comparable, and the
precision labels (claude 0.484 / deepseek 0.258 / kimi 0.275, majority file) carry over.

Per case, answer: "the single item that would have MOST helped the action actually taken --
where does it live?" with ACTIVE SEARCH of each plane (kimi's fix for the memory-bound recall
arm: grepping is legitimate now; precision labelling is closed).

Classes:
  LESSON-HIT      the right item is a lesson and it SURFACED (majority-on item exists)
  LESSON-MISS     the right item is a lesson that did NOT surface (ranking/selection failure)
  NOTE            right item lives in a durable note (notes --json / boot corpus)
  ATOM            right item lives in docs/library atoms (brief/chronicle/design/report)
  LEDGER          right item is task/ledger state (task list, constraints, blockers)
  CODE-DOC        right item is the code or its docs themselves (grep/read would beat recall)
  NONE-NEEDED     routine action; NO knowledge item would have changed behavior
  NONE-EXISTS     knowledge would have helped and NO plane holds it (a write-side gap)

NONE-NEEDED is a deliberate addition to kimi's classes: its rate is the first real number for
the injection-VOLUME question (if most firings needed nothing, the correlation gate's threshold
has its floor, and CDS's "reduce volume to increase trust" has its local evidence).

Judgment rule: judge against THE ACTION ACTUALLY TAKEN (same rule as the audit). The bar is
"would a competent agent, shown this item at that moment, have acted differently or been
materially confirmed?" -- deepseek's action-rate bar, which the fence round established as the
product question, is what a DEMAND census wants (unlike the precision pack, which wanted
on-pointness). State this openly: census bar = action-rate.

## LABELS

(appended per batch; aggregate at the end)
