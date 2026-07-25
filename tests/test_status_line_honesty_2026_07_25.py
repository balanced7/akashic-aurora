"""Status-line honesty pins (W61/W62/W65, filed 2026-07-25 from the fresh-seat audit).

One defect class, three organs: the system computes the truth and then prints something
else. Each pin below is the render, not the mechanism -- the mechanisms were all correct.

  W65  consume drains 5 stale messages, parks them to the bench, prints
       "(no messages consumed)" -- the honest stale_notice is RETURNED by
       consume_inbox() and then discarded by the renderer.
  W61  boot's first instruction (GROUND FIRST) is age-checked but never
       resolved: a pointer to a file deleted by the library migration renders
       as fresh.
  W62  delta reports "HEAD moved BACKWARDS or diverged" for a mark sha that is
       simply not in this repo, and prints a `git log A..B` remedy that fatals.

  P1  consumed=[] + stale_notice  -> the notice renders; NOT the bare "(no messages...)"
  P2  consumed=[] + no notice     -> "(no messages consumed)" is still correct
  P3  consumed=[N] + stale_notice -> both render (notice never swallowed by the happy path)
  P4  grounding pointer that does not resolve -> MOVED marker, not a clean fresh line
  P5  grounding pointer that resolves         -> unchanged (no regression on W37 P2)
  P6  delta mark sha absent from the repo -> says unresolvable, prints NO git-log remedy
  P7  delta genuine divergence (both shas real) -> keeps the loud diverged render
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from agent.harness import delta as delta_mod


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


def _sync_args(**kw):
    base = dict(agent_id="claude", consume=True, limit=20, json=False, traces=False)
    base.update(kw)
    return Ns(**base)


# ---------------------------------------------------------------- W65
def _stub_consume(monkeypatch, payload):
    import agent.bifrost_pull as bp
    monkeypatch.setattr(bp, "consume_inbox", lambda *a, **k: payload)


def test_p1_parked_stale_is_not_silence(monkeypatch, capsys):
    """The live 2026-07-25 case: 5 real messages drained + parked, renderer said nothing."""
    _stub_consume(monkeypatch, {
        "seat_held": False,
        "consumed": [],
        "stale_asks_parked": 2,
        "stale_notice": ("  skipped 3 stale inform(s)/trace(s) (no bench pollution)\n"
                         "  parked 2 stale ask(s) to durable bench"),
    })
    rc = agent_cli.cmd_bifrost_sync(_sync_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "parked 2 stale ask(s)" in out, "the notice the door already returns must render"
    assert out.strip() != "(no messages consumed)", "silence is a lie when the cursor moved"


def test_p2_true_silence_stays_silent(monkeypatch, capsys):
    """Honesty cuts both ways: nothing happened -> say nothing happened."""
    _stub_consume(monkeypatch, {"seat_held": False, "consumed": [], "stale_notice": None})
    rc = agent_cli.cmd_bifrost_sync(_sync_args())
    assert rc == 0
    assert "(no messages consumed)" in capsys.readouterr().out


def test_p3_notice_survives_the_happy_path(monkeypatch, capsys):
    """A notice must not be swallowed just because some mail WAS surfaced."""
    _stub_consume(monkeypatch, {
        "seat_held": False,
        "consumed": [{"frm": "kimi", "kind": "reply", "content": "hello", "id": "1-0"}],
        "stale_asks_parked": 1,
        "stale_notice": "  parked 1 stale ask(s) to durable bench",
    })
    rc = agent_cli.cmd_bifrost_sync(_sync_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "consumed 1 message" in out
    assert "parked 1 stale ask(s)" in out


# ------------------------------------------------- W65 door parity (deepseek fence)
def test_p15_shared_renderer_silent_when_nothing_moved():
    from agent.bifrost_pull import stale_notice_lines
    assert stale_notice_lines({"consumed": [], "stale_notice": None}, "claude") == []


def test_p16_shared_renderer_reports_the_advance():
    from agent.bifrost_pull import stale_notice_lines
    out = stale_notice_lines(
        {"consumed": [], "stale_notice": "  parked 2 stale ask(s) to durable bench"}, "claude")
    assert len(out) == 2
    assert "parked 2 stale ask(s)" in out[0]
    assert "cursor ADVANCED" in out[1]


def test_p17_no_advance_line_when_mail_actually_surfaced():
    from agent.bifrost_pull import stale_notice_lines
    out = stale_notice_lines(
        {"consumed": [{"id": "1-0"}], "stale_notice": "  parked 1 stale ask(s)"}, "claude")
    assert len(out) == 1, "the advance note is for the empty case only"


def test_p18_both_doors_use_the_shared_renderer():
    """deepseek's fence: the CLI door was fixed and the MCP door still lied. A shared
    renderer is the only form of the fix that cannot drift apart again.

    Reads the source FILES rather than inspect.getsource on the live objects: the MCP
    door is wrapped by @mcp.tool(), so getsource resolved to the decorator's object under
    a full-suite import and the pin failed in-suite while passing standalone. A pin whose
    result depends on import order is not a pin."""
    import pathlib
    root = pathlib.Path(agent_cli.__file__).resolve().parent
    for fname in ("ai_setup_mcp.py", "agent_cli.py"):
        src = (root / fname).read_text(encoding="utf-8", errors="replace")
        assert "stale_notice_lines" in src, f"{fname} must render via the shared helper"
    shared = (root / "agent" / "bifrost_pull.py").read_text(encoding="utf-8", errors="replace")
    assert "def stale_notice_lines" in shared, "the one renderer both doors call"


# ---------------------------------------------------------------- W61
def test_p4_unresolvable_grounding_pointer_confesses(monkeypatch):
    monkeypatch.setattr(agent_cli, "_grounding_exists", lambda p: False)
    line = agent_cli._grounding_line("chronicles/deleted-by-migration.md", "2026-07-23", 2)
    assert "MOVED" in line or "UNRESOLVED" in line, "a dangling first instruction must say so"
    assert "chronicles/deleted-by-migration.md" in line


def test_p19_prose_pointer_is_never_claimed_missing():
    """deepseek fence F1: a slash alone is not path-evidence. A pointer opening
    'C1/C2 design' would have rendered a false [MOVED?] -- the exact false-alarm class
    this whole change exists to remove. Only file-ish candidates are resolved."""
    assert agent_cli._grounding_exists("C1/C2 design round") is True
    assert agent_cli._grounding_exists("G0-G5 partner night") is True
    assert agent_cli._grounding_exists("") is True
    # path-shaped pointers are still genuinely checked, both ways
    assert agent_cli._grounding_exists("docs/CONDUCT.md") is True
    assert agent_cli._grounding_exists("chronicles/definitely-not-here-9z.md") is False


def test_p5_resolvable_grounding_pointer_unchanged(monkeypatch):
    monkeypatch.setattr(agent_cli, "_grounding_exists", lambda p: True)
    line = agent_cli._grounding_line("chronicles/real.md", "2026-07-23", 2)
    assert "chronicles/real.md" in line
    assert "MOVED" not in line and "UNRESOLVED" not in line
    assert "[as of 2026-07-23]" in line


# ---------------------------------------------------------------- W62
def test_p6_unresolvable_mark_is_not_a_rewrite_alarm(monkeypatch):
    """f6a96df was not in the repo at all; delta called it a history rewrite."""
    monkeypatch.setattr(delta_mod, "_git_log_range", lambda a, b: None)
    monkeypatch.setattr(delta_mod, "_git_is_forward", lambda a, b: False)
    monkeypatch.setattr(delta_mod, "_git_has_commit",
                        lambda sha: sha != "f6a96df0000000000000000000000000000000000")
    mark = {"git_commit": "f6a96df0000000000000000000000000000000000",
            "ledger_seq": "1", "notes_head": "n", "promoted_id": "p"}
    cur = {"git_commit": "b727096000000000000000000000000000000000",
           "ledger_seq": "1", "notes_head": "n", "promoted_id": "p"}
    txt = "\n".join(delta_mod._sections("claude", mark, cur))
    assert "BACKWARDS" not in txt, "an unresolvable mark is not a rewrite"
    assert "git log" not in txt, "never print a remedy command that cannot run"
    assert "f6a96df" in txt, "still name the mark so it is diagnosable"


# ---------------------------------------------------------------- C1 boot stance block
def test_p11_stance_block_exists_and_stamps_its_version():
    """The organ CONDUCT.md listed in the present tense but never built (deepseek+kimi,
    independently, 2026-07-25)."""
    out = agent_cli._stance_block("claude")
    assert len(out) == 3, "the activation map specifies a 3-line render"
    joined = "\n".join(out)
    assert agent_cli.CONDUCT_VERSION in joined, \
        "v1.1 substrate rule: every projection stamps conduct_version (kimi F2: zero did)"
    assert "docs/CONDUCT.md" in joined, "the render points back at its substrate"


def test_p12_license_line_is_the_load_bearing_one():
    """Kimi's finding: organs delivered the FORMS without the LICENSE to amend them."""
    joined = "\n".join(agent_cli._stance_block("claude")).lower()
    assert "floor" in joined and "ceiling" in joined
    assert "amend" in joined, "the permission to diverge IS the culture/checklist difference"


