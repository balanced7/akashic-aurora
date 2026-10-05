"""G4.P2 S latent fix (ADV-034): `py scripts/gemini_chat.py --smoke` raised NameError.

The smoke built its agents with `geminiAgent(...)`, but the class is `GeminiAgent`, so the manual
transport smoke died before its first request. The smoke runs here with its network-touching names
(SpendMeter, GeminiAgent) swapped for offline fakes.
"""

from typing import Any, ClassVar

import pytest

from scripts import gemini_chat


class _FakeMeter:
    def reconcile(self, **_kw: Any) -> None:
        return None

    def status_line(self) -> str:
        return "meter ok"


class _FakeUsage:
    def model_dump(self) -> dict[str, int]:
        return {"total_tokens": 0}


class _FakeResponse:
    usage = _FakeUsage()


class _FakeAgent:
    built: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, **kw: Any) -> None:
        _FakeAgent.built.append(kw)
        self.last_response = _FakeResponse()

    def send(self, text: str) -> str:
        return f"echo: {text}"


def test_smoke_builds_its_agents_with_the_real_class_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both smoke agents are built through GeminiAgent and the smoke runs to its last line."""
    monkeypatch.setattr(_FakeAgent, "built", [])
    monkeypatch.setattr(gemini_chat, "SpendMeter", _FakeMeter)
    monkeypatch.setattr(gemini_chat, "GeminiAgent", _FakeAgent)
    gemini_chat._smoke()  # NameError: name 'geminiAgent' is not defined, before the fix
    assert len(_FakeAgent.built) == 2
    assert _FakeAgent.built[1]["tools_schemas"][0]["function"]["name"] == "calc"
    assert "== smoke complete ==" in capsys.readouterr().out
