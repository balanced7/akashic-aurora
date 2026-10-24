"""The verb guide and its five pushes (core/coord/verb_guide.py, agent/harness/verbs.py).

What these pin, layer by layer:
  1  every live verb has exactly one card (family, trigger line, keywords) and no card
     outlives its verb -- the table cannot drift from the parser
  2  the session map names every verb and fits the hook-context cap beside the whisper;
     the MCP instructions fit their own cap
  3  every verb sits in exactly one generated family skill, and the skills are current
  4  plain requests find their verb, ordinary coding requests find none, and hand-rolled
     shell gets one pointer per verb per session
  5  a verb the operator typed is counted, everyday words are not

Fixture prompts are written in the words an operator uses, not the keywords; the negatives
are the ordinary requests that make up most turns and must stay silent.
"""

import os
import re
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import verb_guide as vg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _live_verbs():
    import agent_cli

    return [v for v, _ in agent_cli.list_verbs("")]


# ------------------------------------------------------------------------------- layer 1
def test_every_live_verb_has_a_card_and_no_card_outlives_its_verb():
    live, cards = set(_live_verbs()), set(vg.load())
    assert live - cards == set(), f"verbs with no use-when line in verb_guide.json: {sorted(live - cards)}"
    assert cards - live == set(), f"cards for verbs the parser no longer has: {sorted(cards - live)}"


def test_cards_are_trigger_phrased_and_well_formed():
    ticket = re.compile(r"\b[TW]\d{2,}\b|\btask \d{2}\b")
    for verb, card in vg.load().items():
        when = card["when"]
        assert card["family"] in vg.FAMILIES, verb
        assert when.startswith("Use when "), f"{verb}: {when!r}"
        assert ": " in when, f"{verb} has no situation/action colon: {when!r}"
        assert len(when) <= 170, f"{verb}: {len(when)} chars"
        assert not ticket.search(when), f"{verb} names a ticket code: {when!r}"
        assert 3 <= len(card["keywords"]) <= 12, verb
        for hr in card["hand_rolled"]:
            re.compile(hr["pattern"])


def test_core_and_common_tiers_name_real_verbs():
    cards = vg.load()
    assert set(vg.CORE) <= set(cards)
    assert set(vg.COMMON) <= set(cards)


def test_discover_searches_the_trigger_lines(capsys):
    import agent_cli

    # "pre-existing" appears in no verb name or parser purpose; only the use-when line has it.
    args = agent_cli.build_parser().parse_args(["discover", "pre-existing", "--json"])
    agent_cli.cmd_discover(args)
    import json

    rows = json.loads(capsys.readouterr().out)
    assert any(r["verb"] == "suite-baseline" for r in rows), rows


# ------------------------------------------------------------------------------- layer 2
def test_map_names_every_verb_and_fits_beside_the_whisper():
    from agent.harness.verbs import HOOK_CONTEXT_CAP, build_verb_map

    whisper_like = 1500
    m = build_verb_map(already=whisper_like)
    assert m.startswith(vg.MARK)
    assert whisper_like + 1 + len(m) <= HOOK_CONTEXT_CAP
    for verb in vg.load():
        assert re.search(rf"(?<![\w-]){re.escape(verb)}(?![\w-])", m), f"map lost {verb}"


def test_map_folds_detail_not_verbs_when_tight():
    tight = vg.render_map("aurora", max_chars=4000)
    assert len(tight) <= 4000
    for verb in vg.load():
        assert re.search(rf"(?<![\w-]){re.escape(verb)}(?![\w-])", tight), f"tight map lost {verb}"
    # the highest-priority verb keeps its trigger longest
    assert "  boot: " in tight


def test_session_start_carries_the_map_in_scope(monkeypatch):
    from agent.harness import context as ctx
    from agent.harness.scope import repo_root

    monkeypatch.delenv("AKASHIC_VERB_MAP", raising=False)
    monkeypatch.setattr(ctx, "_build_whisper", lambda cwd, agent_id, session_id="": "[akashic] DIRECTIVE: x")
    out = ctx.build_autoboot_context(repo_root(), "claude")
    assert out.startswith("[akashic] DIRECTIVE: x\n" + vg.MARK)
    assert len(out) <= 10_000
    monkeypatch.setenv("AKASHIC_VERB_MAP", "0")
    assert ctx.build_autoboot_context(repo_root(), "claude") == "[akashic] DIRECTIVE: x"


