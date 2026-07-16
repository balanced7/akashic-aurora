"""T078 W1 ACCEPTANCE — C6 token dashboard + T056 join (the meter).

Spec: research/reviewed/t078-capability-surface-reconciliation-2026-07-15.md
ruling R1: meters before levers. deepseek builds, claude verifies.

Three parts built:
  1. TokenJournal: daily JSON in state/runner_<agent>_<YYYY-MM-DD>.json
  2. T056 join: runner passes tokens to turn_metrics.record() at each turn-close
  3. Doctor line: examine() reads the journal and renders a cost finding
"""
import json
import inspect
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.runner_token_journal import TokenJournal
from core.comm import turn_metrics as tm
from core.comm import doctor


# --------------------------------------------------------------- W1-P1 TokenJournal
def test_p1_token_journal_new_day_creates_fresh(tmp_path):
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    assert j.turns == 0
    assert j.prompt_tokens == 0
    assert j.completion_tokens == 0
    j._save()
    raw = json.loads(open(j._path, encoding="utf-8").read())
    assert raw["agent"] == "deepseek"
    assert raw["date"] == time.strftime("%Y-%m-%d")


def test_p1_token_journal_accumulates(tmp_path):
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    j.add_turn(prompt=500, completion=300)
    j.add_turn(prompt=200, completion=100)
    assert j.turns == 2
    assert j.prompt_tokens == 700
    assert j.completion_tokens == 400
    j2 = TokenJournal("deepseek", journal_dir=str(tmp_path))
    assert j2.turns == 2
    assert j2.prompt_tokens == 700


def test_p1_token_journal_old_file_ignored(tmp_path):
    # LOCAL time, matching the journal's own date convention (the 2026-07-15 flake:
    # gmtime here vs local strftime in the journal made yesterday==today whenever
    # UTC had crossed midnight and local had not -- the rename became a no-op)
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    j.add_turn(prompt=100, completion=50)
    j._save()
    yesterday_path = os.path.join(str(tmp_path), f"runner_deepseek_{yesterday}.json")
    os.rename(j._path, yesterday_path)
    j2 = TokenJournal("deepseek", journal_dir=str(tmp_path))
    assert j2.turns == 0
    assert os.path.exists(yesterday_path)


def test_p1_cost_estimate_positive(tmp_path):
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    j.add_turn(prompt=500000, completion=250000)
    assert j.total_cost_est() > 0.5


# --------------------------------------------------------------- W1-P2 T056 feed
def test_p2_turn_metrics_accepts_tokens_kwarg():
    sig = inspect.signature(tm.record)
    assert "tokens" in sig.parameters, "W1-P2: tokens kwarg must exist in record()"
    param = sig.parameters["tokens"]
    assert param.default is None


# --------------------------------------------------------------- W1-P3 doctor line
def test_p3_doctor_cost_line_renders(tmp_path):
    path = os.path.join(str(tmp_path), f"runner_deepseek_{time.strftime('%Y-%m-%d')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"agent": "deepseek", "date": time.strftime("%Y-%m-%d"),
                   "turns": 12, "prompt_tokens": 45000, "completion_tokens": 18000,
                   "cost_est": 0.06}, f)

    finding = doctor._token_cost_line("deepseek", journal_dir=str(tmp_path))
    assert finding is not None
    assert "12 turn" in finding["line"]
    assert "63k" in finding["line"]
    assert finding["grade"] == "dashboard"


def test_p3_doctor_silent_when_absent(tmp_path):
    finding = doctor._token_cost_line("nobody", journal_dir=str(tmp_path))
    assert finding is None


def test_p3_doctor_silent_when_zero(tmp_path):
    path = os.path.join(str(tmp_path), f"runner_deepseek_{time.strftime('%Y-%m-%d')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"agent": "deepseek", "date": time.strftime("%Y-%m-%d"),
                   "turns": 0, "prompt_tokens": 0, "completion_tokens": 0}, f)
    assert doctor._token_cost_line("deepseek", journal_dir=str(tmp_path)) is None
