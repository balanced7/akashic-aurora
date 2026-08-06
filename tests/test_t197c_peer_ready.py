"""
T197c -- make the peer EXIST: pre-registered acceptance (committed RED, before impl).

The last hop of Sol's front door. T197b made an absent peer visible in one second
instead of thirty minutes; visibility is not a peer. The operator still had to know
WHICH registry tag to launch, from a registry where four tags share one agent_id.

Fenced with deepseek (2026-08-06), which named the failures autolaunch invites:
thundering herd, singleton-lock races, launch storms from a retry loop, and "boots but
never consumes". Its own (D) then said to skip the single-flight lock and the readiness
wait -- contradicting its (B), and the contradiction was put back to it rather than
adopted. This slice keeps both guards, because (B) was right:
  * single-flight is NOT reimplemented here -- the launcher's runner_lock gate already
    checks cross-process and deliberately never HOLDS the lock (the child needs it).
    Re-locking here would starve the very spawn it guards.
  * readiness is polled against attendance(), never slept, so "launched" means a probe
    said ATTENDED -- the one definition under which "boots but never consumes" cannot
    render as success.

Run: py -m pytest tests/test_t197c_peer_ready.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import peer_ready as PR  # noqa: E402

REGISTRY = [
    {"tag": "deepseek", "agent_id": "deepseek"},
    {"tag": "deepseek-build", "agent_id": "deepseek"},
    {"tag": "deepseek-think", "agent_id": "deepseek"},
    {"tag": "deepseek-write", "agent_id": "deepseek"},
    {"tag": "gemini", "agent_id": "gemini"},
    {"tag": "claude_headless", "agent_id": "claude_headless"},
]


class FakeLauncher:
    """Records what it was asked to spawn; never spawns anything."""

    def __init__(self, registry=REGISTRY, ok=True, error=None, pid=4242):
        self._registry, self._ok, self._error, self._pid = registry, ok, error, pid
        self.launched = []

    def registry(self):
        return self._registry

    def launch(self, tag, **kw):
        self.launched.append(tag)
        return ({"ok": True, "pid": self._pid} if self._ok
                else {"ok": False, "error": self._error, "pid": self._pid})


def _attend(monkeypatch, *states):
    """Scripted attendance verdicts, one per call, last value repeating."""
    seq = list(states)

    def fake(peer):
        s = seq.pop(0) if len(seq) > 1 else seq[0]
        return (s == "ATTENDED", s, f"scripted {s}")

    monkeypatch.setattr(PR, "_attending", fake)


# --------------------------------------------------------------------------------------
# The ambiguity it refuses to resolve.
# --------------------------------------------------------------------------------------

# A peer whose agent_id maps to several tags with NO tag named exactly after it. The
# real `deepseek` is deliberately NOT this case -- it ships a tag named `deepseek`, which
# is what makes the common call unambiguous (see the exact-tag test below). This fixture
# is the shape that has no declared default, and it is the one that must refuse to guess.
AMBIGUOUS_REGISTRY = [
    {"tag": "worker-fast", "agent_id": "worker"},
    {"tag": "worker-deep", "agent_id": "worker"},
    {"tag": "gemini", "agent_id": "gemini"},
]


def test_ambiguous_peer_is_returned_as_a_choice_not_guessed():
    """An agent_id with several tags and no tag named after it has no declared default.
    Which configuration answers your question is a decision with an owner, and it is not
    this function -- silently taking the first would be an unowned choice wearing a
    default's clothes."""
    r = PR.resolve_tag("worker", AMBIGUOUS_REGISTRY)
    assert r["ok"] is False and r["reason"] == "ambiguous"
    assert r["candidates"] == ["worker-deep", "worker-fast"], "sorted, so it is stable"
    assert "worker-deep" in r["why"], "the caller must be able to act without a second command"


def test_the_real_deepseek_registry_is_not_ambiguous():
    """The live registry ships four `deepseek` tags AND one named `deepseek` -- so the
    ordinary call resolves without asking the operator anything. Pinned because it is the
    ergonomics claim: the front door must not interrogate you about tags on the common
    path, and a later registry edit that drops the eponymous tag would silently start."""
    assert PR.resolve_tag("deepseek", REGISTRY)["tag"] == "deepseek"


def test_exact_tag_wins_outright():
    """Naming the tag IS the disambiguation -- it must not be re-litigated by agent_id."""
    r = PR.resolve_tag("deepseek-think", REGISTRY)
    assert r["ok"] and r["tag"] == "deepseek-think"


def test_unique_agent_id_resolves():
    assert PR.resolve_tag("gemini", REGISTRY)["tag"] == "gemini"


def test_unknown_peer_says_so_plainly():
    r = PR.resolve_tag("sol", REGISTRY)
    assert r["ok"] is False and r["reason"] == "no_tag" and r["candidates"] == []


