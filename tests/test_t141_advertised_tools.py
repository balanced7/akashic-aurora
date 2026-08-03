"""PRE-REGISTERED ACCEPTANCE (T141) -- a doc that names a TOOL must name one that exists.

MEASURED 2026-08-03 by a five-seat DeepSeek round on the wiring/verb/tools surface. The COLD SEAT
(deepseek-ui, read-only by grant) was asked to do three ordinary things using only the discovery
surfaces a newcomer gets. It could not complete STEP ONE:

    AGENTS.md:18   py agent_cli.py boot <your_agent_id> --task "..."

It has no shell. `run_command` is gated by allow_exec/trust plus the ACL families door, and
security/acl.json quarantines unlisted agents to read-only BY DEFAULT -- so the default new agent
cannot run the first command the door contract gives it. The capability it needed existed the whole
time: `knowledge_boot` at core/comm/toolbox.py:486. AGENTS.md contained ZERO mentions of the tool
surface -- not knowledge_boot, not knowledge_learn, not toolbox.

That is this repo's own signature defect seen from the other side. check_wiring hunts capability
with no door pointing at it; this is a DOOR with no pointer to the capability. The fix (a two-door
fork at the top of AGENTS.md) is one edit and would drift back in a month, so it gets a guard.

check_advertised_verbs.py already enforces the shell half: every `py agent_cli.py <verb>` in live
code must resolve. Nothing enforced the tool half. These pins are that twin.

WHY THE MATCHING IS NAMESPACE-SCOPED, and not "any identifier that looks like a tool". Prefixes with
only ONE real tool (read_, write_, list_, run_) are ordinary English in this codebase --
`write_tombstone`, `read_verdict`, `list_parked` are core functions, not tools. Flagging those
would produce exactly the false-positive flood that makes a guard get silenced. So only genuine
NAMESPACES count -- a prefix carrying two or more real tools (bifrost_, knowledge_, git_, memory_).
Same reasoning the sibling gate records twice: a guard that cries wolf gets fed exceptions until it
guards nothing.

  T1  a doc naming a tool that does not exist is REPORTED
  T2  a doc naming a real tool is NOT reported
  T3  a filename is not a tool call            (scripts/bifrost_runner_deepseek.py must not flag)
  T4  single-tool prefixes are not a namespace (write_tombstone must not flag)
  T5  AGENTS.md names the tool-surface door    (regression guard for the fix that prompted this)

Run: py -m pytest tests/test_t141_advertised_tools.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_advertised_tools as cat  # noqa: E402


def _doc(tmp_path, text, name="D.md"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_t1_a_nonexistent_tool_is_reported(tmp_path):
    d = _doc(tmp_path, "To get oriented, call `knowledge_bootstrap(task)` first.\n")
    bad = cat.scan([d])
    assert any(n == "knowledge_bootstrap" for _f, n, _ln in bad), (
        "a doc that tells a newcomer to call a tool which does not exist strands them exactly "
        "the way AGENTS.md stranded the cold seat")


def test_t2_a_real_tool_is_not_reported(tmp_path):
    d = _doc(tmp_path, "Call `knowledge_boot(task)`, then `bifrost_send(to=...)`.\n")
    assert cat.scan([d]) == []


def test_t3_a_filename_is_not_a_tool_call(tmp_path):
    """scripts/bifrost_runner_deepseek.py shares the bifrost_ namespace and is a FILE. The guard
    must not report the repo's own runner scripts as missing tools."""
    d = _doc(tmp_path, "The runner lives at scripts/bifrost_runner_deepseek.py and rides the bus.\n")
    assert cat.scan([d]) == []


def test_t4_single_tool_prefixes_are_not_a_namespace(tmp_path):
    """`write_` has exactly one tool (write_file), so write_tombstone is ordinary code vocabulary.
    Treating it as a namespace would flood the guard with core function names."""
    d = _doc(tmp_path, "wake_seat.write_tombstone() records the death; read_verdict() reads it.\n")
    assert cat.scan([d]) == []


def test_t5_agents_md_names_the_tool_surface_door():
    """The fix this file exists to protect. A read-only agent must find its door in the contract."""
    text = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8", errors="replace").read()
    assert "knowledge_boot" in text, (
        "AGENTS.md gives a shell command as step 1 and the default new agent has no shell -- "
        "it must name the tool-surface door too")


def test_t6_the_real_docs_advertise_no_missing_tools():
    """Against the live tree: the contract docs must not name a tool that does not exist."""
    docs = [os.path.join(ROOT, f) for f in ("AGENTS.md", "README.md")]
    docs = [d for d in docs if os.path.exists(d)]
    bad = cat.scan(docs)
    assert not bad, f"docs advertise tool(s) that do not exist: {bad}"
