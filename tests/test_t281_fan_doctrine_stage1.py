"""T281 Stage 1+2: named geometries at the ask door, coverage in the envelope, route journal.

The fan doctrine (atom fan-doctrine-v1_b70185, fence r1 folded) named six+one geometries and
two measurement gaps. This slice lands the door-side mechanics:

  - `geometry` is DECLARED intent, stamped verbatim into the fan detail (never derived --
    the T228 declared-vs-derived law).
  - the evidence builder records `chars_total` per included file, so coverage becomes a
    NUMBER (chars_sent / chars_total) instead of a prose warning -- the laundering class
    (night of 2026-08-10) gets a mechanical field, not just a notice.
  - every fan appends one line to the ROUTE JOURNAL (state/route_journal.jsonl, env
    AKASHIC_ROUTE_JOURNAL overrides) -- the substrate for per-route funnel counters and the
    tokens-per-confirmed-finding delta (Daniil 08-11: "quantify the performance and impact
    delta"). Fail-open: a dead journal must never wedge an ask.
  - `validate_geometry` teaches: wrong flag combinations 422 with the expected shape, never
    a silent stamp (the grammar's own error law, applied to the door).

Pins:
  P1  geometry stamped verbatim; absent stays empty (declared, never derived)
  P2  build_context records chars_total; coverage ratio computes; unclipped file -> 1.0
  P3  ask_many appends one route-journal line with the doctrine fields
  P4  validate_geometry teaches on bad combinations and lists the vocabulary on unknowns
  P5  the ask parser's help carries the when-to-fan rubric and every geometry name

Run: py -m pytest tests/test_t281_fan_doctrine_stage1.py -q
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import ask as A  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class _Resp:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})(),
                                       "finish_reason": "stop"})()]
        self.usage = None


class _Scripted:
    """Mirror of the t182 harness: a fake client keyed by prompt."""
    def __init__(self, table):
        class _Completions:
            @staticmethod
            def create(model=None, messages=None, max_tokens=None, **kw):
                prompt = messages[-1]["content"]
                for key, text in table.items():
                    if key in prompt:
                        return _Resp(text)
                return _Resp("unscripted")
        self.table = table
        self.chat = type("Chat", (), {"completions": _Completions()})()


# ---------------------------------------------------------------- P1: geometry declared
def test_p1_geometry_stamped_verbatim(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_ROUTE_JOURNAL", str(tmp_path / "rj.jsonl"))
    o = A.ask_many(["p1", "p2"], client=_Scripted({"p1": "a", "p2": "b"}),
                   geometry="lens")
    assert o.detail.get("geometry") == "lens", "P1: declared geometry rides the detail"
    o2 = A.ask_many(["p1"], client=_Scripted({"p1": "a"}))
    assert o2.detail.get("geometry", "") == "", (
        "P1: no declaration -> no geometry; the door never infers intent (T228 law)")


# ---------------------------------------------------------------- P2: coverage numbers
def test_p2_builder_records_totals_and_ratio(tmp_path):
    f = ROOT / "scratch" / "_t281_pin_fixture.txt"
    f.write_text("x" * 1000, encoding="utf-8")
    try:
        _, meta = A.build_context([str(f)], budget_chars=100)
        inc = meta["included"][0]
        assert inc["truncated"] is True and inc["chars"] == 100
        assert inc.get("chars_total") == 1000, (
            "P2: the builder reads the whole file; recording its total costs nothing and "
            "turns the clip warning into a NUMBER")
        cov = A.coverage_from_meta(meta)
        assert cov and abs(cov["ratio"] - 0.1) < 1e-9 and cov["chars_total"] == 1000

        _, meta_full = A.build_context([str(f)], budget_chars=5000)
        cov_full = A.coverage_from_meta(meta_full)
        assert cov_full["ratio"] == 1.0, "P2: unclipped -> ratio exactly 1.0"
    finally:
        f.unlink(missing_ok=True)


def test_p2b_fan_detail_carries_coverage(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_ROUTE_JOURNAL", str(tmp_path / "rj.jsonl"))
    f = ROOT / "scratch" / "_t281_pin_fixture2.txt"
    f.write_text("evidence " * 20, encoding="utf-8")
    try:
        o = A.ask_many(["p1"], client=_Scripted({"p1": "a"}), with_files=[str(f)])
        cov = o.detail.get("coverage")
        assert cov and cov["ratio"] == 1.0 and cov["chars_total"] > 0, (
            "P2b: a fan that rode evidence carries the coverage block in its envelope")
    finally:
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------- P3: the route journal
def test_p3_route_journal_appends_one_line(tmp_path, monkeypatch):
    rj = tmp_path / "routes.jsonl"
    monkeypatch.setenv("AKASHIC_ROUTE_JOURNAL", str(rj))
    A.ask_many(["p1", "p2"], client=_Scripted({"p1": "a", "p2": "b"}),
               geometry="partition")
    lines = rj.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1, "P3: one fan, one route line"
    rec = json.loads(lines[0])
    for field in ("ts", "geometry", "n", "n_ok", "usd", "elapsed_s", "warnings_n"):
        assert field in rec, f"P3: route record must carry '{field}'"
    assert rec["geometry"] == "partition" and rec["n"] == 2


def test_p3b_dead_journal_never_wedges(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_ROUTE_JOURNAL", str(tmp_path / "no_dir" / "x" / "rj.jsonl"))
    o = A.ask_many(["p1"], client=_Scripted({"p1": "a"}))
    assert o.ok, "P3b: journal failure is invisible to the ask (fail-open)"


# ---------------------------------------------------------------- P4: teaching errors
def test_p4_validate_geometry_teaches():
    err = A.validate_geometry("panel", fan_n=1, n_prompts=1, has_evidence=False)
    assert err and "--fan" in err, "P4: panel without --fan N>1 names the missing flag"
    err2 = A.validate_geometry("no-such-shape", fan_n=1, n_prompts=1, has_evidence=False)
    assert err2 and "partition" in err2 and "backbrief" in err2, (
        "P4: unknown geometry lists the vocabulary (422-with-vocabulary, the grammar law)")
    assert A.validate_geometry("", fan_n=1, n_prompts=1, has_evidence=False) == "", (
        "P4: empty declaration is always valid (geometry is optional)")
    assert A.validate_geometry("lens", fan_n=1, n_prompts=3, has_evidence=True) == ""


# ---------------------------------------------------------------- P4b: the WIRING refuses
def test_p4b_cli_refuses_before_any_model_call(tmp_path):
    """The pin the leak demanded. P4 proved the pure function teaches; the first wiring never
    CALLED it on the single path, and two live smokes went to the model with --geometry
    silently ignored. This drives the real CLI: a broken API key guards the failure mode --
    if the refusal doesn't fire pre-call, the run dies on auth, not on billing."""
    import subprocess
    env = dict(os.environ, DEEPSEEK_API_KEY="broken-on-purpose",
               AKASHIC_ROUTE_JOURNAL=str(tmp_path / "rj.jsonl"))
    r = subprocess.run([sys.executable, str(ROOT / "agent_cli.py"), "ask",
                        "--geometry", "panel", "smoke"],
                       capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 2, f"expected pre-call refusal, got rc={r.returncode}"
    assert "--fan" in (r.stderr or ""), "the refusal must teach the missing flag"
    assert "auth" not in (r.stderr or "").lower(), "refusal must precede any model call"

    r2 = subprocess.run([sys.executable, str(ROOT / "agent_cli.py"), "ask",
                         "--geometry", "backbrief", "smoke"],
                        capture_output=True, text=True, env=env, timeout=120)
    assert r2.returncode == 2 and "--with" in (r2.stderr or ""), (
        "backbrief without a pack refuses and names --with")


# ---------------------------------------------------------------- P5: the rubric at the door
def test_p5_help_carries_rubric_and_vocabulary():
    src = io.open(ROOT / "agent_cli.py", encoding="utf-8").read()
    i = src.find('add_parser("ask"')
    assert i > 0
    block = src[i:i + 6000]
    assert "WHEN TO FAN" in block, "P5: the rubric headline rides the ask parser help"
    for g in A.GEOMETRIES:
        assert g in block, f"P5: geometry '{g}' must appear in the door's help"
