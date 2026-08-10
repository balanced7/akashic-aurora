"""T260 RED -- "what has Navi learned about X" is not a question the substrate can answer.

GAP 2 OF THE RESIDENTS DESIGN (atom art_20260809_residents-and-callsigns-design_b6c98c,
sec. 6): the learning store holds 837 records attributed per agent, the directive makes each
resident's archive load-bearing ("they each develop memories and their own archives of what
has worked and what hasn't"), and search_learnings_by_keyword(keyword, domain) has a domain
filter and NO agent filter. The per-resident read simply does not exist on any door.

WHY IT MATTERS BEYOND SYMMETRY: T261's caught-up fan branch builds its catch-up pack FROM
this query -- a resident reads its OWN lessons on the way into a question. Without scoping,
the pack would be the whole fleet's corpus, which is precisely not the point of a resident.

THE ONE SUBTLE PIN (P3): the store's weak-match fallback. When nothing clears the relevance
floor, search returns the best few hits FLAGGED weak_match rather than silence -- a deliberate
confession mechanism. Under an agent scope that fallback must not leak OTHER agents' lessons
in: a confession about kimi's archive may only confess kimi's lessons. The degraded answer
must be a SUBSET of the normal one (the audited fallback class).

Run: py -m pytest tests/test_recall_agent_scope.py -q
"""
import os
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


@pytest.fixture(scope="module")
def corpus():
    """Three agents, one shared topic, distinct lessons -- scoping has to tell them apart."""
    # The topic word rides the BODY, not only the name: lesson names are atomic tokens
    # (learning_store.py:75), so a name-only topic is unfindable -- the gap-3 defect, live.
    # This file pins SCOPING; the tokenizer is its own slice.
    rows = [
        ("kimi", "scope_kimi_pools", "convergence: same-checkpoint pools cannot certify completeness"),
        ("kimi", "scope_kimi_fold", "the fold selects for narrative continuity"),
        ("deepseek", "scope_deepseek_wire", "listened to the wire about convergence claims"),
        ("claude", "scope_claude_ledger", "convergence evidence needs an independence ledger"),
    ]
    for agent, exp, tried in rows:
        rc, out, err = run("learn", agent, "--experiment", exp,
                           "--tried", tried, "--result", "scope-pin seed")
        assert rc == 0, f"seed {exp} failed: {err or out}"
    return rows


# ------------------------------------------------------------ P1: the scoped read exists

def test_p1_scoped_search_returns_only_the_named_agents_records(corpus):
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    hits = s.search_learnings_by_keyword("convergence pools completeness", agent="kimi")
    ids = [h.get("id") for h in hits]
    assert "scope_kimi_pools" in ids, "kimi's own lesson must be findable in scope"
    for h in hits:
        assert (h.get("agent_id") or "").strip() == "kimi", \
            f"a kimi-scoped search returned {h.get('id')} authored by {h.get('agent_id')!r}"


def test_p1b_unscoped_search_is_a_superset_of_scoped(corpus):
    """Scoping narrows. It must never surface something the unscoped search cannot see."""
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    scoped = {h.get("id") for h in
              s.search_learnings_by_keyword("convergence", agent="kimi")}
    unscoped = {h.get("id") for h in s.search_learnings_by_keyword("convergence")}
    assert scoped <= unscoped, f"scoped hits outside the unscoped set: {scoped - unscoped}"


def test_p1c_agent_none_is_byte_identical_to_before(corpus):
    """Every existing caller passes no agent; their world must not move."""
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    a = [h.get("id") for h in s.search_learnings_by_keyword("convergence")]
    b = [h.get("id") for h in s.search_learnings_by_keyword("convergence", agent=None)]
    assert a == b


# ------------------------------------------------------------ P2: empty is empty

def test_p2_an_agent_with_no_matches_returns_empty(corpus):
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    assert s.search_learnings_by_keyword("convergence", agent="nobody_by_this_name") == []


# ------------------------------------------------------------ P3: the weak-match fallback

def test_p3_the_weak_match_confession_respects_the_scope(corpus):
    """A nine-word grab-bag that clears no floor triggers the flagged-weak fallback. Under an
    agent scope, that fallback may only confess THAT AGENT's lessons -- the degraded answer
    must be a subset of the normal one, never wider."""
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    hits = s.search_learnings_by_keyword(
        "fold selects narrative continuity checkpoint pools certify wire independence",
        agent="kimi")
    assert hits, "the grab-bag should surface SOMETHING for kimi (weak or strong)"
    for h in hits:
        assert (h.get("agent_id") or "").strip() == "kimi", \
            f"weak-match fallback leaked {h.get('id')} by {h.get('agent_id')!r} into kimi's scope"


# ------------------------------------------------------------ P4: composes with domain

def test_p4_agent_scope_composes_with_domain_scope(corpus):
    from core.learning.learning_store import get_learning_store
    s = get_learning_store()
    # No seeded record carries a domain, so a domain filter must empty the scoped result --
    # BOTH filters applying is the claim; either alone letting records through is the defect.
    hits = s.search_learnings_by_keyword("convergence", agent="kimi", domain="no_such_domain")
    assert hits == [], "agent= and domain= must BOTH apply, not either-or"


# ------------------------------------------------------------ P5: the door

def test_p5_recall_agent_flag_scopes_the_cli(corpus):
    rc, out, _ = run("recall", "convergence", "--agent", "kimi")
    assert rc == 0
    assert "scope_kimi_pools" in out, "kimi's lesson must surface under --agent kimi"
    assert "scope_claude_ledger" not in out, \
        "claude's lesson must NOT surface under --agent kimi"


def test_p5b_recall_without_the_flag_is_unchanged(corpus):
    rc, out, _ = run("recall", "convergence")
    assert rc == 0
    assert "scope_kimi_pools" in out and "scope_claude_ledger" in out, \
        "unscoped recall must keep returning the whole fleet's matches"
