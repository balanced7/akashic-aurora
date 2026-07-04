"""
Tests for the negotiation round (core/coord/negotiation.py + intent.py proposal functions).

These are hermetically testable because intent.py uses an injectable Redis client.
We test: proposal submission, round state, conflict detection, verdict logic.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.coord import intent


# --- fake Redis for hermetic testing ---
class FakeRedis:
    def __init__(self):
        self.store = {}

    def keys(self, pattern):
        import fnmatch
        return [k for k in self.store if fnmatch.fnmatch(k, pattern)]

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return 1


@pytest.fixture
def client():
    return FakeRedis()


# --- proposal submission ---
def test_propose_submits_and_returns_round_state(client):
    result = intent.propose("claude", {"what": "add rate limiting", "scope": ["api.py"], "estimate": "~5 min"}, client=client)
    assert result["ok"] is True
    assert result["round"]["verdict"] == "green"
    assert len(result["round"]["proposals"]) == 1
    assert result["round"]["proposals"][0]["agent"] == "claude"


def test_two_agents_different_scopes_no_conflict(client):
    intent.propose("claude", {"what": "restyle header", "scope": ["ui.py"], "estimate": "1 slice"}, client=client)
    intent.propose("deepseek", {"what": "add metrics", "scope": ["metrics.py"], "estimate": "2 slices"}, client=client)
    state = intent.round_state(client=client)
    assert state["verdict"] == "green"
    assert len(state["proposals"]) == 2
    assert state["conflicts"] == []


def test_two_agents_same_file_different_intents_amber(client):
    intent.propose("claude", {"what": "restyle header", "scope": ["ui.py"], "estimate": "1 slice"}, client=client)
    intent.propose("deepseek", {"what": "add hint cards", "scope": ["ui.py"], "estimate": "~5 min"}, client=client)
    state = intent.round_state(client=client)
    assert state["verdict"] == "amber"
    assert len(state["conflicts"]) == 1
    c = state["conflicts"][0]
    assert c["file"] == "ui.py"
    assert set(c["agents"]) == {"claude", "deepseek"}
    assert c["same_intent"] is False


def test_two_agents_same_file_same_intent_red(client):
    """Same file + same explicit intent tag = red (duplicate work). The 'what' text differs but the
    intent TAG is the coordination key — this is the whole point of tags over free-text slugging."""
    intent.propose("claude", {"what": "restyle header", "intent": "restyle-header", "scope": ["ui.py"], "estimate": "1 slice"}, client=client)
    intent.propose("deepseek", {"what": "restyle the header", "intent": "restyle-header", "scope": ["ui.py"], "estimate": "~5 min"}, client=client)
    state = intent.round_state(client=client)
    assert state["verdict"] == "red"
    c = state["conflicts"][0]
    assert c["same_intent"] is True


def test_scope_conflict_across_multiple_files(client):
    intent.propose("claude", {"what": "refactor bus", "scope": ["bus.py", "locks.py"], "estimate": "2 slices"}, client=client)
    intent.propose("deepseek", {"what": "add fencing", "scope": ["locks.py", "intent.py"], "estimate": "1 slice"}, client=client)
    state = intent.round_state(client=client)
    assert state["verdict"] == "amber"   # same file (locks.py) but different intents
    assert len(state["conflicts"]) == 1
    assert state["conflicts"][0]["file"] == "locks.py"


def test_clear_round_removes_proposals(client):
    intent.propose("claude", {"what": "test", "scope": ["x.py"], "estimate": "1 min"}, client=client)
    intent.propose("deepseek", {"what": "test2", "scope": ["y.py"], "estimate": "1 min"}, client=client)
    assert len(intent.round_state(client=client)["proposals"]) == 2
    count = intent.clear_round(client=client)
    assert count == 2
    assert intent.round_state(client=client)["proposals"] == []


def test_round_state_empty_offline(client):
    state = intent.round_state(client=client)
    assert state["proposals"] == []
    assert state["verdict"] == "green"
    assert state["agents"] == []


def test_scope_normalization(client):
    """String scope is normalized to list."""
    result = intent.propose("claude", {"what": "fix bug", "scope": "api.py", "estimate": "~5 min"}, client=client)
    assert result["round"]["proposals"][0]["scope"] == ["api.py"]


def test_round_id_stable():
    """Same minute produces same round id."""
    id1 = intent._round_id()
    id2 = intent._round_id()
    assert id1 == id2


def test_full_round_flow(client):
    """End-to-end: propose x2 (same file + same intent tag = red), check state, clear, verify empty."""
    intent.propose("claude", {"what": "add tests", "intent": "add-tests", "scope": ["test_x.py"], "estimate": "1 slice"}, client=client)
    s1 = intent.round_state(client=client)
    assert s1["verdict"] == "green"
    intent.propose("deepseek", {"what": "add tests", "intent": "add-tests", "scope": ["test_x.py"], "estimate": "~5 min"}, client=client)
    s2 = intent.round_state(client=client)
    assert s2["verdict"] == "red"  # same file + same intent tag
    intent.clear_round(client=client)
    s3 = intent.round_state(client=client)
    assert s3["proposals"] == []