def test_resolve_tag_is_pure():
    """No launcher, no bus, no clock -- so the ambiguity law is testable in isolation
    and cannot drift behind an I/O failure."""
    before = list(REGISTRY)
    PR.resolve_tag("deepseek", REGISTRY)
    assert REGISTRY == before


# --------------------------------------------------------------------------------------
# What it does, and refuses to do, about launching.
# --------------------------------------------------------------------------------------

def test_an_attending_peer_is_never_relaunched(monkeypatch):
    """The cheapest correct outcome, and the guard against a retry loop turning into a
    launch storm (deepseek's B): if it is up, nothing is spawned."""
    _attend(monkeypatch, "ATTENDED")
    lz = FakeLauncher()
    out = PR.ensure_peer("deepseek", launcher=lz)
    assert out["action"] == "already_attending" and out["attending"] is True
    assert lz.launched == [], "an attending peer must not be respawned"


def test_ambiguous_peer_spawns_nothing(monkeypatch):
    """An unresolved choice must not become a spawned process."""
    _attend(monkeypatch, "UNATTENDED")
    lz = FakeLauncher(registry=AMBIGUOUS_REGISTRY)
    out = PR.ensure_peer("worker", launcher=lz)
    assert out["action"] == "ambiguous" and lz.launched == []
    assert out["candidates"] == ["worker-deep", "worker-fast"]


def test_launch_then_attended_reports_launched(monkeypatch):
    _attend(monkeypatch, "UNATTENDED", "ATTENDED")
    lz = FakeLauncher()
    out = PR.ensure_peer("deepseek-think", launcher=lz, wait_s=5, poll_s=0,
                         sleep=lambda s: None)
    assert out["action"] == "launched" and out["attending"] is True
    assert lz.launched == ["deepseek-think"] and out["pid"] == 4242


def test_boots_but_never_consumes_is_reported_not_hidden(monkeypatch):
    """DEEPSEEK'S NAMED FAILURE MODE, pinned. A fixed sleep would have called this a
    success; polling the verdict is what makes it impossible to."""
    _attend(monkeypatch, "UNATTENDED")
    lz = FakeLauncher()
    out = PR.ensure_peer("gemini", launcher=lz, wait_s=0, poll_s=0, sleep=lambda s: None)
    assert out["action"] == "never_attended" and out["attending"] is False
    assert lz.launched == ["gemini"]
    assert "boots without consuming" in out["why"] or "still be booting" in out["why"]


def test_a_launcher_refusal_is_a_state_not_a_crash(monkeypatch):
    """The singleton gate declining to spawn a duplicate is CORRECT behaviour. It must
    read as a reportable state, never as an error to route around -- routing around it
    is precisely the duplicate-spawn bug the gate exists to prevent."""
    _attend(monkeypatch, "UNATTENDED")
    lz = FakeLauncher(ok=False, error="'gemini' already has a live runner (pid 99)")
    out = PR.ensure_peer("gemini", launcher=lz, wait_s=0, sleep=lambda s: None)
    assert out["action"] == "launch_refused" and out["attending"] is False
    assert "live runner" in out["why"]


def test_no_single_flight_lock_is_reimplemented():
    """The launcher checks runner_lock cross-process and deliberately never HOLDS it --
    a lock acquired here would starve the child that needs it. deepseek's (D) advised
    skipping single-flight entirely; the resolution was to USE the existing one, not to
    build a second.

    READ AS NAMES, NOT TEXT -- T171's K6 lesson, which this pin's first cut re-learned the
    hard way: a raw-source scan makes the module's own prose part of its input, so the
    docstring EXPLAINING that single-flight is delegated to runner_lock falsified the law
    about not using runner_lock. Stripping docstrings via AST dissolves the reflexivity
    instead of patching this one instance of it.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(PR))
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            referenced.update((node.module or "").split("."))
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)

    for forbidden in ("runner_lock", "acquire", "setnx", "SETNX", "lock"):
        assert forbidden not in referenced, (
            f"{forbidden}: single-flight belongs to the launcher, which checks the lock "
            f"cross-process and deliberately never holds it")


def test_never_raises_when_everything_is_broken(monkeypatch):
    """A door that crashes the ask it was meant to help is worse than no door."""
    _attend(monkeypatch, "UNATTENDED")

    class Broken:
        def registry(self):
            raise RuntimeError("redis down")

    out = PR.ensure_peer("deepseek", launcher=Broken())
    assert out["action"] == "launch_refused" and out["attending"] is False
    assert "registry unreadable" in out["why"]


def test_blind_list_is_non_empty_and_names_the_lane_gap():
    """ATTENDED proves a process beats, never that it reads the lane this ask rode.
    That gap is real and separate (a healthy seat CAN read the wrong lane), so it is
    confessed rather than implied."""
    out = PR.BLIND
    assert out and any("lane" in b for b in out)