def test_p13_missing_stretch_renders_a_named_gap(monkeypatch):
    """Unrecorded must read as a GAP, not as a silent zero -- tonight's whole theme."""
    monkeypatch.setattr(agent_cli, "_charter_stretch", lambda a: None)
    line = [l for l in agent_cli._stance_block("kimi") if "stretch" in l][0]
    assert "GAP" in line and "CHARTER.md" in line


def test_p14_stance_rides_the_head_without_displacing_the_cold_start_four():
    """deepseek proved the runner's folded system prompt carried zero stance -- so the
    fix is PRESENCE in the head. It is not primacy: the first placement put stance above
    the map and pushed 'RULE: DONE is closed' out of the head-16 window that the T022
    cold-start contract owns, and test_boot_orientation caught it on the first run. This
    pin holds both halves so the next organ cannot re-learn it the same way."""
    head = agent_cli._orientation_header("claude")
    assert "# STANCE" in head, "the head a stateless peer folds must carry the stance"
    first16 = "\n".join(head.splitlines()[:16])
    assert "# STANCE" not in first16, \
        "a new organ does not spend the head-16 the four cold-start questions own"


def test_p20_stance_survives_the_runner_onboarding_trim():
    """kimi's fence raised the decisive question: a runner folds boot's head into its
    system prompt through _trim_onboarding, which cuts the TAIL at a budget (default
    6000 chars) and names what it DROPPED. C1 is deliberately end-placed in the header,
    so its survival is POSITIONAL -- and positional survival that nothing pins is a
    silent failure waiting for the header to grow. Measured 2026-07-25: STANCE landed at
    offset ~5238 of a 10145-char payload, inside the budget but with only ~760 chars of
    margin. This pin fires BEFORE a growing header starts costing seats their stance."""
    head = agent_cli._orientation_header("claude")
    idx = head.find("# STANCE")
    assert idx >= 0, "stance must be in the head at all"
    assert idx < 5200, (
        f"stance sits at offset {idx} in the orientation header; the runner's onboarding "
        "trim budget defaults to 6000 chars and cuts the tail. Something above it grew -- "
        "shorten it, or the fold will silently drop the stance for every runner seat.")


