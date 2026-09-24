"""A runner seat can FETCH -- the wiring designed 2026-09-01 and landed 2026-09-24.

THE INCIDENT. Daniil asked a seat on a deepseek runner to look something up. It reported back
that it found nothing. The seat had no fetch tool at all: `web_fetch` appeared ZERO times in
core/comm/toolbox.py, which is the entire tool surface a runner seat gets. It could search and
it could never READ, and nothing in its tool list said the fetch door existed somewhere else.

THE EVIDENCE THAT MADE IT UNDENIABLE. core/web/door.py writes a receipt on every path -- success,
HTTPError, and the generic exception branch. In 171 receipts, exactly two seats had ever appeared:

    claude       162
    dsh_agent      9

No kimi. No deepseek. No sol. Not once, in three weeks of the door existing. That silence was not
"the seats did not need the web"; it was "the seats could not reach it."

WHY IT SAT. The wiring was designed on 2026-09-01, in the same session that built the door. That
session was an unattended Discord !spawn and was write-blocked, so the package was handed off and
never applied. check_door_parity recorded the state honestly -- `"web_fetch": "mcp_only"` with the
comment "ToolBox wiring lands with the Heimdall fence" -- so this was a KNOWN, TRACKED gap, not an
unguarded hole. The manifest did its job; the landing simply never happened.

WHAT THESE PINS PROTECT, beyond "the method exists":

  1. THE RECEIPT NAMES THE SEAT. Passing seat= through is the entire point of the ledger. A
     fetch that receipts as "unknown" re-creates the blindness this fixes.
  2. THE RANGE TRAVELS. The door's discipline is "range API over silent truncation". A wrapper
     that renders only the text re-introduces the silent cut one layer up -- the wrapper-narrowing
     defect this session found four times across two modules in one night.
  3. A FAILURE IS NOT AN ABSENCE. A failed fetch must be impossible to mistake for an empty page.
     That confusion is exactly what produced the incident: "nothing back" got reported as "nothing
     there".

Run::

    py -m pytest tests/test_toolbox_web_fetch_reaches_the_door.py -q
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _toolbox(agent_id="test-seat"):
    from core.comm.toolbox import ToolBox
    tb = ToolBox(ROOT, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *a, **k: True)
    tb.agent_id = agent_id
    return tb


def test_web_fetch_is_in_the_runner_tool_surface():
    """THE PIN THE INCIDENT NEEDED. Not "the door exists" -- the door existed the whole time.
    The question is whether a runner seat can SEE it."""
    from core.comm.toolbox import TOOLS
    names = {t["function"]["name"] for t in TOOLS}
    assert "web_fetch" in names, (
        "a runner seat has no fetch tool. It can search and never read, and nothing in its "
        "surface says the fetch door is reachable elsewhere -- which is how 'I have no tool' "
        "gets reported to an operator as 'I found nothing'."
    )


def test_the_spec_warns_that_fetched_text_is_untrusted():
    """Fetched content is a stranger's writing entering a model's context. The tool description
    is the only place the seat is told so BEFORE it calls."""
    from core.comm.toolbox import TOOLS
    spec = next(t for t in TOOLS if t["function"]["name"] == "web_fetch")
    desc = spec["function"]["description"].lower()
    assert "untrusted" in desc, "the spec does not tell the seat the content is untrusted"
    assert "instruction" in desc, (
        "the spec does not tell the seat that fetched text may try to instruct it -- the "
        "indirect-prompt-injection surface, unnamed at the one place the seat reads before calling"
    )


def test_a_non_url_is_refused_and_says_which_door_to_use():
    tb = _toolbox()
    out = tb.web_fetch("core/web/door.py")
    assert out.startswith("ERROR"), f"a filesystem path was not refused: {out[:120]!r}"
    assert "read_file" in out, "the refusal does not name the door that WOULD work"
    out2 = tb.web_fetch("")
    assert out2.startswith("ERROR"), "an empty url was not refused"


def test_a_failed_fetch_can_never_read_as_an_empty_page():
    """THE INCIDENT'S OWN SHAPE. 'Nothing back' became 'nothing there'. A failure must say so
    loudly enough that a seat cannot report the subject as absent on the strength of it."""
    tb = _toolbox()
    out = tb.web_fetch("https://this-host-does-not-exist.invalid")
    assert "FETCH FAILED" in out, f"a failure did not announce itself: {out[:160]!r}"
    low = out.lower()
    assert "not an empty page" in low and "absent" in low, (
        "the failure does not distinguish itself from an empty page / an absent subject, which "
        "is the exact confusion that produced this task"
    )


def test_the_range_survives_the_wrapper(monkeypatch):
    """The door returns total_chars/offset/returned so a caller can page. If the ToolBox renders
    only the text, the silent truncation the door refuses is re-introduced by its own wrapper.

    NOTE ON THE DOUBLE, because the first draft of this pin did not actually substitute: the
    method does `from core.web import door`, which binds the ATTRIBUTE on the package, so
    swapping sys.modules["core.web.door"] changed nothing and the test silently hit the real
    network (and failed on a 404 -- loudly, which is the only reason I noticed). Patch the real
    symbol instead; this also keeps the pin honest about the import path the code actually uses.
    """
    tb = _toolbox()
    import core.web.door as real_door

    def _fake_fetch(url, **kw):
        return {"ok": True, "url": url, "final_url": url, "fetched_at": "2026-09-24T00:00:00Z",
                "status": 200, "content_type": "text/html", "sha256": "a" * 64, "bytes": 10,
                "cache": "miss-filled", "is_pdf": False,
                "cleaned": {"total_chars": 5000, "offset": 0, "returned": 80, "text": "x" * 80},
                "raw_available": True}

    monkeypatch.setattr(real_door, "fetch", _fake_fetch)
    out = tb.web_fetch("https://example.com/long", limit=80)

    assert "5000" in out, "total_chars did not survive the wrapper -- the reader cannot tell there is more"
    assert "MORE REMAINS" in out, "the wrapper did not say that the page continues"
    assert "offset=80" in out, "the wrapper said there was more but not how to reach it"


def test_the_receipt_names_the_seat_that_fetched():
    """The ledger's whole purpose. A fetch that receipts as 'unknown' rebuilds the blindness:
    three weeks of receipts showed two seats because the others had no door, and a receipt that
    cannot name its caller would have hidden the fix as well as the defect."""
    tb = _toolbox(agent_id="pin-seat")
    receipts = ROOT / "state" / "coord" / "web_fetch_receipts.jsonl"
    before = receipts.read_text(encoding="utf-8").count("\n") if receipts.exists() else 0

    out = tb.web_fetch("https://this-host-does-not-exist.invalid")
    assert "FETCH FAILED" in out

    lines = [l for l in receipts.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) > before, "a failed fetch wrote NO receipt -- the error path is unaudited"
    row = json.loads(lines[-1])
    assert row.get("seat") == "pin-seat", (
        f"the receipt names {row.get('seat')!r}, not the calling seat -- attribution is the "
        f"entire point of this ledger"
    )
