"""Advisory path-locks with fencing tokens + TTL (Concurrency design C2).

Hermetic: a tiny in-memory fake Redis (shared between the two agents' managers) so
tests never touch canonical Redis. Covers acquire/deny, re-entrancy, holder-only
release, the fencing-token check, TTL reclaim, awareness listing, fail-soft offline,
and the hook's peer-lock veto for Edit/Write.

Run: py -m pytest tests/test_locks.py -q
"""
import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import locks as L
from core.comm.locks import LockManager, path_conflict, normalize_path


class FakeRedis:
    """Just enough Redis for LockManager, with a controllable clock for TTL tests."""
    def __init__(self):
        self.kv, self.exp, self.t = {}, {}, [1000.0]

    def _alive(self, k):
        if k in self.exp and self.t[0] >= self.exp[k]:
            self.kv.pop(k, None); self.exp.pop(k, None)
        return k in self.kv

    def incr(self, k):
        v = (int(self.kv[k]) + 1) if self._alive(k) else 1
        self.kv[k] = str(v); self.exp.pop(k, None); return v

    def get(self, k):
        return self.kv[k] if self._alive(k) else None

    def set(self, k, v, nx=False, ex=None):
        if nx and self._alive(k):
            return None
        self.kv[k] = v
        if ex is not None:
            self.exp[k] = self.t[0] + ex
        else:
            self.exp.pop(k, None)
        return True

    def delete(self, k):
        self.kv.pop(k, None); self.exp.pop(k, None); return 1

    def scan_iter(self, pattern):
        return [k for k in list(self.kv) if self._alive(k) and fnmatch.fnmatch(k, pattern)]

    def advance(self, seconds):
        self.t[0] += seconds


def _two():
    fake = FakeRedis()
    return fake, LockManager("claude", client=fake), LockManager("cursor", client=fake)


# ------------------------------------------------------------------- acquire/deny
def test_acquire_then_peer_denied():
    _, claude, cursor = _two()
    a = claude.acquire("scripts/x.py")
    assert a["ok"] and a["mine"] and a["held_by"] == "claude"
    b = cursor.acquire("scripts/x.py")
    assert b["ok"] is False and b["held_by"] == "claude" and b["token"] == a["token"]


def test_reacquire_is_reentrant_same_token():
    _, claude, _ = _two()
    t1 = claude.acquire("a/b.py")["token"]
    again = claude.acquire("a/b.py")
    assert again["ok"] and again["token"] == t1     # refresh, not a new token


def test_release_only_by_holder():
    _, claude, cursor = _two()
    claude.acquire("f.py")
    assert cursor.release("f.py") is False           # not yours
    assert claude.release("f.py") is True
    assert cursor.acquire("f.py")["ok"] is True       # now free


# ------------------------------------------------------------------- fencing token
def test_fencing_rejects_stale_token_after_steal():
    fake, claude, cursor = _two()
    a = claude.acquire("hot.py", ttl=10)
    assert claude.validate_token("hot.py", a["token"]) is True
    fake.advance(11)                                  # claude's lock expires (paused/crashed)
    b = cursor.acquire("hot.py")                      # cursor reclaims -> new, higher token
    assert b["ok"] and b["token"] > a["token"]
    assert claude.validate_token("hot.py", a["token"]) is False   # stale holder rejected
    assert cursor.validate_token("hot.py", b["token"]) is True


# ------------------------------------------------------------------- TTL / awareness
def test_ttl_makes_lock_reclaimable():
    fake, claude, cursor = _two()
    claude.acquire("temp.py", ttl=5)
    fake.advance(6)
    assert claude.holder("temp.py") is None
    assert cursor.acquire("temp.py")["ok"] is True


def test_list_locks_shows_both_agents():
    _, claude, cursor = _two()
    claude.acquire("p1.py"); cursor.acquire("p2.py")
    held = claude.list_locks()
    assert {h["path"] for h in held} == {"p1.py", "p2.py"}
    assert {h["agent"] for h in held} == {"claude", "cursor"}


# ------------------------------------------------------------------- fail-soft
def test_offline_is_failsoft(monkeypatch):
    monkeypatch.setattr(L, "_connect", lambda: None)   # simulate Redis down
    lm = LockManager("claude")                          # auto-connect -> None
    assert lm.online is False
    r = lm.acquire("x.py")
    assert r["ok"] is False and r["online"] is False
    assert lm.list_locks() == []


# ------------------------------------------------------------------- path_conflict
def test_path_conflict_detects_peer_only():
    fake, claude, _ = _two()
    claude.acquire("shared.py")
    assert path_conflict("shared.py", "cursor", client=fake)["conflict"] is True
    assert path_conflict("shared.py", "claude", client=fake)["conflict"] is False   # your own
    assert path_conflict("other.py", "cursor", client=fake)["conflict"] is False    # unlocked


def test_normalize_path_folds_separators_and_case():
    assert normalize_path("./scripts\\Foo.PY") == "scripts/foo.py"
    assert normalize_path("a/b/") == "a/b"


# ------------------------------------------------------------------- hook veto
def test_hook_blocks_edit_on_peer_locked_path(monkeypatch):
    from scripts.hooks import claude_pretooluse as hook
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    monkeypatch.setattr(L, "path_conflict",
                        lambda path, agent, client=None: {"conflict": True, "held_by": "cursor",
                                                          "reason": "locked by cursor"})
    reason = hook._check_write({"tool_input": {"file_path": "scripts/x.py"}})
    assert "locked by cursor" in reason


def test_hook_allows_edit_when_no_agent_id(monkeypatch):
    from scripts.hooks import claude_pretooluse as hook
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    assert hook._check_write({"tool_input": {"file_path": "scripts/x.py"}}) == ""
