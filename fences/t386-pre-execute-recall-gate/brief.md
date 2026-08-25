# M1-BRIEF — t386-pre-execute-recall-gate

## CHARTER
Daniil, 2026-08-24, on the last unclosed DSH tier: "How do we fix action recall to not be
one beat late. DSH is built to be modular, can we integrate the API runner to DSH to overcome
the limitations?" — then, on the design Rill proposed: "can you fence this to Heimdall I want
to see what his approach would be and his thoughts as well."

This fence designs the ONE remaining trigger gap of the DSH integration: recall reaches the
seat one beat after the action, because DSH's pre-execute seam is gate-only with no inject
(t383 inventory) and the model's tool-call decision precedes every pre-execution seam. The
question is whether a PRE-EXECUTE RECALL GATE — deny-with-teaching on scope-matched lessons —
closes the gap honestly, and what its contract is.

## INPUTS (measured 2026-08-24, receipts in-repo)
- The harness contract already ships the pattern: approval-style pre-execute decisions return
  deny + reason; the tool fails with the reason as feedback and the model retries with the
  reason in hand (dsh-tools/lib/index.js:3345-3353, the user-approval dance).
- PostToolDecision (post-execute) carries additionalContexts (dsh-tool-cordis/lib/index.js:5394);
  the pre-execute waterfall is gate-only, NO inject (t383 fence inventory).
- agent.steer exists, but its contract says steering runs ANOTHER step (dsh-tool-cordis
  tool description) — steering is +1, not same-step.
- The current T3 is one-beat-late BY CONSTRUCTION: post-execute context rides the next step's
  active batch (dsh-agent-loop/lib/index.js:183).
- The gate's fuel is the t385 design (scoped lessons with declared class/glob scopes) — a
  deny-with-teaching gate fires ONLY when a scope matches, which is what keeps it from
  becoming alert fatigue (the corpus law: a trigger that fires on everything is a trigger
  nobody reads).
- The pluggable-execution option exists: tools/execute is a waterfall and the code-runtime is
  swappable; an out-of-process variant would sit in front of dsh-api-gateway (Rill's
  "API runner" reading of Daniil's hint). Both are the same shape one hop apart.

## RULES OF ENGAGEMENT
Blind halves: do not read the other half before sealing yours. Every load-bearing claim
carries a line-start V-verdict with the tag on the verdict's FIRST PHYSICAL LINE
([CERTAIN|DESIGN|INFERRED|UNCERTAIN]; CERTAIN requires file:line). MEASURE, DO NOT SPECULATE:
a claim about what a seam does must be a runnable invocation or a cited contract, never an
inference from prose. Write via `py agent_cli.py fence write t386-pre-execute-recall-gate
--slot half_a|half_b --by <agent> --file <path>`, then `fence seal`.

Security-adjacent constraint, non-negotiable: a gate that can DENY tool execution must not be
able to silently swallow the denial — the model must always see the feedback, and the gate
must fail OPEN on any exception in its own code (a broken recall gate must never brick a
tool).

## THE QUESTION
(a) **THE GATE.** Should a pre-execute recall gate deny-with-teaching on scope-matched
lessons, and if so: what does the gate consult (lesson scopes only? locks? both?), what is
the deny decision's exact shape, how does the model get the lesson before the retry, and what
stops the retry from being re-denied (a seen-mark at the gate)?
(b) **THE COST.** What does it cost per call (the t385 per-call discipline) and what is the
fatigue budget — when must it fire, when must it stay silent, and how is "silent when it
should have fired" measured?
(c) **THE SEAM.** Where exactly does the gate live so BOTH harnesses implement one contract
(in-process pre-execute for DSH; the PreToolUse deny shape for claude-code) — and is the
out-of-process API-runner variant better, equal, or worse for the failure modes (fail-open,
latency, observability)?
(d) **THE TRUTH CHECK.** Is one-beat-late even the right thing to fix — or is the honest
maximum a hybrid (ambient recall stays +1, classed dangers stop the action)? Answer
explicitly, because the registry tier T3's final grade depends on it.

## OUTPUT CONTRACT
A numbered design (V-tagged, citations real), at least TWO MEASUREMENTS you ran yourself with
invocation and result shown verbatim, the per-call cost and the fatigue budget, a file plan,
and a RISKS section naming the top two ways this gate makes things WORSE (a gate that bricks
tools or one that teaches nothing and only adds latency). Length: whatever the design needs,
no padding.

## SEAT NOTE (independence)
The brief author (dsh_agent) proposed the gate; he will hold half_b blind. Heimdall holds
half_a. Vandor reconciles when his servers clear. The brief is a proposal, not a ruling —
half_a is explicitly invited to argue AGAINST the gate if the evidence says so.
