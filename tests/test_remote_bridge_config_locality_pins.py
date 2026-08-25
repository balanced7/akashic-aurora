"""Pins: the bridge route config is INSTANCE-LOCAL, not shared truth.

Found by Zadkiel (Serge's seat), 2026-08-24: `state/coord/remote_bridge.json` was committed
carrying a peer.url pointing at ONE peer's tailnet address. Every instance that pulls gets
another instance's route, and every instance that fills in its own conflicts on the next
merge — "exactly like security/acl.json did before t384", which is precisely the right
comparison, because that is the same class and this house already solved it once.

The defect is mine and it is small in code and large in kind: A ROUTE IS A FACT ABOUT ONE
MACHINE'S RELATIONSHIP TO ANOTHER, and committing it asserts that relationship is true for
everyone who clones. Two Auroras each correctly configured will always disagree about this
file, so a shared copy guarantees a conflict rather than risking one.

The ceremony is the one already established at t384: the live file is gitignored per-machine
truth; a tracked `.example.json` carries the SHAPE with no instance values in it.

These pins run against git's index, not the working tree — the distinction that mattered all
night, and the only one that can catch this class. A pin that read the working tree would
pass happily on the machine where the mistake was made.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

LIVE = "state/coord/remote_bridge.json"
EXAMPLE = "state/coord/remote_bridge.example.json"


def _tracked(path: str) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                       cwd=REPO, capture_output=True, text=True)
    return r.returncode == 0


def test_live_route_config_is_not_tracked():
    """The instance-local half. If this is tracked, every pull hands one fleet another
    fleet's route and every locally-correct config becomes a merge conflict."""
    assert not _tracked(LIVE), (
        f"{LIVE} is tracked by git. It holds THIS machine's peer route — instance-local "
        f"truth, same class as security/acl.json (t384). Untrack it: "
        f"`git rm --cached {LIVE}` and keep the tracked template instead.")


def test_a_tracked_template_exists():
    """Absent-is-not-broken has a limit: a newcomer needs the SHAPE even though they must
    not inherit the values."""
    assert _tracked(EXAMPLE), f"{EXAMPLE} must be tracked so a fresh clone learns the shape"


def test_the_template_carries_no_instance_values():
    """The template must be inert. A peer url or a peer name baked into it is the original
    defect wearing a different filename — and it would be COPIED into every new instance,
    which is worse than the conflict it was meant to prevent."""
    raw = subprocess.run(["git", "show", f"HEAD:{EXAMPLE}"], cwd=REPO,
                         capture_output=True, text=True).stdout
    cfg = json.loads(raw)
    peer = cfg.get("peer") or {}
    assert not (peer.get("url") or "").strip(), (
        f"the tracked template ships a peer.url ({peer.get('url')!r}) — that is one "
        f"machine's route asserted as everyone's")
    for banned in ("100.", "127.0.0.1", "localhost", "http"):
        assert banned not in json.dumps(peer), (
            f"the template's peer block contains {banned!r} — an address of any kind is an "
            f"instance value")


def test_the_reader_still_works_with_no_config_at_all():
    """Absent config must be a configuration STATE, not a crash and not a guess — the
    inert-until-keyed property the whole bridge leans on."""
    from core.comm import remote_relay as RR
    import os
    old = os.environ.pop("AKASHIC_REMOTE_BRIDGE_PEER_URL", None)
    try:
        cfg = RR._config()
        assert isinstance(cfg, dict), "a missing/unreadable config must read as {}, never raise"
    finally:
        if old is not None:
            os.environ["AKASHIC_REMOTE_BRIDGE_PEER_URL"] = old


def test_env_override_beats_the_file():
    """The escape hatch that makes per-instance routing possible without ANY file edit —
    which is what a service or a container needs."""
    from core.comm import remote_relay as RR
    import os
    old = os.environ.get("AKASHIC_REMOTE_BRIDGE_PEER_URL")
    os.environ["AKASHIC_REMOTE_BRIDGE_PEER_URL"] = "https://override.invalid/xfer"
    try:
        assert RR.peer_url() == "https://override.invalid/xfer"
    finally:
        if old is None:
            os.environ.pop("AKASHIC_REMOTE_BRIDGE_PEER_URL", None)
        else:
            os.environ["AKASHIC_REMOTE_BRIDGE_PEER_URL"] = old
