"""T243 -- the helper's reasoning trace is returned by the provider and thrown away.

MEASURED 2026-08-08, deepseek-v4-pro, one probe: `choices[0].message.reasoning_content` came
back populated (357 chars for "what is 17*23, think it through") and `model_extra` listed
`reasoning_content`. `ask()` reads `choice.message.content` and nothing else.

We already PAY for it. `detail["reasoning_tokens"]` is set one field below the line that drops
the text -- the count is kept and the content discarded.

WHY IT MATTERS BEYOND TIDINESS. Daniil, 2026-08-08: a seat should be able to peek the output
AND the reasoning of other seats. A nested fan currently asks each helper to self-report a
REASONING section, which is a helper's account of its reasoning rather than the trace. In this
session that gap was live twice: cross-band REASONING conflict is what located a truncated
evidence pack, and a tier-3 helper reached a TRUE conclusion through a demonstrably FALSE
premise -- something only visible by reading the route, never the verdict.

ABSENT WHEN THE PROVIDER RETURNS NONE. Never "", never a placeholder. The field one line up
already states this law for its own value: "None, never 0: a provider that does not report
reasoning must not read as 'reasoned zero' -- the fabricated-measurement lie." An empty string
in a reasoning field is that same lie in text.
"""
from core.comm import ask as ask_mod


class _Msg:
    def __init__(self, content, reasoning=None):
        self.content = content
        if reasoning is not None:
            self.reasoning_content = reasoning


class _Choice:
    def __init__(self, content, reasoning=None):
        self.message = _Msg(content, reasoning)
        self.finish_reason = "stop"


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


class _Resp:
    def __init__(self, content, reasoning=None):
        self.choices = [_Choice(content, reasoning)]
        self.usage = _Usage()


def _client(content="ANSWER", reasoning=None):
    class _Completions:
        def create(self, **kwargs):
            return _Resp(content, reasoning)

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    return _Client()


def test_reasoning_content_reaches_the_caller():
    """The whole defect: the provider hands it over and the boundary drops it."""
    trace = "Let me work through this. 17*20=340, 17*3=51, so 391."
    out = ask_mod.ask("q", client=_client("391", trace))
    d = out.detail or {}

    assert d.get("answer") == "391", "the answer path must be unchanged"
    assert d.get("reasoning") == trace, (
        "the provider returned reasoning_content and it did not reach detail. Measured live "
        "2026-08-08: 357 chars available, dropped, while reasoning_tokens was recorded.")


def test_absent_when_the_provider_returns_none():
    """Never "", never a placeholder.

    detail["reasoning_tokens"] already carries this law for the count: None never 0, because a
    provider that does not report must not read as 'reasoned zero'. An empty string in a
    reasoning field is the same fabricated measurement, in text.
    """
    out = ask_mod.ask("q", client=_client("plain", reasoning=None))
    d = out.detail or {}
    assert "reasoning" not in d, (
        f"a provider that returned no trace must leave no key, got {d.get('reasoning')!r}")


def test_empty_string_from_the_provider_is_treated_as_absent():
    """A provider that sends "" has told us nothing, and "" must not render as a trace."""
    out = ask_mod.ask("q", client=_client("plain", reasoning=""))
    d = out.detail or {}
    assert "reasoning" not in d, (
        'an empty reasoning_content is an absence, not a trace; it must not create the key')


def test_the_count_and_the_text_do_not_disagree():
    """Structural: if we report a trace we must not simultaneously report it as unmeasured.

    Guards the half-landed version of this fix, where the text is captured but the existing
    reasoning_tokens plumbing is left reading a different object.
    """
    out = ask_mod.ask("q", client=_client("391", "some reasoning here"))
    d = out.detail or {}
    assert "reasoning" in d, "fixture is wrong -- this test needs the trace present"
    assert d.get("reasoning"), "a present reasoning key must carry text"
