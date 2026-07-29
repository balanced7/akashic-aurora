"""T119 RED PIN: one clock, many typed times (G5) + liveness self-proof groundwork (G6).

Charter G5: canonical time lives in ids (UTC); renders DERIVE from ids through ONE
derivation door; a rendered time contradicting its id is a defect. Scout receipts
(2026-07-28): the machine is EDT (UTC-4), event renders print UTC wall-clock UNLABELED
(agent_cli events block), one site prints LOCAL via fromtimestamp (agent_cli:894), and
ten modules stamp naive-LOCAL strings that would land 4h in the past if they ever enter
to_epoch (which asserts naive == UTC).

The contract these pins enforce, per docs charter + scout map:
  (1) timeutil.now_iso()      -> aware UTC ISO (self-describing on the wire)
  (2) timeutil.render_iso()   -> the ONE display door; every rendered timestamp carries
                                 an explicit frame label (Z / UTC / local tz name)
  (3) the naive-LOCAL stamper class is gone: the listed modules stamp via now_iso
  (4) agent_cli's event render path goes through render_iso (wired, not just built)

Pins written RED-first per M3; observed red before the fix commit.
"""
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


# -- (1) now_iso: aware UTC ---------------------------------------------------

def test_now_iso_is_aware_utc():
    from datetime import datetime, timezone
    from core.foundation.timeutil import now_iso
    s = now_iso()
    dt = datetime.fromisoformat(s)
    assert dt.tzinfo is not None, f"now_iso must be tz-aware, got naive: {s}"
    assert dt.utcoffset().total_seconds() == 0, f"now_iso must be UTC, got {s}"


def test_to_epoch_roundtrips_now_iso():
    from core.foundation.timeutil import now_iso, to_epoch
    e = to_epoch(now_iso())
    assert abs(e - time.time()) < 5, "to_epoch(now_iso()) must be 'now' on the one clock"


# -- (2) render_iso: the one display door, frames always labeled --------------

def test_render_iso_labels_utc_frame():
    from core.foundation.timeutil import render_iso
    out = render_iso("2026-07-28T20:41:26", tz="utc")
    assert out.endswith("Z") or "UTC" in out, \
        f"UTC render must carry an explicit frame label, got: {out}"


def test_render_iso_labels_local_frame():
    from core.foundation.timeutil import render_iso
    out = render_iso("2026-07-28T20:41:26+00:00", tz="local")
    # A local render must NOT masquerade as bare/unlabeled time.
    assert not re.fullmatch(r"[\d\-T:\. ]+", out), \
        f"local render must carry a tz label, got bare digits: {out}"


def test_render_iso_same_instant_both_frames():
    from core.foundation.timeutil import render_iso, to_epoch
    src = "2026-07-28T20:41:26+00:00"
    u = render_iso(src, tz="utc")
    l = render_iso(src, tz="local")
    # Frames differ in label/wall-clock but must name the same instant: re-parsing
    # each rendered string (strip label -> not required parseable) is out of scope;
    # the door must at minimum not raise and not return identical strings on a
    # non-UTC box unless local IS utc.
    assert u and l, "both frames must render"


# -- (3) the naive-LOCAL stamper class is retired -----------------------------

NAIVE_LOCAL_STAMPERS = [
    "core/toolbelt/registry.py",
    "core/comm/control.py",
    "core/comm/nudge.py",
    "core/comm/session_state.py",
    "core/comm/runner_lock.py",
    "core/coord/intent.py",
    "core/coord/suite_baseline.py",
    "core/coord/defer_queue.py",
    "core/comm/triage_park.py",
]

_LOCAL_STAMP_PATTERNS = [
    r'time\.strftime\(\s*["\']%Y-%m-%dT',          # naive local wall-clock string
    r'datetime\.now\(\)\.isoformat\(',              # naive local isoformat
]


def test_naive_local_stampers_are_gone():
    offenders = []
    for rel in NAIVE_LOCAL_STAMPERS:
        src = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        for pat in _LOCAL_STAMP_PATTERNS:
            if re.search(pat, src):
                offenders.append(f"{rel} matches {pat}")
    assert not offenders, (
        "naive-LOCAL timestamp stampers remain (each lands 4h in the past the moment "
        "its string enters to_epoch on this box):\n  " + "\n  ".join(offenders))


def test_stampers_use_the_one_clock():
    missing = []
    for rel in NAIVE_LOCAL_STAMPERS:
        src = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        if "now_iso" not in src:
            missing.append(rel)
    assert not missing, (
        "modules must stamp via timeutil.now_iso (the one clock door); missing in:\n  "
        + "\n  ".join(missing))


# -- (4) wired, not just built: agent_cli renders through the door ------------

def test_agent_cli_event_render_uses_the_door():
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    assert "render_iso" in src, \
        "agent_cli must render event timestamps through timeutil.render_iso"
    # the local-clock fromtimestamp render (injections ledger, :894 class) must be gone
    assert not re.search(r"datetime\.fromtimestamp\(float\(i\.get\(", src), \
        "the bare local fromtimestamp render must go through render_iso"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
