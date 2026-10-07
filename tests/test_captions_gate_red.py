"""RED pins -- the CAPTIONS GATE, first gate built from the compilability census (bucket a).

PRE-REGISTRATION per M3: committed alone, before any implementation. Every pin fails solely
because `core.recall.gates.captions` does not exist.

THE GOLDEN CASE: lesson `youtube_transcript_is_a_door_verb_not_a_script` -- "the first move
on a video URL is the captions verb" -- named its own moment on 2026-08-22 and failed to fire
at that moment TWICE (2026-08-22 and 2026-08-27, 5.5 days apart, both documented). Both
times a seat reached for WebFetch on a YouTube URL and got footer navigation; both times the
verb existed. This gate is that lesson moved from prose to a surface.

SCOPE, deliberately narrow: ONE lesson, ONE tool, ADVISE-only.
  - It watches WebFetch arguments for video URLs. Bash `curl` of a video URL is OUT of v1
    scope and pinned as such -- declared scope, not silent scope.
  - It ADVISES; it never blocks. Enforcement is a different delivery mode with a different
    cost-of-wrong (the operator's threat axis: a wrong advisory costs a glance, a wrong
    block costs a workflow). decision vocabulary is FIRE | SILENT, nothing else.
  - It is a PURE FUNCTION over (tool_name, tool_args). No clock, no network, no writes.

THE DESIGN LAW IT CARRIES (Kimi's finding, self-adjudication audit 2026-08-28): SILENCE IS A
ROW. Every evaluation returns a verdict record -- SILENT verdicts carry their reason, and
different silences are distinguishable, so the gate's quiet is auditable instead of
self-certified. A gate that logs only its hits reproduces the exact blindness this whole arc
was built to end.
"""

import ast
import importlib
import inspect

import pytest


MODULE = "core.recall.gates.captions"


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover -- the RED state
        pytest.fail(f"{MODULE} does not exist yet (expected while the gate is RED): {exc}")


def _evaluate(tool_name, tool_args):
    mod = _mod()
    if not hasattr(mod, "evaluate"):
        pytest.fail(f"{MODULE}.evaluate is missing")
    return mod.evaluate(tool_name, tool_args)


# ---------------------------------------------------------------------------
# Pin 1 -- the golden case FIRES, teaches the verb, and carries its provenance.
# ---------------------------------------------------------------------------

def test_p1_webfetch_on_a_watch_url_fires_and_teaches():
    v = _evaluate("WebFetch", {"url": "https://www.youtube.com/watch?v=aY92k2DAO0Q",
                               "prompt": "summarize this"})
    assert v["decision"] == "FIRE", v
    assert "captions" in v["message"], (
        f"the whole point is teaching the door verb at the moment of the miss: {v}")
    assert "agent_cli" in v["message"], "the message must give the runnable form, not a hint"
    assert v["lesson"] == "youtube_transcript_is_a_door_verb_not_a_script", (
        f"a gate without provenance is an opinion; it must cite the lesson it enforces: {v}")
    assert v["mode"] == "advise", "v1 advises; it never blocks"


# ---------------------------------------------------------------------------
# Pin 2 -- URL shape coverage: short links, shorts, uppercase hosts, embedded.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://youtu.be/MhMPsO2e8bw",
    "https://www.youtube.com/shorts/abc123DEF45",
    "https://YOUTUBE.COM/watch?v=gT01zWMnylE",
    "http://m.youtube.com/watch?v=x",
])
def test_p2_video_url_shapes_fire(url):
    v = _evaluate("WebFetch", {"url": url})
    assert v["decision"] == "FIRE", (url, v)


# ---------------------------------------------------------------------------
# Pin 3 -- SILENCE IS A ROW: a non-video fetch returns a reasoned verdict, not None.
# ---------------------------------------------------------------------------

