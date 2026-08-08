"""T237 RED: `ask --json` returns before the evidence notice, so machine callers are blind.

FOUND BY BEING THE MACHINE CALLER. A blind-draft experiment tonight was silently compromised
by a clipped file (`bus.py` at 40000 of 80052 chars, hiding `cursor:lane:` at line 1201), and
I scored the resulting miss as a reasoning failure until I checked. The notice built to
prevent exactly that never reached me.

TWO SEPARATE GAPS, and I only knew about the first:

  1. the notice goes to STDERR, and my probe captured stdout only;
  2. AND THE `--json` BRANCH RETURNS BEFORE THE NOTICE IS EMITTED AT ALL -- so it fires on
     NEITHER channel for a programmatic caller.

Verified: `ask --with core/comm/bus.py --json` produced `context.truncated == True` in the
payload and `'CLIPPED' in stderr == False`.

That is my own T218 reaching some call sites and not all -- the same shape as T219 (a fix
wired into one of two harnesses) and T220 (a pointer fixed at one of two clip sites), both of
which I found in other people's code today.

THE FIX FOR A MACHINE READER IS NOT A STDERR LINE. A JSON consumer does not read prose; it
reads keys. The signal already exists at `context.truncated`, but a caller has to KNOW that
nested key to find it, and none of my four probes tonight did. A top-level `warnings` array
is discoverable by anyone who prints the payload once.

Same law as the lesson this run produced: a warning is loud only on a channel the reader is
actually listening to -- and for a machine, the channel is a field.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _ask_json(*extra):
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "ask", "--json", *extra, "reply with just: OK"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300)
    out = r.stdout or ""
    i = out.find("{")
    return (json.loads(out[i:]) if i >= 0 else {}), r


def test_a_json_caller_gets_a_discoverable_warning_when_evidence_was_clipped():
    """THE PIN. bus.py is ~80k chars against a 40k budget, so this always clips."""
    d, _ = _ask_json("--with", "core/comm/bus.py")
    assert (d.get("context") or {}).get("truncated") is True, "precondition: it clipped"
    warnings = d.get("warnings")
    assert warnings, (
        "the payload carries context.truncated but no top-level `warnings` -- a machine "
        "caller must know a nested key to learn its evidence was incomplete, and four "
        "probes tonight did not")
    joined = " ".join(str(w) for w in warnings).lower()
    assert "clip" in joined or "partial" in joined
    assert "bus.py" in joined, "a warning that does not name the file is unactionable"


def test_a_clean_run_carries_no_warnings():
    """Noise on clean runs gets filtered out mentally, and that is how the real one is missed.
    An empty or absent list on a clean call, never a placeholder."""
    d, _ = _ask_json("--with", "core/outcome.py")
    assert (d.get("context") or {}).get("truncated") is False, "precondition: fits the budget"
    assert not d.get("warnings")


def test_the_human_path_still_prints_to_stderr():
    """REGRESSION. The machine channel is ADDITIVE -- T218's stderr notice is what a person
    reads, and gaining a field must not cost the line."""
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "ask", "--with", "core/comm/bus.py",
         "reply with just: OK"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300)
    assert "CLIPPED" in (r.stderr or ""), "the human notice regressed"