def test_session_start_outside_scope_gets_no_map(monkeypatch):
    from agent.harness import context as ctx

    monkeypatch.setattr(ctx, "_build_whisper", lambda cwd, agent_id, session_id="": "")
    monkeypatch.setattr(ctx, "session_in_scope", lambda cwd: False)
    assert ctx.build_autoboot_context("/somewhere/else", "claude") == ""


#: Read the MCP server in a child process. Importing ai_setup_mcp swaps sys.stdout for the
#: server's thread-local proxy, once. Imported inside a test, pytest puts its own sys.stdout back
#: when that test ends, so the proxy is gone for the rest of the run: every later in-process MCP
#: call arms a proxy nothing writes through and returns "(no output)" (test_t060's CLI/MCP
#: comparison read an empty string after this test until it moved out).
#: The probe writes to sys.__stdout__: the proxy routes a plain print from an unarmed thread to
#: stderr by design, so the JSON-RPC channel can never carry a stray line.
_MCP_PROBE = """
import asyncio, json, sys, ai_setup_mcp as door
tools = asyncio.run(door.mcp.list_tools())
sys.__stdout__.write(json.dumps({"instructions": door.mcp.instructions or "",
                  "always": sorted(t.name for t in tools if (t.meta or {}).get("anthropic/alwaysLoad")),
                  "names": sorted(t.name for t in tools)}) + "\\n")
"""


def test_mcp_instructions_fit_their_cap_and_core_tools_stay_loaded():
    import json
    import subprocess

    r = subprocess.run(
        [sys.executable, "-c", _MCP_PROBE], cwd=ROOT, capture_output=True, text=True, timeout=120, check=True
    )
    probe = json.loads(r.stdout.strip().splitlines()[-1])
    instructions = probe["instructions"]
    assert len(instructions) <= 4096
    assert vg.MARK in instructions
    assert "boot(agent, task)" in instructions
    for verb in vg.CORE:
        name = "web_fetch" if verb == "web" else verb.replace("-", "_")
        if name in probe["names"]:
            assert name in probe["always"], name


# ------------------------------------------------------------------------------- layer 3
def test_every_verb_sits_in_exactly_one_family_skill():
    from scripts.generators import gen_verb_skills as gen

    seen: dict[str, str] = {}
    for _fam, path in gen.targets():
        text = Path(path).read_text(encoding="utf-8")
        table = text.split(gen.BEGIN, 1)[1].split(gen.END, 1)[0]
        for verb in re.findall(r"^\| `([\w-]+)` \|", table, re.M):
            assert verb not in seen, f"{verb} in {path} and {seen[verb]}"
            seen[verb] = path
    assert set(seen) == set(vg.load())


def test_family_skills_are_current():
    from scripts.generators import gen_verb_skills as gen

    guide = vg.load()
    for fam, path in gen.targets():
        existing = Path(path).read_text(encoding="utf-8")
        assert gen.render(fam, existing, guide) == existing, f"stale: run gen_verb_skills.py ({path})"


# ------------------------------------------------------------------------------- layer 4
POSITIVE = [
    ("can you check whether this test failure is pre-existing or mine", "suite-baseline"),
    ("fetch https://example.com/docs and summarise it", "web"),
    ("is anyone else editing scripts/bifrost_ui.py right now?", "locks"),
    ("why is deepseek stuck and not answering", "unwedge"),
    ("what did I ask for last week about the shader avatar", "eye"),
    ("get a second opinion from another model on this design", "ask"),
    ("the fleet seems stuck, check everything is running", "doctor"),
    ("leave a handoff for the next agent", "handoff"),
    ("where is that pdf I downloaded yesterday", "find"),
    ("pull the captions from this youtube video", "captions"),
    ("send a message to heimdall asking for review", "bifrost-send"),
    ("what changed since I was last here", "delta"),
    ("why did we decide to use sqlite for the mirror", "lookback"),
    ("record what we learned about the bash heredoc bug as a lesson", "learn"),
    ("has anyone already done this or is a seat working on it", "scout"),
    ("I need you to store my openai api key", "secret"),
]

NEGATIVE = [
    "fix the typo in README",
    "let's refactor the parser to be faster",
    "add a docstring to this function",
    "rename the variable x to count",
    "yes, go ahead",
    "commit this and push",
    "make the button blue",
    "write unit tests for the date parser",
    "explain how this regex works",
    "thanks, looks good",
]


@pytest.mark.parametrize(("prompt", "verb"), POSITIVE)
def test_plain_requests_find_their_verb(prompt, verb):
    got = vg.match_prompt(prompt, k=1)
    assert got, prompt
    assert got[0][0] == verb, got


