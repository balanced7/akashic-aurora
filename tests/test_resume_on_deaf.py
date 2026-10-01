"""S2 resume-on-deaf pins (T420, 2026-10-01). Daniel's ladder property (1): a deaf session is
re-opened by the house, not by a human. Hermetic: no daemon, no bus, no credential, no launch
-- the actuator takes an injected Popen and a fake PATH, the records live in tmp_path.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import resume_on_deaf as rod
from core.comm import wake_seat as ws

AGENT = "tresume"
NOW = 1_700_000_000.0


# ---------------------------------------------------------------- expected-up record
def test_expected_record_is_declared_by_the_launcher_and_retracted(tmp_path):
    base = str(tmp_path / "exp")
    assert rod.expected_sessions(AGENT, base) == []
    assert rod.declare_expected(AGENT, "s1", by="harness", cwd="E:/x", base=base, now=NOW)
    recs = rod.expected_sessions(AGENT, base)
    assert len(recs) == 1 and recs[0]["session_id"] == "s1" and recs[0]["by"] == "harness"
    assert rod.declare_expected(AGENT, "s1", base=base)          # idempotent
    assert len(rod.expected_sessions(AGENT, base)) == 1
    assert rod.retract_expected(AGENT, "s1", base) is True
    assert rod.retract_expected(AGENT, "s1", base) is False      # gone: a measured absence
    assert rod.declare_expected(AGENT, "", base=base) is False   # no session, no record


# ---------------------------------------------------------------- the decision table
@pytest.mark.parametrize("kw,verdict,needle", [
    (dict(expected=False, alive_age_min=30, harness_armed=False, token_ok=True), "hold", "not expected"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, tombstoned=True, token_ok=True), "hold", "tombstoned"),
    (dict(expected=True, alive_age_min=30, harness_armed=True, token_ok=True), "hold", "reachable"),
    (dict(expected=True, alive_age_min=None, harness_armed=False, token_ok=True), "hold", "no activity marker"),
    (dict(expected=True, alive_age_min=4, harness_armed=False, token_ok=True), "hold", "grace"),
    (dict(expected=True, alive_age_min=30 * 60, harness_armed=False, token_ok=True), "hold", "stale"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, token_ok=True, failures=3), "hold", "breaker"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, token_ok=True, last_resume_age_min=5), "hold", "cooldown"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, token_ok=False), "hold", "no credential"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, token_ok=True), "resume", "deaf 30m"),
    (dict(expected=True, alive_age_min=30, harness_armed=False, token_ok=True, last_resume_age_min=45, failures=2), "resume", "deaf"),
])
def test_resume_decision_names_every_hold(kw, verdict, needle):
    v, reason = rod.resume_decision(**kw)
    assert v == verdict and needle in reason, (v, reason)


# ---------------------------------------------------------------- argv + prompt
def test_resume_argv_is_resume_first_with_the_arm_grant():
    argv = rod.resume_argv(["C:/claude.exe"], "sid-123", "PROMPT", model_flag=["--model", "x"],
                           permission_flags=["--permission-mode", "acceptEdits"])
    assert argv[:3] == ["C:/claude.exe", "--model", "x"]
    assert "-p" in argv and argv[argv.index("-p") + 1] == "PROMPT"
    assert "--resume" in argv and argv[argv.index("--resume") + 1] == "sid-123"
    assert argv[-2:] == ["--permission-mode", "acceptEdits"]


def test_resume_prompt_forbids_arming_and_names_the_operator_reply_path():
    p = rod.resume_prompt("claude", "deaf 30m")
    assert "Do NOT arm a wake listener" in p and "--to daniil" in p and "boot claude" in p


# ---------------------------------------------------------------- the actuator (fake launch)
class _Launch:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        return object()


def test_trigger_resume_launches_detached_with_token_and_records_a_receipt(tmp_path):
    launch = _Launch()
    ok, detail = rod.trigger_resume(AGENT, "sid-abc", reason="deaf 30m",
                                    which=lambda n: "C:/fake/claude.cmd", popen=launch,
                                    env={"PATH": "x"}, token="tok-123", logged_in=None,
                                    receipts_base=str(tmp_path / "r"), log_dir=str(tmp_path / "logs"),
                                    now=NOW)
    assert ok and "resumed sid-abc" in detail
    argv, kw = launch.calls[0]
    assert "--resume" in argv and argv[argv.index("--resume") + 1] == "sid-abc"
    assert kw["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "tok-123" and kw["env"]["AKASHIC_AGENT_ID"] == AGENT
    assert os.path.isfile(kw["stdout"].name)
    last, failures = rod.resume_history(AGENT, "sid-abc", str(tmp_path / "r"), now=NOW + 60)
    assert last == pytest.approx(1.0) and failures == 0


def test_trigger_resume_refuses_at_t0_with_no_credential_and_launches_nothing(tmp_path):
    launch = _Launch()
    ok, detail = rod.trigger_resume(AGENT, "sid-abc", reason="deaf", which=lambda n: "C:/fake/claude",
                                    popen=launch, env={}, token="", logged_in=False,
                                    receipts_base=str(tmp_path / "r"), log_dir=str(tmp_path / "logs"), now=NOW)
    assert not ok and "no credential" in detail and launch.calls == []
    _, failures = rod.resume_history(AGENT, "sid-abc", str(tmp_path / "r"), now=NOW)
    assert failures == 1


def test_trigger_resume_fails_open_on_unknown_login_state(tmp_path):
    launch = _Launch()
    ok, _ = rod.trigger_resume(AGENT, "sid-x", reason="deaf", which=lambda n: "C:/fake/claude",
                               popen=launch, env={}, token="", logged_in=None,
                               receipts_base=str(tmp_path / "r"), log_dir=str(tmp_path / "logs"), now=NOW)
    assert ok and len(launch.calls) == 1                 # unknown is not 'no'


# ---------------------------------------------------------------- maybe_resume over live facts
def _alive(tmp, sid, age_min):
    with open(ws.activity_marker_path(AGENT, sid, str(tmp)), "w") as f:
        f.write(str(NOW - age_min * 60))


def test_maybe_resume_holds_without_expected_record_and_resumes_when_deaf(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path / "nosecrets"))
    exp, rcp = str(tmp_path / "exp"), str(tmp_path / "r")
    calls = []

    def fake_trigger(agent, sid, *, reason, **kw):
        calls.append((agent, sid, reason))
        rod.record_resume(agent, sid, True, "fake", base=rcp, now=kw.get("now"))
        return True, "fake"

    _alive(tmp_path, "s9", 30)
    v, r = rod.maybe_resume(AGENT, "s9", now=NOW, tmp=str(tmp_path), expected_base=exp,
                            receipts_base=rcp, token="tok", trigger=fake_trigger)
    assert v == "hold" and "not expected" in r and calls == []
    rod.declare_expected(AGENT, "s9", base=exp, now=NOW)
    v, r = rod.maybe_resume(AGENT, "s9", now=NOW, tmp=str(tmp_path), expected_base=exp,
                            receipts_base=rcp, token="tok", trigger=fake_trigger)
    assert v == "resume" and calls == [(AGENT, "s9", "deaf 30m, expected-up, credential present")]
    v, r = rod.maybe_resume(AGENT, "s9", now=NOW + 60, tmp=str(tmp_path), expected_base=exp,
                            receipts_base=rcp, token="tok", trigger=fake_trigger)
    assert v == "hold" and "cooldown" in r and len(calls) == 1
    v, r = rod.maybe_resume(AGENT, "s9", now=NOW, tmp=str(tmp_path), expected_base=exp,
                            receipts_base=str(tmp_path / "r2"), token="", logged_in=False,
                            trigger=fake_trigger)
    assert v == "hold" and "no credential" in r


# ---------------------------------------------------------------- R4 falsifier (Heimdall): launched, then died
class _Proc:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


def test_a_resume_that_launches_then_dies_early_is_a_failed_receipt_the_breaker_counts(tmp_path):
    rcp = str(tmp_path / "r")
    rod.in_flight.clear()
    proc = _Proc(code=None)
    ok, _ = rod.trigger_resume(AGENT, "sid-dead", reason="deaf", which=lambda n: "C:/fake/claude",
                               popen=lambda *a, **k: proc, env={}, token="tok",
                               receipts_base=rcp, log_dir=str(tmp_path / "logs"), now=NOW)
    assert ok and "sid-dead" in rod.in_flight
    assert rod.settle_in_flight(AGENT, now=NOW + 5) == [("sid-dead", "pending")]
    proc.code = 1                                                  # the child died at 16 s
    assert rod.settle_in_flight(AGENT, now=NOW + 16) == [("sid-dead", "dead")]
    _, failures = rod.resume_history(AGENT, "sid-dead", rcp, now=NOW + 20)
    assert failures == 1 and "sid-dead" not in rod.in_flight
    v, _ = rod.resume_decision(expected=True, alive_age_min=30, harness_armed=False, token_ok=True,
                               last_resume_age_min=0.1, failures=failures)
    assert v == "hold"                                            # cooldown now, breaker after three


def test_a_resume_still_running_past_the_floor_is_alive_and_leaves_the_registry(tmp_path):
    rcp = str(tmp_path / "r")
    rod.in_flight.clear()
    rod.trigger_resume(AGENT, "sid-live", reason="deaf", which=lambda n: "C:/fake/claude",
                       popen=lambda *a, **k: _Proc(code=None), env={}, token="tok",
                       receipts_base=rcp, log_dir=str(tmp_path / "logs"), now=NOW)
    assert rod.settle_in_flight(AGENT, now=NOW + 31) == [("sid-live", "alive")]
    _, failures = rod.resume_history(AGENT, "sid-live", rcp, now=NOW + 40)
    assert failures == 0 and rod.in_flight == {}


def test_resume_env_seeds_the_work_lane(tmp_path):
    launch = _Launch()
    rod.in_flight.clear()
    rod.trigger_resume(AGENT, "sid-env", reason="deaf", which=lambda n: "C:/fake/claude",
                       popen=launch, env={}, token="tok", receipts_base=str(tmp_path / "r"),
                       log_dir=str(tmp_path / "logs"), now=NOW)
    env = launch.calls[0][1]["env"]
    assert env["BIFROST_CONSUME_LANE"] == "work" and env["BIFROST_WAKE_LANE"] == "work"
