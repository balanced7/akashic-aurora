"""W0.2 pins (RED first): touch.v1 -- what a seat actually touched, on the one spine, joinable.

SPEC: fences/context-system/reconciliation.md section 4, row W0.2, as folded by
      fences/one-spine/reconciliation.md (which rules that W0.2 ABSORBS Gap 3 of the
      record-is-total map: a hook firing IS the idle->active transition, so activity needs no
      separate kind, and emitting one would be a second writer for one fact).
BUILDS ON: core/coord/target.py (W0.1, context.target.v1), RED 9aee64c9 / GREEN 653b5723.

WHY, measured rather than asserted. Scanned `events:raw` this session, 6,918 records:

    kind                           total   with a session_id
    turn_metrics                    1546                   0
    boot                            1374                   0
    fail                            1227                   0
    file_edit                        192                   0
    session_signals                   89                  89

Eighty-nine of 6,918 carry a session id and they are all one kind. Every hook-emitted kind --
`fail`, `file_edit`, `command`, `flip`, `observation` -- carries none. That is the reach map's
"0.0% of captured events carrying a session id" as a live count, and it is the whole reason the
spine cannot answer "what was this SEAT, in this INCARNATION, doing at 03:12". The most recent
`fail` on the stream when this was written was my own failed command, captured correctly, with
`session_id: ""`.

Measured at the same time, because the design would differ if it were true: the two hook copies
do NOT systematically double-fire. `fail` shows 13 near-simultaneous twins in 1,227 (~1%) and
`file_edit` 4 in 192, where a systematic double-fire would show ~50%. So this slice needs twin
PARITY (both copies carry the fix) and not an idempotency mechanism for that cause.

SCOPE, stated so the next reader knows what was deliberately left out. This is the emit and its
payload: the typed targets, the session id, fail-open with a counted drop, and both twins. The
ring's retention, the per-ref capped list and the PHYSICS declaration are W0.4's instrument, which
prices this before Wave 1. Shipping the emit before its instrument is the ratified order.

Hermetic: the builder is pure, taking the payload, the roots and an existence callable. No disk,
no Redis, no hook subprocess except the twin-parity pin, which reads two files.
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.coord import target as T          # noqa: E402
from core.events import touch as TOUCH      # noqa: E402

MAIN = "E:/AI-Setup"
SUN = "C:/Users/L5/AppData/Local/AkashicAurora/worktrees/sunshine-discord-split"
ROOTS = T.Roots(main=MAIN, worktrees=(SUN,))
EXISTS = {"core/coord/orient.py", "a.py", "b.py", "core/"}


def build(payload, **kw):
    return TOUCH.build(payload, roots=ROOTS, exists=lambda k: k in EXISTS, **kw)


def P(tool, ti, session_id="sid-1", cwd=MAIN, **extra):
    d = {"tool_name": tool, "tool_input": ti, "session_id": session_id, "cwd": cwd}
    d.update(extra)
    return d


# ---------------------------------------------------------------- the schema and the kind
def test_the_schema_name_and_kind():
    assert TOUCH.SCHEMA == "touch.v1"
    assert TOUCH.KIND == "touch"


def test_the_detail_declares_its_own_schema_so_a_reader_never_guesses():
    t = build(P("Read", {"file_path": "core/coord/orient.py"}))
    assert t.detail["schema"] == "touch.v1"


# ---------------------------------------------------------------- the session id, the whole point
def test_the_session_id_comes_from_the_payload():
    t = build(P("Read", {"file_path": "core/coord/orient.py"}, session_id="payload-sid"))
    assert t.session_id == "payload-sid"


def test_the_payload_beats_the_environment(monkeypatch):
    # Env is ambient: it inherits from parents and siblings, so env-first silently attributes one
    # session's action to another. The payload's session_id is ground truth for who made the call.
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-sid")
    t = build(P("Read", {"file_path": "core/coord/orient.py"}, session_id="payload-sid"))
    assert t.session_id == "payload-sid"


def test_the_environment_is_the_fallback_not_the_source(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-sid")
    t = build(P("Read", {"file_path": "core/coord/orient.py"}, session_id=""))
    assert t.session_id == "env-sid"


def test_a_touch_with_no_session_id_anywhere_is_still_emitted_and_says_so(monkeypatch):
    # Zero is not no. An unattributable touch is still a fact about the house; what it must not do
    # is look identical to an attributed one. Same discipline as T418-b's unverified boot.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    t = build(P("Read", {"file_path": "core/coord/orient.py"}, session_id=""))
    assert t is not None and t.session_id == ""
    assert t.detail.get("session_source") == "unknown"


# ---------------------------------------------------------------- typed targets (W0.1 is the key)
def test_a_file_tool_yields_one_typed_target():
    t = build(P("Read", {"file_path": "core/coord/orient.py"}))
    assert [(x["action"], x["key"]) for x in t.detail["targets"]] == [("read", "core/coord/orient.py")]


def test_an_edit_is_a_write_not_a_read():
    t = build(P("Edit", {"file_path": "core/coord/orient.py"}))
    assert t.detail["targets"][0]["action"] == "write"


def test_a_worktree_path_carries_its_plane_into_the_key():
    t = build(P("Write", {"file_path": SUN + "/core/comm/bus.py"}))
    assert t.detail["targets"][0]["key"] == "work:sunshine-discord-split:core/comm/bus.py"


def test_a_shell_tool_goes_through_the_extraction_contract():
    t = build(P("Bash", {"command": "cp a.py b.py"}))
    assert sorted((x["action"], x["key"]) for x in t.detail["targets"]) == \
        [("read", "a.py"), ("write", "b.py")]


def test_a_command_that_cannot_be_seen_into_says_so_rather_than_reporting_a_clean_zero():
    # CORRECTED before GREEN. The RED commit asserted `== []` here, which contradicts the very
    # amendment this slice is built on: Navi's B5 rules that an uninspectable command emits
    # `targets: null` plus the flag, and says in as many words that "the touch.v1 detail carries
    # both". `[]` with a flag would have preserved the distinction only for a reader who knew to
    # look at the flag, which is the same trap one layer up -- so the schema keeps null meaning
    # "could not see" and `[]` meaning "looked, found nothing", identically in both places.
    t = build(P("Bash", {"command": "py - <<'EOF'\nimport os\nEOF"}))
    assert t.detail["targets"] is None and t.detail["targets_incomplete"] is True


def test_a_command_that_touched_nothing_is_a_measured_zero():
    t = build(P("Bash", {"command": "cd core && git status"}))
    assert t.detail["targets"] == [] and t.detail["targets_incomplete"] is False


def test_targets_are_capped_and_the_cap_is_confessed_never_silent():
    many = " ".join(f"f{i}.py" for i in range(200))
    t = build(P("Bash", {"command": "cat " + many}), exists_all=True)
    assert len(t.detail["targets"]) <= TOUCH.MAX_TARGETS
    assert t.detail["targets_total"] >= len(t.detail["targets"])
    if t.detail["targets_total"] > len(t.detail["targets"]):
        assert t.detail["targets_truncated"] is True


# ---------------------------------------------------------------- nothing raw is stored
def test_the_raw_command_text_never_lands_in_the_record():
    secret = "export AKASHIC_TOKEN=sk-ant-not-a-real-key-000 && cat a.py"
    t = build(P("Bash", {"command": secret}))
    blob = json.dumps(t.detail)
    assert "sk-ant-not-a-real-key-000" not in blob
    assert secret not in blob


def test_a_file_tools_content_never_lands_in_the_record():
    t = build(P("Write", {"file_path": "a.py", "content": "SUPER_SECRET_BODY = 1"}))
    assert "SUPER_SECRET_BODY" not in json.dumps(t.detail)


# ---------------------------------------------------------------- the refs the spine joins on
def test_the_subject_rides_the_record_fields_not_a_reinvented_field():
    # Navi's ruling in the one-spine round: the subject is DERIVABLE from agent_id + session_id,
    # which every events:raw record already carries, so no emit needs new plumbing and no `target`
    # field is added to the record.
    t = build(P("Read", {"file_path": "core/coord/orient.py"}, session_id="sid-9"))
    assert t.session_id == "sid-9" and "target" not in t.detail


def test_target_keys_ride_refs_so_the_byref_index_can_join_them():
    t = build(P("Read", {"file_path": "core/coord/orient.py"}))
    assert "core/coord/orient.py" in t.refs


def test_refs_never_carry_an_unparseable_spelling():
    t = build(P("Bash", {"command": "cp a.py b.py"}))
    for r in t.refs:
        T.parse(r, roots=ROOTS, exists=lambda k: True)     # must not raise


# ---------------------------------------------------------------- which tools, and fail-open
@pytest.mark.parametrize("tool", ["Read", "Edit", "Write", "NotebookEdit", "Bash",
                                  "PowerShell", "Grep", "Glob", "WebFetch"])
def test_every_tool_named_by_the_spec_produces_a_touch(tool):
    ti = {"command": "cat a.py"} if tool in ("Bash", "PowerShell") else \
         {"pattern": "foo", "path": "core/"} if tool in ("Grep", "Glob") else \
         {"url": "https://example.com/x"} if tool == "WebFetch" else \
         {"file_path": "a.py"}
    assert build(P(tool, ti)) is not None


def test_an_unlisted_tool_produces_no_touch():
    assert build(P("SomeOtherTool", {"file_path": "a.py"})) is None


def test_the_builder_never_raises_into_the_hook_and_counts_what_it_dropped():
    # The hook runs on every tool call for every seat. A telemetry builder that can raise is a
    # telemetry builder that can wedge the house's hot path.
    before = TOUCH.drops()
    t = TOUCH.build({"tool_name": "Bash", "tool_input": {"command": "cat a.py"}},
                    roots=None, exists=None)                  # deliberately malformed inputs
    assert t is None
    assert TOUCH.drops() == before + 1, "a swallowed failure must still be counted"


# ---------------------------------------------------------------- the twins stay in parity
def test_both_hook_copies_carry_the_touch_emit():
    """This repo keeps seven hook pairs under scripts/hooks/ and agent/harness/hooks/ that differ
    only by their sys.path depth. USER settings invoke the scripts/ copy and PROJECT settings the
    agent/harness/ copy, so a home-rooted seat runs ONLY the copy check_wiring deliberately does
    not walk. Patching one is shipping to half the fleet, invisibly."""
    a = open(os.path.join(REPO, "agent", "harness", "hooks", "claude_posttooluse.py"),
             encoding="utf-8").read()
    b = open(os.path.join(REPO, "scripts", "hooks", "claude_posttooluse.py"),
             encoding="utf-8").read()
    for name, src in (("agent/harness/hooks", a), ("scripts/hooks", b)):
        assert "touch" in src and "core.events" in src, f"{name} copy has no touch emit"


def test_the_twins_differ_only_by_their_path_depth_and_prose():
    a = open(os.path.join(REPO, "agent", "harness", "hooks", "claude_posttooluse.py"),
             encoding="utf-8").read()
    b = open(os.path.join(REPO, "scripts", "hooks", "claude_posttooluse.py"),
             encoding="utf-8").read()
    strip = lambda s: [ln for ln in s.splitlines()
                       if "sys.path.insert" not in ln and not ln.strip().startswith("#")]
    assert strip(a) == strip(b), "the hook twins have drifted in CODE, not just in comments"
