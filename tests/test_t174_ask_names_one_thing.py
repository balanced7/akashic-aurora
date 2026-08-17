"""PRE-REGISTERED ACCEPTANCE (T174) -- 'ask' names one thing.

T171 minted a CLI verb `ask` (a synchronous helper call, no seat behind it). A bus message kind
'ask' already existed -- in STALE_ASK_KINDS and NOWHERE else. So the token meant two things, and
the kind meaning was the broken one:

    STALE_ASK_KINDS   {question, request, handoff, ask}   <- classifies a stale ask
    ASK_KINDS         {question, request, handoff}        <- gates the AUTO expectation window
    WAKE_WORTHY_KINDS {request, handoff, reply, blocker, question, completion, nudge}

A kind=ask message got no automatic deadline and woke nobody, while the staleness predicate still
called it an ask. That is the kind=review casualty pre-loaded (a peer gate lost to three seats
staying silent), with one escape hatch nobody is told about.

THE RETIREMENT PASSES codex_root's RULE, which is why it is safe. From
fragmentation_cost_is_distributed_obligation_surface_2026_08_05: "Do not merge merely because
current measured consumers treat two tokens alike -- enumerate PRODUCERS, consumers, planes and
enforcement." Enumerated here:

  * PRODUCERS: none. No call site emits kind="ask" -- pinned below by K2, so a future one fails
    loudly instead of inheriting a silent kind.
  * CONSUMERS: one (packet_spec.py:409, the staleness predicate). Unreachable in practice,
    because nothing produces the token it tests for.
  * PLANES: bus only. No event/beat collision.
  * ENFORCEMENT: none -- the token is in no wake, arm, escalate, salient or flaggable set.

HONEST LIMIT: the Bus API exposes inbox/tail/pending, not a full history scan, so "no historical
message ever carried kind=ask" is NOT verified -- only "no code path emits it". The decision is
safe either way: the token is in no other policy set, so such a message was already fully silent,
and removing it from a predicate it can never reach changes no delivery behaviour. This is a
POLICY deletion, not a re-meaning of anything already written -- the append-only substrate is
untouched.

  K1  'ask' is a verb and not a kind -- no *KINDS set in the tree contains it
  K2  no producer emits kind="ask" (the rule made enforceable, not remembered)
  K3  the real ask kinds keep their full membership -- this retires one token, not the concept
  K4  the CLI verb still exists and is the only 'ask' in the lexicon

Run: py -m pytest tests/test_t174_ask_names_one_thing.py -q
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.checkers import check_kind_policy as KP  # noqa: E402

_SEND_FNS = {"send", "send_reply", "broadcast", "emit", "capture_event"}


def _producers_of(kind_literal):
    """Every call site that hands `kind_literal` to a send-shaped function.

    Bus.send(to, kind, content, ...) puts kind at position 1; keyword form is kind=.
    """
    hits = []
    for path in KP._python_files(ROOT):
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if fn not in _SEND_FNS:
                continue
            args = list(node.args[1:2]) + [k.value for k in node.keywords if k.arg == "kind"]
            for a in args:
                if isinstance(a, ast.Constant) and a.value == kind_literal:
                    rel = os.path.relpath(path, ROOT).replace("\\", "/")
                    hits.append(f"{rel}:{node.lineno}")
    return sorted(set(hits))


def test_k1_ask_is_a_verb_not_a_kind():
    holders = [f"{p}:{n}" for (p, n), members in KP.discover_kind_sets(ROOT).items()
               if "ask" in members]
    assert holders == [], (
        f"'ask' is still a message kind in {holders}. It is the T171 CLI verb; one token may not "
        f"mean a synchronous helper call AND a bus message.")


def test_k2_no_producer_emits_kind_ask():
    """codex_root's rule made enforceable: enumerate PRODUCERS, do not merely trust consumers."""
    producers = _producers_of("ask")
    assert producers == [], (
        f"something now emits kind='ask' at {producers}. That token was RETIRED under T174 "
        f"because it woke nobody and armed nothing. Use request / question / handoff, or give "
        f"the new kind full policy membership first -- see the merged record/wire census.")


def test_k3_the_concept_survives_only_the_token_is_retired():
    from core.comm import packet_spec
    from scripts import bifrost_wake as bw
    # T332: the set was renamed NEVER_DROP_WHEN_STALE and gained `blocker`. T174's invariant
    # is that the TOKEN `ask` stays retired -- pinned directly now, instead of riding on an
    # exact-equality assertion that also froze membership T174 never ruled on.
    assert "ask" not in packet_spec.NEVER_DROP_WHEN_STALE
    assert {"question", "request", "handoff"} <= set(packet_spec.NEVER_DROP_WHEN_STALE)
    assert {"question", "request", "handoff"} <= set(bw.WAKE_WORTHY_KINDS), (
        "the real ask kinds must keep waking their recipient")


def test_k4_the_cli_verb_is_the_only_ask_in_the_lexicon():
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert re.search(r'add_parser\(\s*["\']ask["\']', src), "the T171 verb must still be there"