def test_p3_non_video_url_is_reasoned_silence_not_absence():
    v = _evaluate("WebFetch", {"url": "https://github.com/amd/skills"})
    assert v["decision"] == "SILENT", v
    assert v["reason"], "a silent verdict without a reason is self-certified quiet"
    assert "video" in v["reason"].lower() or "referent" in v["reason"].lower(), v
    # the negative: silence must still identify the gate that stayed quiet
    assert v["gate"] == "captions", v


# ---------------------------------------------------------------------------
# Pin 4 -- OUT-OF-SCOPE TOOL is a DIFFERENT silence than out-of-scope content.
# ---------------------------------------------------------------------------

def test_p4_scope_silence_is_distinguishable_from_content_silence():
    bash = _evaluate("Bash", {"command": "curl https://www.youtube.com/watch?v=x"})
    fetch = _evaluate("WebFetch", {"url": "https://example.com"})
    assert bash["decision"] == "SILENT" and fetch["decision"] == "SILENT"
    assert bash["reason"] != fetch["reason"], (
        "out-of-scope-tool and no-video-content are different quiets; collapsing them makes "
        "the gate's declared scope invisible from its own record")
    assert "scope" in bash["reason"].lower(), bash


# ---------------------------------------------------------------------------
# Pin 5 -- deterministic, and structurally unable to look elsewhere.
# ---------------------------------------------------------------------------

def test_p5_same_input_same_verdict_and_no_clock_or_randomness():
    a = _evaluate("WebFetch", {"url": "https://youtu.be/x"})
    b = _evaluate("WebFetch", {"url": "https://youtu.be/x"})
    assert a == b, "replay must be exact"

    tree = ast.parse(inspect.getsource(_mod()))
    forbidden = {"random", "secrets", "datetime", "uuid", "time"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not ({a2.name.split(".")[0] for a2 in node.names} & forbidden), (
                "a gate that reads the clock scores the same call differently on replay")
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden


def test_p5b_module_imports_cannot_reach_a_writer():
    tree = ast.parse(inspect.getsource(_mod()))
    allowed = {"__future__", "re", "urllib", "typing", "dataclasses"}
    seen = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            seen.append(node.module.split(".")[0])
    offenders = [s for s in seen if s not in allowed]
    assert not offenders, (
        f"the gate is a pure function over its arguments; these imports give it reach it must "
        f"not have: {offenders}")


# ---------------------------------------------------------------------------
# Pin 6 -- the gate can never break the call it watches.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("args", [
    {},                            # no url at all
    {"url": None},                 # explicit None
    {"url": 42},                   # wrong type
    {"url": ""},                   # empty
    {"prompt": "no url key"},      # unrelated keys only
])
def test_p6_malformed_args_are_reasoned_silence_never_an_exception(args):
    v = _evaluate("WebFetch", args)   # must NOT raise
    assert v["decision"] == "SILENT", (args, v)
    assert v["reason"], (args, v)


# ---------------------------------------------------------------------------
# Pin 7 -- bounded output. Precision at the gate buys density in the pool.
# ---------------------------------------------------------------------------

def test_p7_fire_message_is_bounded():
    v = _evaluate("WebFetch", {"url": "https://www.youtube.com/watch?v=aY92k2DAO0Q"})
    assert len(v["message"]) <= 400, (
        f"an advisory that costs more attention than the mistake it prevents is noise: "
        f"{len(v['message'])} chars")


# ---------------------------------------------------------------------------
# Pin 8 -- no promotion surface. The gate advises; nothing here scores or blocks.
# ---------------------------------------------------------------------------

def test_p8_no_blocking_or_scoring_surface_exists():
    mod = _mod()
    forbidden = {"block", "enforce", "score", "usefulness", "promote", "record_outcome"}
    present = sorted(n for n in dir(mod) if n.lower() in forbidden)
    assert not present, (
        f"v1 is advise-only by declared scope; these names offer a different delivery mode "
        f"without its own gate: {present}")
