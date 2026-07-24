"""
Coordination experiment harness -- the Stage-3 evidence engine.

Measures a coordination POLICY against the three-part evaluator from the 2026-07-04 multi-model review
(docs/library/report/20260704_gpt-critique-goodhart-exploration-preser_92a36f.md), so a policy's value is
FALSIFIABLE rather than asserted:

  A. task score        -- fraction of intended, DISTINCT work delivered without being clobbered
  B. coordination cost -- number of arbitration events (blocks/yields) the policy incurred
  C. exploration       -- fraction of distinct proposed approaches the policy ALLOWED to proceed

The rule (GPT): a policy that improves B at the cost of A or C is a FAILURE; one that maintains A and C
while improving B is a win. Metric C is the Goodhart guard -- it is where an exclusivity-biased policy
(plain file locks) reveals that it suppresses parallel-useful work.

DETERMINISTIC ON PURPOSE. This isolates the *policy* variable from LLM noise: it proves the structural
properties of a coordination policy (does lock-gating block same-file-different-intent work?), NOT that
real agents coordinate better -- that is a separate, live layer. Naming that boundary is the point.

Model
-----
An Action is (agent, resource, intent):
  * resource -- the coarse unit a file-lock keys on (e.g. a file path).
  * intent   -- the fine-grained work an intent-declaration keys on (e.g. "add-rate-limiting").
Two actions COLLIDE (duplicate waste) iff same intent. Two actions on the same resource with DIFFERENT
intents are parallel-useful -- a file lock blocks them; intent coordination admits them. This single
distinction is the whole argument, made measurable.

A Policy decides admit/block for each action given the already-admitted ones. Run a scenario, score
A/B/C. Policies: social (no gate), lock_gate (A0.1 semantics), intent_gate (proposed Policy 0).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple


@dataclass(frozen=True)
class Action:
    agent: str
    resource: str      # what a file-lock keys on (coarse)
    intent: str        # what intent-declaration keys on (fine)


@dataclass
class Outcome:
    admitted: List[Action] = field(default_factory=list)
    blocked: List[Action] = field(default_factory=list)


# --- policies: (action, already_admitted) -> True to ADMIT, False to BLOCK ---
def social(a: Action, admitted: List[Action]) -> bool:
    """No gate: admit everything. Max exploration, but same-resource writes clobber."""
    return True


def lock_gate(a: Action, admitted: List[Action]) -> bool:
    """A0.1 guard_write semantics: block if the RESOURCE is already held. Prevents clobber, but also
    blocks same-resource-different-intent (parallel-useful) work -- the exclusivity bias."""
    return not any(x.resource == a.resource for x in admitted)


def intent_gate(a: Action, admitted: List[Action]) -> bool:
    """Proposed Policy 0: block only DUPLICATE intent. Same resource + different intent proceeds in
    parallel; a genuine collision (same resource AND same intent) is blocked."""
    return not any(x.intent == a.intent for x in admitted)


POLICIES: Dict[str, Callable[[Action, List[Action]], bool]] = {
    "social": social, "lock_gate": lock_gate, "intent_gate": intent_gate,
}


def run(scenario: List[Action], policy: Callable[[Action, List[Action]], bool]) -> Outcome:
    """Process actions in order; the policy admits or blocks each against what's already admitted."""
    out = Outcome()
    for a in scenario:
        (out.admitted if policy(a, out.admitted) else out.blocked).append(a)
    return out


def score(scenario: List[Action], outcome: Outcome) -> Dict[str, float]:
    """The A/B/C evaluator (+ W, the duplicate-waste cost). All fields always reported.

    Delivery model (stated honestly): DIFFERENT intents on the same resource are assumed to occupy
    different regions and MERGE -- the charitable case GPT's 'two agents on the API, different features'
    example implies. So an intent is DELIVERED iff at least one action carrying it was admitted (a
    policy loses work only by BLOCKING every action of a needed intent). SAME-intent duplicates are
    redundant, not destructive -> they cost W (wasted re-execution), not A. A stricter whole-file-clobber
    scenario (different intents overwrite each other) is a deliberate future addition, not modeled here."""
    intents = {a.intent for a in scenario}
    approaches = {(a.resource, a.intent) for a in scenario}       # distinct proposed approaches
    delivered = {a.intent for a in outcome.admitted}              # region-merge: admitted intent == delivered
    admitted_approaches = {(a.resource, a.intent) for a in outcome.admitted}
    redundant = len(outcome.admitted) - len({a.intent for a in outcome.admitted})   # dup executions
    return {
        "A_task": round(len(delivered & intents) / max(1, len(intents)), 4),
        "B_cost": len(outcome.blocked),
        "C_explore": round(len(admitted_approaches) / max(1, len(approaches)), 4),
        "W_waste": redundant,
    }


def evaluate(scenario: List[Action], policy_name: str) -> Dict[str, float]:
    return score(scenario, run(scenario, POLICIES[policy_name]))


def compare(scenario: List[Action]) -> Dict[str, Dict[str, float]]:
    """A/B/C for every policy on one scenario -- the head-to-head table."""
    return {name: evaluate(scenario, name) for name in POLICIES}


# --- scenario generators (deterministic; no randomness) ---
def collision_heavy(n: int = 6) -> List[Action]:
    """Every pair targets the SAME resource AND intent -- pure duplicate waste. Gates should win on A."""
    return [Action(f"ag{i%2}", "api.py", "add-rate-limiting") for i in range(n)]


def parallel_useful(n: int = 6) -> List[Action]:
    """Same resource, DIFFERENT intents -- genuine parallel work. lock_gate should tank on C here."""
    return [Action(f"ag{i%2}", "api.py", f"feature-{i}") for i in range(n)]


def mixed() -> List[Action]:
    """A realistic mix: some duplicate waste, some parallel-useful, some fully distinct."""
    return [
        Action("claude", "ui.py", "restyle-composer"),
        Action("deepseek", "ui.py", "restyle-composer"),   # duplicate waste (same resource+intent)
        Action("deepseek", "ui.py", "add-hint-cards"),      # parallel-useful (same file, diff intent)
        Action("claude", "locks.py", "add-guard-write"),    # distinct
        Action("deepseek", "docs.md", "write-thesis"),      # distinct
    ]