# ---------------------------------------------------------------- W64
def test_p8_heal_folds_by_default():
    """484 UNKNOWN keys led every boot, above the context, tagged not-your-job."""
    lines = [f"[heal][fleet-hygiene] drift line {i}" for i in range(3)]
    out = agent_cli._heal_render(lines, verbose=False)
    assert len(out) == 1, "unowned drift must not lead the boot payload"
    assert "3 drift line(s) folded" in out[0]
    assert "AKASHIC_HEAL_VERBOSE=1" in out[0], "the escape hatch must be named"
    assert "[fleet-hygiene]" in out[0], "W03 scope tag survives the fold"


def test_p9_heal_verbose_restores_full_detail():
    lines = [f"[heal][fleet-hygiene] drift line {i}" for i in range(3)]
    assert agent_cli._heal_render(lines, verbose=True) == lines, "detail is folded, never destroyed"


def test_p10_heal_silent_when_in_sync():
    assert agent_cli._heal_render([], verbose=False) == []
    assert agent_cli._heal_render(None, verbose=False) == []


def test_p7_real_divergence_still_loud(monkeypatch):
    monkeypatch.setattr(delta_mod, "_git_log_range", lambda a, b: None)
    monkeypatch.setattr(delta_mod, "_git_is_forward", lambda a, b: False)
    monkeypatch.setattr(delta_mod, "_git_has_commit", lambda sha: True)
    mark = {"git_commit": "aaaaaaa0000000000000000000000000000000000",
            "ledger_seq": "1", "notes_head": "n", "promoted_id": "p"}
    cur = {"git_commit": "bbbbbbb0000000000000000000000000000000000",
           "ledger_seq": "1", "notes_head": "n", "promoted_id": "p"}
    txt = "\n".join(delta_mod._sections("claude", mark, cur))
    assert "BACKWARDS" in txt and "git log" in txt, "genuine divergence keeps its alarm"
