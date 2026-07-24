"""T090 pins: sol_chat transport shape -- OFFLINE (no network, no key). Receipts these encode:
docs/library/design/20260717_sol-gpt-5-6-live-api-probe-receipts-2026_ae0409.md (params) + the C3-1-style injection seams."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sol_chat
from sol_chat import SolTransport, preview_401_retry, to_responses_tools


def test_effort_ladder_matches_api_receipt():
    # API error enumerated exactly these on 2026-07-17; 'max' (aggregator claim) is absent.
    assert sol_chat.EFFORTS == ("none", "low", "medium", "high", "xhigh")


def test_tool_conversion_chat_nested_to_flat():
    flat = to_responses_tools([{"type": "function", "function": {
        "name": "calc", "description": "d", "parameters": {"type": "object"}}}])
    assert flat == [{"type": "function", "name": "calc", "description": "d",
                     "parameters": {"type": "object"}}]


def test_tool_conversion_flat_passthrough_and_hosted_untouched():
    src = [{"type": "function", "name": "calc", "description": "", "parameters": {}},
           {"type": "web_search"}]
    assert to_responses_tools(src) == src
    assert to_responses_tools(None) is None


def test_tool_conversion_rejects_garbage():
    with pytest.raises(ValueError):
        to_responses_tools([{"type": "function", "nonsense": True}])


class _Boom(Exception):
    pass


def test_preview_401_retry_recovers():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise _Boom()
        return "ok"

    assert preview_401_retry(flaky, retries=3, exception_cls=_Boom, sleep_s=0) == "ok"
    assert len(attempts) == 3


def test_preview_401_retry_exhausts_loudly():
    def dead():
        raise _Boom()

    with pytest.raises(_Boom):
        preview_401_retry(dead, retries=2, exception_cls=_Boom, sleep_s=0)


def test_transport_validates_knobs():
    with pytest.raises(ValueError):
        SolTransport(effort="max")        # aggregator fiction must fail loud
    with pytest.raises(ValueError):
        SolTransport(verbosity="terse")


def test_request_kwargs_shape_is_the_probe_verified_shape():
    t = SolTransport(model="gpt-5.6-sol", effort="low", verbosity="low",
                     max_output_tokens=1234, service_tier="flex", client=object())
    kw = t.request_kwargs("SYS", [{"role": "user", "content": "hi"}],
                          tools=[{"type": "function", "function": {"name": "f", "parameters": {}}}])
    assert kw["store"] is False                      # RB-26: substrate owns conversation truth
    assert kw["max_output_tokens"] == 1234           # max_tokens is DEAD on this model
    assert kw["reasoning"] == {"effort": "low"}
    assert kw["text"] == {"verbosity": "low"}
    assert kw["service_tier"] == "flex"
    assert kw["instructions"] == "SYS"
    assert kw["tools"][0]["name"] == "f"
    assert "temperature" not in kw                   # locked at 1 -- never send it


def test_extract_pairs_calls_for_stateless_resend():
    class Item:
        type = "function_call"
        call_id, name, arguments = "c1", "calc", '{"expr":"6*7"}'

    class Resp:
        output = [Item()]
        output_text = ""

    text, calls, items = SolTransport.extract(Resp())
    assert calls == [{"call_id": "c1", "name": "calc", "arguments": {"expr": "6*7"}}]
    assert items and items[0].call_id == "c1"        # raw items preserved for history
