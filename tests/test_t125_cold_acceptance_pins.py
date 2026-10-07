"""T125 cold-acceptance pins — cursor_grok newcomer lookups (mechanical bar).

Source lookups: research/in-flight/newcomer-failed-lookups-grok-2026-07-31.md
Amended bar (note t125-acceptance-amendment, 2026-07-31):
  (1) STRUCTURAL — one hop from datasheet/blast-radius: exposes, depends-on,
      depended-on-by, tests naming it, env flags, named-but-missing paths,
      historical co-change.
  (2) SEMANTIC — ownership / authority / forbidden-effect questions MUST render
      UNKNOWN (or appear only under not_derived). An affirmative answer from
      mechanical-only inputs is a FAIL even if coincidentally correct.

These pins are the cold-seat instrument. Do NOT open Codex's sealed qualitative
key. A warm seat writing these would unconsciously supply negations; this suite
converts the published lookup list into permanent acceptance.

Run:  py -m pytest tests/test_t125_cold_acceptance_pins.py -v
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "scripts", "generators", "gen_datasheet.py")
LOOKUPS = os.path.join(
    ROOT, "research", "in-flight", "newcomer-failed-lookups-grok-2026-07-31.md"
)


def _load_gen():
    assert os.path.isfile(GEN), f"missing generator: {GEN}"
    spec = importlib.util.spec_from_file_location("gen_datasheet_t125", GEN)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def graph():
    mod = _load_gen()
    g = mod.build()
    assert not g.get("error"), f"datasheet build fatal: {g.get('error')}"
    return g


@pytest.fixture(scope="module")
def sheets(graph):
    return graph["sheets"]


@pytest.fixture(scope="module")
def coverage(graph):
    return graph["coverage"]


# ── P0: door exists for a cold seat ──────────────────────────────────


def test_p0_generator_and_lookups_artifact_exist():
    """P0: cold seat can find the tool and the published lookup list."""
    assert os.path.isfile(GEN)
    assert os.path.isfile(LOOKUPS)
    body = open(LOOKUPS, encoding="utf-8").read()
    assert "check_comprehensibility" in body
    assert "I blamed myself" in body


def test_p0_cli_explain_door(graph):
    """P0b: --explain is a one-hop door (not a second research project)."""
    mod = _load_gen()
    assert callable(getattr(mod, "render_sheet", None))
    assert callable(getattr(mod, "main", None))
    assert "scripts/githooks/pre_commit.py" in graph["sheets"]


# ── Structural pins mapped from lookups ──────────────────────────────


def test_p7_broken_path_named_by_pre_commit(sheets):
    """Lookup 7 STRUCTURAL: ghost path must surface as BROKEN in one hop.

    Question: where is check_comprehensibility.py?
    Expected: pre_commit datasheet lists scripts/check_comprehensibility.py under
    broken_path_refs; the real checker path is not broken.
    """
    s = sheets["scripts/githooks/pre_commit.py"]
    broken = set(s.get("broken_path_refs") or [])
    assert "scripts/check_comprehensibility.py" in broken, (
        f"RED/STRUCTURAL: ghost path not flagged BROKEN; got {sorted(broken)}"
    )
    real = "scripts/checkers/check_comprehensibility.py"
    assert real not in broken
    assert os.path.isfile(os.path.join(ROOT, real.replace("/", os.sep)))


def test_p2_two_worklive_organs_are_distinct_modules(sheets):
    """Lookup 2 STRUCTURAL: two organs sharing an English name must both sheet.

    Question: which worklive key is the truth?
    Mechanical v0 cannot name 'the truth' (semantic). It MUST make both modules
    independently queryable so a cold seat sees TWO surfaces, not one word.
    """
    liv = sheets.get("core/comm/liveness.py")
    ros = sheets.get("core/comm/roster.py")
    assert liv and ros, "RED: liveness/roster missing from universe sheets"
    assert "core.comm.liveness" in (ros.get("imports_internal") or []), (
        "RED: roster does not declare depends-on liveness in one hop"
    )
    # Both touch WORKLIVE dials or the word in their sheetable surface.
    liv_flags = set(liv.get("flags") or [])
    ros_flags = set(ros.get("flags") or [])
    assert liv_flags or ros_flags, "RED: neither organ exposes WORKLIVE-related flags"
    assert liv_flags != ros_flags or liv["path"] != ros["path"]


def test_p1_alive_now_is_not_claimed_by_temporal_band(sheets, coverage):
    """Lookup 1 SEMANTIC/RUNTIME honesty: datasheet must not claim who is alive NOW.

    Question: are deepseek/kimi alive right now?
    Affirmative from git/temporal band = FAIL. Honesty text or not_derived = PASS.
    """
    ros = sheets["core/comm/roster.py"]
    # Temporal fields may exist; they must not be framed as live presence.
    assert "last_touch_days" in ros
    not_derived = " ".join(coverage.get("not_derived_in_v0") or []).lower()
    # Generator docstring / coverage must refuse runtime liveness claims.
    src = open(GEN, encoding="utf-8").read().lower()
    assert "who is active" in src or "says nothing about who is" in src or (
        "runtime/observed" in not_derived
    ), "RED: no honesty marker that temporal ≠ live presence"


def test_p_mailbox_ownership_stays_unknown(sheets, coverage):
    """Lookups that ask 'who owns mail' — SEMANTIC UNKNOWN is PASS.

    Mechanical sheet may show mailbox.py edges; it must NOT mint authoritative_for.
    """
    s = sheets.get("core/comm/mailbox.py")
    assert s, "RED: mailbox.py unscanned/missing — cannot even be honest"
    blob = str(s).lower()
    for banned in ("authoritative_for", "owns mail", "owner:", "authority:"):
        assert banned not in blob, f"FAIL: mechanical sheet invented semantic claim {banned!r}"
    nd = " ".join(coverage.get("not_derived_in_v0") or []).lower()
    assert "authoritative" in nd or "authored claims" in nd, (
        "RED: coverage does not declare authored authority claims as not-derived"
    )


def test_p_no_verified_claim_without_gate_receipts(sheets, coverage):
    """Cross-cutting: nothing renders VERIFIED in v0 (gate-health not yet green)."""
    for path, s in sheets.items():
        blob = str(s).lower()
        assert "verified" not in blob or "no field here is verified" in open(
            GEN, encoding="utf-8"
        ).read().lower(), f"unexpected verified claim on {path}"
    nd = " ".join(coverage.get("not_derived_in_v0") or []).lower()
    assert "verified" in nd or "gate-health" in nd or "gate" in nd


# ── One-hop recipe pins (cold seat can run without a peer) ───────────


@pytest.mark.parametrize(
    "lookup_id,module,must_answer",
    [
        # Structural slices that the datasheet is ON THE HOOK for.
        (7, "scripts/githooks/pre_commit.py", "broken_path_refs"),
        (2, "core/comm/roster.py", "imports_internal"),
        (2, "core/comm/liveness.py", "flags"),
        # Mailbox edges are structural; ownership is not (tested separately).
        (3, "core/comm/mailbox.py", "exposes"),
    ],
)
def test_one_hop_field_present(sheets, lookup_id, module, must_answer):
    """For structural lookups: the named field exists and is non-empty in one hop."""
    s = sheets.get(module)
    assert s, f"lookup {lookup_id}: UNSCANNED {module}"
    val = s.get(must_answer)
    assert val not in (None, [], "", "UNKNOWN"), (
        f"RED lookup {lookup_id}: {module}.{must_answer} empty/UNKNOWN — "
        f"cold seat still cannot answer in one hop"
    )


@pytest.mark.parametrize(
    "lookup_id,reason",
    [
        (1, "live process liveness is runtime, not git"),
        (4, "wake-worthiness of kind=chat is protocol, not import graph"),
        (5, "CURRENT DIRECTIVE / notes are not .py universe"),
        (6, "where-we-are note currency is not .py universe"),
        (8, "CLI flag symmetry is not import graph"),
        (9, "skip-to-now ceremony is not import graph"),
        (10, "wake truncation is transport runtime"),
        (11, "note supersession is note-store, not datasheet"),
        (12, "charter identity is not mechanical module edges"),
        (13, "watcher exit-and-rearm is process lifecycle"),
        (14, "doctor LANE STALL is runtime presence"),
    ],
)
def test_ops_lookups_must_not_fake_structural_answers(sheets, coverage, lookup_id, reason):
    """Ops/runtime lookups: datasheet must not invent a structural 'answer'.

    PASS = field absent / UNKNOWN / listed not_derived. FAIL = confident fake.
    """
    # Pulse/history honesty already covers (1)/(14) class; here we only forbid
    # a sheet claiming to settle the listed ops questions via a magic field.
    forbidden_keys = {
        "alive_now",
        "process_alive",
        "wake_kinds",
        "current_directive",
        "note_currency",
        "cli_flag_symmetry",
        "owner_agent",
        "charter_for",
        "watcher_policy",
        "lane_stall_meaning",
    }
    for s in sheets.values():
        for k in forbidden_keys:
            assert k not in s, (
                f"FAIL lookup {lookup_id}: invented field {k} ({reason})"
            )
    assert coverage.get("not_derived_in_v0"), f"lookup {lookup_id}: empty not_derived"


# ── Unscanned ≠ empty ────────────────────────────────────────────────


def test_coverage_manifest_distinguishes_unscanned(coverage):
    """Law: UNSCANNED != EMPTY. Manifest must exist with revision + counts."""
    assert coverage.get("revision")
    assert "scanned" in coverage or "in_universe" in coverage
    assert isinstance(coverage.get("skipped"), list)
    assert coverage.get("not_derived_in_v0"), "RED: not_derived list missing"


def test_render_marks_mechanical_v0_not_verified(sheets, coverage):
    """Rendered sheet must say mechanical v0 / not VERIFIED (trust language ban)."""
    mod = _load_gen()
    text = mod.render_sheet(sheets["scripts/githooks/pre_commit.py"], coverage).lower()
    assert "mechanical v0" in text or "no field here is verified" in text
    assert "unbypassable" not in text


# ── Remaining RED gaps (pre-registered; must fail until closed) ───────
# These are the newcomer questions the current mechanical sheet still cannot
# settle in ONE hop without reading source. Keep them RED on purpose.


def test_red_p2_dual_worklive_key_shapes_on_sheet(sheets):
    """RED lookup 2: sheet must name BOTH key shapes without reading .py bodies.

    Today: two modules sheet, but the Redis key patterns
    (bifrost:worklive:<agent> vs …:<agent>#<sid8>) are not a datasheet field.
    Cold seat still opens source — so the wasting-asset question is unsolved.
    """
    for path in ("core/comm/liveness.py", "core/comm/roster.py"):
        blob = str(sheets[path]).lower()
        if "worklive:" in blob or "worklive/<" in blob or "#sid" in blob:
            return
    assert False, (
        "RED: worklive dual-key shapes not surfaced on sheets — "
        "cold seat still needs source archaeology for lookup 2"
    )


def test_red_p7_broken_path_points_at_successor(sheets):
    """RED lookup 7 polish: BROKEN ref should hint where the file moved.

    Today: broken_path_refs lists the ghost. Cold seat still asks 'where DID it go?'
    Acceptance: ghost entry carries successor path scripts/checkers/... or equivalent.
    """
    s = sheets["scripts/githooks/pre_commit.py"]
    broken = s.get("broken_path_refs") or []
    # Prefer structured successor; string blob search is the minimum bar.
    blob = str(s)
    if any(isinstance(x, dict) and "successor" in x for x in broken):
        return
    if "scripts/checkers/check_comprehensibility.py" in blob:
        return
    assert False, (
        "RED: broken_path_refs names the ghost but not the successor path — "
        "lookup 7 still needs a second hop"
    )


def test_red_lookup_recipe_index_exists():
    """RED: cold seat needs lookup-id → one-hop command index (not tribal knowledge)."""
    candidates = [
        os.path.join(ROOT, "research", "in-flight", "t125-cold-lookup-recipes.md"),
        os.path.join(ROOT, "docs", "t125-cold-lookup-recipes.md"),
    ]
    assert any(os.path.isfile(p) for p in candidates), (
        "RED: no lookup→recipe index file — cold seat cannot map questions 1–14 "
        "to --explain/--impact commands without a peer"
    )
