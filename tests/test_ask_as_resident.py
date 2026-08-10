"""T261 RED -- the caught-up resident branch: tier-1 fan-out, tier riding the finding.

DANIIL'S ASK, 2026-08-09, verbatim:

    "I want us to have levels to fan outs, lowest rank is the pure fanout ask. an advanced
     fanout would be fresh resident agents that have caught up start tackling the issue...
     their continuity and persistance mean that you don't have to explain the risks and
     incorrect assumptions every single time"

WHAT `ask --as <resident>` MEANS, and what it must not mean:

  THE BRANCH IS SPAWNED CARRYING ITS IDENTITY. The registry block (callsign + receipts) and a
  catch-up pack of the resident's OWN archive lessons relevant to the prompt ride the system
  context. The brief stops re-carrying the standing premises -- that is the burden his
  directive names. The pack comes FROM THE STORE, which is why this does not violate ask.py's
  own "no persistent memory" doctrine: memory that crosses invocations lives where the whole
  fleet can inspect it, and the branch READS it on the way in. (P2, P5.)

  THE TIER RIDES THE FINDING. Eight caught-up residents agreeing is NOT eight blind branches
  agreeing, and a report must not render them identically -- the T254 defect one level up.
  Every outcome carries tier ("blind" | "resident") and, for tier 1, the designation. (P3, P4.)

  A NON-RESIDENT CANNOT CLAIM THE TIER. --as with no ratified designation refuses BEFORE any
  model call -- a tier asserted without a registry entry is exactly the self-declared-identity
  class (T255). (P1.)

  TIER 0 STAYS THE CONTROL ARM. No flag, no injection, no behavior change beyond the honest
  tier stamp -- it is the only arm whose agreement is uncorrelated. (P4.)

STANDING CAVEAT, kimi's verdict, carried not closed: persistence is UNMEASURED as a
correctness cause. This slice makes tier 1 EXPRESSIBLE and LABELLED; it claims nothing about
it being better, and it is precisely the harness the kill-drill needs.

Run: py -m pytest tests/test_ask_as_resident.py -q
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


def _seed_lesson(agent, experiment, tried):
    rc, out, err = run("learn", agent, "--experiment", experiment,
                       "--tried", tried, "--result", "t261 seed")
    assert rc == 0, f"seed {experiment} failed: {err or out}"
    return experiment


# --------------------------------------------------------------- a hermetic fake client

class _FakeCompletions:
    """Captures every request; answers canned. The pin reads what WOULD go on the wire."""
    def __init__(self, log):
        self._log = log

    def create(self, **kw):
        self._log.append(kw)

        class _Msg:                    # the minimal shape ask() reads back
            content = "canned answer"
            reasoning_content = None

        class _Choice:
            message = _Msg()
            finish_reason = "stop"

        class _Usage:
            prompt_tokens = 10
            completion_tokens = 5
            total_tokens = 15
            completion_tokens_details = None

        class _Resp:
            choices = [_Choice()]
            usage = _Usage()
            model = kw.get("model", "fake")
            system_fingerprint = "fp_fake"

        return _Resp()


class _FakeClient:
    def __init__(self):
        self.requests = []
        self.chat = type("chat", (), {"completions": _FakeCompletions(self.requests)})()


@pytest.fixture(scope="module")
def resident_kimi():
    """A RATIFIED resident with topical lessons of its own, plus a decoy by another agent."""
    from core.fleet import residents as R
    receipt = _seed_lesson("kimi", "t261_receipt_kimi", "the receipt that earned the name")
    _seed_lesson("kimi", "t261_kimi_cursor_lesson",
                 "cursor divergence: drain the lane you armed before re-arming")
    _seed_lesson("claude", "t261_claude_cursor_decoy",
                 "cursor divergence: a decoy lesson by a DIFFERENT author")
    R.nominate(nominee="kimi", callsign="Navi", receipts=[receipt], by="daniil_pin")
    R.ratify(nominee="kimi", callsign="Navi", by="daniil_pin")
    return "kimi"


# --------------------------------------------------------------- P1: the tier is guarded

def test_p1_a_non_resident_cannot_claim_the_tier_and_no_call_is_made(resident_kimi):
    from core.comm.ask import ask
    fake = _FakeClient()
    out = ask("any question", as_resident="unregistered_seat", client=fake)
    assert not out.ok, "an unregistered --as must refuse"
    why = str(out.why or "").lower()
    assert "resident" in why, "the refusal must say WHY: not a resident"
    assert fake.requests == [], \
        "the refusal must happen BEFORE any model call -- a helper must not be billed for it"


# --------------------------------------------------------------- P2: identity rides the wire

def test_p2_the_system_context_carries_callsign_and_own_lessons(resident_kimi):
    from core.comm.ask import ask
    fake = _FakeClient()
    out = ask("how do I handle cursor divergence on re-arm?",
              as_resident="kimi", client=fake)
    assert out.ok, f"resident ask must succeed: {out.why}"
    assert len(fake.requests) == 1
    msgs = fake.requests[0]["messages"]
    system = " ".join(m.get("content", "") for m in msgs if m.get("role") == "system")
    assert "Navi" in system, "the callsign must ride the system context -- the branch is SPAWNED named"
    assert "t261_kimi_cursor_lesson" in system, \
        "the catch-up pack must carry the resident's own topical lesson"


def test_p5_the_pack_contains_only_the_residents_lessons(resident_kimi):
    from core.comm.ask import ask
    fake = _FakeClient()
    ask("how do I handle cursor divergence on re-arm?", as_resident="kimi", client=fake)
    system = " ".join(m.get("content", "") for m in fake.requests[0]["messages"]
                      if m.get("role") == "system")
    assert "t261_claude_cursor_decoy" not in system, \
        "another agent's lesson in the pack would make the resident a fleet-corpus reader -- " \
        "precisely not the point (T260's scope exists for this)"


# --------------------------------------------------------------- P3/P4: the tier stamp

def test_p3_a_resident_outcome_carries_tier_and_designation(resident_kimi):
    from core.comm.ask import ask
    out = ask("q", as_resident="kimi", client=_FakeClient())
    assert out.detail.get("tier") == "resident"
    assert "Navi" in str(out.detail.get("designation") or ""), \
        "the finding must carry WHO answered -- convergence claims must be able to state their spread"


def test_p4_a_blind_ask_is_stamped_blind_and_carries_no_identity(resident_kimi):
    from core.comm.ask import ask
    fake = _FakeClient()
    out = ask("q", client=fake)
    assert out.ok
    assert out.detail.get("tier") == "blind", \
        "tier 0 must be LABELLED too -- unlabelled control arms stop being control arms"
    system = " ".join(m.get("content", "") for m in fake.requests[0]["messages"]
                      if m.get("role") == "system")
    assert "Navi" not in system and "t261_kimi_cursor_lesson" not in system, \
        "a blind branch must stay blind -- injection into tier 0 destroys the only uncorrelated arm"


# --------------------------------------------------------------- P6: the door refuses early

def test_p6_cli_as_unknown_resident_refuses_before_any_network(resident_kimi):
    """The CLI refusal path must trigger on the registry read, never reaching the API --
    safe to run offline, and the proof is the nonzero exit with the reason named."""
    rc, out, err = run("ask", "any question", "--as", "unregistered_seat")
    text = (out + err).lower()
    assert rc != 0, "an unknown resident on the CLI must exit nonzero"
    assert "resident" in text, "and say why"
