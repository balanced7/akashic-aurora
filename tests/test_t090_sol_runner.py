"""T090 runner pins -- OFFLINE (no network, no key, no Redis writes).

Covers the two fence-order hardening slices landed 2026-07-17 (continuity header,
RB-23 gate wiring) plus the build_parser extraction that made the runner constructible
under test. The RB-23 machinery itself (bounce_promise/content_floor_check) is the
deepseek runner's genus implementation -- these pins prove SOL'S wiring of it: promise
bounces once, markers confess in sol's name, clean answers pass untouched.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bifrost_runner_sol as R

_NOOP_PULSE = lambda agent, reason, **kw: None


# ---- build_parser extraction ------------------------------------------------------------------

def test_build_parser_defaults_offline():
    args = R.build_parser().parse_args([])
    assert args.agent == "sol"
    assert args.model == R.DEFAULT_MODEL
    assert args.effort == R.DEFAULT_EFFORT
    assert not args.agentic and not args.once
    assert not args.allow_write and not args.allow_exec
    assert args.ignore_source == []
    # continuity flags default None -- main() resolves them to the conventional path
    assert args.summary_file is None and args.inject_summary is None


def test_build_parser_full_seat_flags():
    args = R.build_parser().parse_args(["--agentic", "--allow-write", "--allow-exec",
                                        "--ignore-source", "discord",
                                        "--effort", "high", "--once"])
    assert args.agentic and args.allow_write and args.allow_exec and args.once
    assert args.effort == "high"
    assert args.ignore_source == ["discord"]


# ---- hardening slice 1: continuity ------------------------------------------------------------

def test_default_summary_path_is_per_agent_and_conventional():
    p = R.default_summary_path("sol")
    assert p.endswith(os.path.join("state", "runner", "sol-exit-summary.json"))
    assert R.default_summary_path("sol-2") != p


def test_continuity_header_newborn_is_empty():
    assert R.continuity_header({}) == ""


def test_continuity_header_session2_reads_prior():
    prior = {"exit_code": 0, "turns": 7, "verdict": "ok", "session": 1,
             "last_error": None, "timestamp": time.time() - 3900}
    h = R.continuity_header(prior)
    assert "session 2" in h
    assert "exit=0" in h and "turns=7" in h and "verdict=ok" in h
    assert "1h05m ago" in h
    assert "Last error" not in h


def test_continuity_header_abnormal_run_warns_reverify():
    prior = {"exit_code": 4, "turns": 2, "verdict": "abnormal", "session": 3,
             "last_error": "timeout", "timestamp": time.time() - 60}
    h = R.continuity_header(prior)
    assert "session 4" in h
    assert "Last error: timeout" in h
    assert "re-verify" in h


def test_exit_summary_roundtrip_carries_session(tmp_path):
    p = tmp_path / "state" / "runner" / "sol-exit-summary.json"   # exercises makedirs
    R._RUN_STATS["turns"], R._RUN_STATS["last_error"] = 5, ""
    R._write_exit_summary(str(p), 0, session=3)
    prior = R.read_prior_summary(str(p))
    assert prior["session"] == 3 and prior["exit_code"] == 0 and prior["turns"] == 5
    assert prior["verdict"] == "ok"
    assert "session 4" in R.continuity_header(prior)   # the cycle increments


def test_read_prior_summary_missing_or_garbage_is_empty(tmp_path):
    assert R.read_prior_summary(str(tmp_path / "nope.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert R.read_prior_summary(str(bad)) == {}


# ---- hardening slice 2: RB-23 gate wiring -----------------------------------------------------

def test_rb23_promise_shaped_bounces_once():
    calls = []

    def resend(reprompt):
        calls.append(reprompt)
        return "Here is the actual verdict: SHIP. All pins green."

    out = R._rb23_gates("Verdict below.\n\nLet me fold this into my review closure.",
                        resend, "sol", pulse=_NOOP_PULSE)
    assert out == "Here is the actual verdict: SHIP. All pins green."
    assert len(calls) == 1
    assert "Deliver the promised work NOW" in calls[0]


def test_rb23_marker_confesses_in_sols_name_after_one_retry():
    calls = []

    def resend(reprompt):
        calls.append(reprompt)
        return "(sol produced no final answer)"

    out = R._rb23_gates("(sol produced no final answer)", resend, "sol", pulse=_NOOP_PULSE)
    assert out.startswith("(sol --"), out       # confession shape _process_one refuses to ack
    assert len(calls) == 1


def test_rb23_clean_answer_passes_untouched_no_resend():
    calls = []
    out = R._rb23_gates("Verdict: SHIP. 11/11 pins green by my run.",
                        lambda r: calls.append(r) or "x", "sol", pulse=_NOOP_PULSE)
    assert out == "Verdict: SHIP. 11/11 pins green by my run."
    assert calls == []


def test_rb23_error_marker_recovers_when_retry_delivers():
    def resend(reprompt):
        assert "[system bounce]" not in reprompt   # gate passes the reprompt; wrapping is the replier's job
        return "Recovered: the answer is 42."

    out = R._rb23_gates("(sol runner error: TimeoutError: boom)", resend, "sol",
                        pulse=_NOOP_PULSE)
    assert out == "Recovered: the answer is 42."


# ---- answerable gate --------------------------------------------------------------------------

def test_should_answer_matrix():
    assert R.should_answer("handoff", "codex_root", "sol")
    assert R.should_answer("inform", "claude", "sol")
    assert not R.should_answer("reply", "claude", "sol")    # echo-loop guard
    assert not R.should_answer("chat", "sol", "sol")        # own echo
    assert not R.should_answer("steer", "claude", "sol")    # folds via inject, never answered
    assert not R.should_answer("trace", "deepseek", "sol")  # narration is not a question


def test_dedicated_discord_owner_can_be_excluded_without_muting_peer_mail():
    args = R.build_parser().parse_args(["--ignore-source", "discord"])
    assert R.source_is_ignored({"source": "discord", "operator": True}, args) is True
    assert R.source_is_ignored({"source": "DISCORD"}, args) is True
    assert R.source_is_ignored({"source": "bifrost"}, args) is False
    assert R.source_is_ignored({}, args) is False