@pytest.mark.parametrize("prompt", NEGATIVE)
def test_ordinary_requests_stay_silent(prompt):
    assert vg.match_prompt(prompt) == []


def test_a_named_verb_is_not_echoed_back():
    assert all(v != "captions" for v, _ in vg.match_prompt("run `aurora captions` on this youtube video"))


@pytest.mark.parametrize(
    ("command", "verb"),
    [
        ("curl -sL https://example.com/page", "web"),
        ("locate settings.json", "find"),
        ("find / -name '*.pdf' 2>/dev/null", "find"),
        ("redis-cli -p 16379 XRANGE bifrost:inbox:claude - +", "capture"),
    ],
)
def test_hand_rolled_commands_point_at_their_verb(command, verb):
    assert verb in [v for v, _ in vg.hand_rolled(command)]


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "ls -la",
        "curl -s http://localhost:8787/health",
        "uv run agent_cli.py web fetch https://example.com",
        "aurora find thing",
        "grep -rn foo core/",
        "uv run pytest tests/test_verb_guide.py -q",
    ],
)
def test_ordinary_or_house_commands_get_no_hint(command):
    assert vg.hand_rolled(command) == []


def test_action_hint_fires_once_per_verb_per_session(monkeypatch):
    from agent.harness import verbs

    monkeypatch.delenv("AKASHIC_VERB_NUDGE", raising=False)
    monkeypatch.setattr(verbs, "_log", lambda *a, **k: None)
    sid = "test-" + uuid.uuid4().hex
    first = verbs.verb_action_line("curl -sL https://example.com/page", sid)
    assert first.startswith(vg.MARK)
    assert "web fetch" in first
    assert verbs.verb_action_line("wget https://example.org/x", sid) == ""
    monkeypatch.setenv("AKASHIC_VERB_NUDGE", "0")
    assert verbs.verb_action_line("curl -sL https://example.org/y", "test-" + uuid.uuid4().hex) == ""


def test_plan_line_suggests_once_and_counts_reminders(monkeypatch):
    from agent.harness import verbs

    events = []
    monkeypatch.delenv("AKASHIC_VERB_NUDGE", raising=False)
    monkeypatch.setattr(verbs, "_log", lambda *a, **k: None)
    monkeypatch.setattr(
        "core.events.event_log.capture_event", lambda kind, summary, **kw: events.append((kind, kw["detail"]))
    )
    sid = "test-" + uuid.uuid4().hex
    line = verbs.verb_plan_line("pull the captions from this youtube video", sid)
    assert vg.MARK in line
    assert "captions" in line
    assert verbs.verb_plan_line("pull the captions from this youtube video", sid) == ""
    verbs.verb_plan_line("please run `aurora doctor` and then `aurora recall heredoc`", sid)
    assert ("verb_reminder", {"verbs": ["doctor", "recall"]}) in events


# ------------------------------------------------------------------------------- layer 5
@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("run aurora recall heredoc", ["recall"]),
        ("try `uv run agent_cli.py doctor`", ["doctor"]),
        ("use `sift` for that", ["sift"]),
        ("call mcp__akashic-aurora__bifrost_sync first", ["bifrost-sync"]),
        ("find the file and check the status", []),
        ("`find` it", []),
        ('<pasted_content id="x">aurora recall foo</pasted_content id="x"> thanks', []),
    ],
)
def test_mentioned_verbs_counts_commands_not_everyday_words(text, want):
    assert vg.mentioned_verbs(text, vg.load().keys()) == want


def test_awareness_meter_reads_a_transcript(tmp_path):
    import json

    from core.coord import verb_awareness as va

    proj = tmp_path / "projects" / "-x-akashic-labs-aurora"
    proj.mkdir(parents=True)
    rows = [
        {"type": "user", "timestamp": "2026-10-22T10:00:00Z", "message": {"content": "use aurora recall for this"}},
        {
            "type": "attachment",
            "attachment": {
                "type": "hook_additional_context",
                "content": [f"{vg.MARK} x\n  `aurora web fetch <url>` -- y"],
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "aurora web fetch https://e.com"}},
                    {"type": "tool_use", "name": "mcp__akashic-aurora__recall", "input": {"query": "x"}},
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "aurora-research"}},
                ]
            },
        },
    ]
    (proj / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    r = va.measure(list(vg.load()), root=str(tmp_path / "projects"))
    assert (r["sessions"], r["reminders"]) == (1, 1)
    assert (r["verb_calls"], r["distinct_verbs_used"]) == (2, 2)
    assert (r["nudged"], r["nudges_followed"]) == (1, 1)
    assert r["house_skill_invocations"] == 1
