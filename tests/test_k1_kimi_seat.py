"""K1 pins (2026-07-18): the kimi seat transport honors its fence-agreed deltas OFFLINE --
request shape, frozen cache prefix, spend-meter math in both cached-token dialects, and the
no-sampling-knobs rule. Fake client injected; no network, no spend."""
import json
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from kimi_chat import KimiAgent, SpendMeter   # noqa: E402


def _resp(content="ok", usage=None):
    msg = types.SimpleNamespace(content=content, reasoning_content="thought",
                                tool_calls=None)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)],
                                 usage=usage or {"prompt_tokens": 10, "completion_tokens": 5})


class FakeClient:
    def __init__(self):
        self.calls = []
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.calls.append(kw)
                return _resp()
        self.chat = types.SimpleNamespace(completions=_Completions())


def _agent(tmp_path, **kw):
    meter = SpendMeter(path=tmp_path / "spend.json", budget=105.0)
    return KimiAgent(instructions="SYSTEM-BLOCK", client=FakeClient(), meter=meter, **kw)


def test_request_shape_and_no_knobs(tmp_path):
    ag = _agent(tmp_path, temperature=0.5, top_p=0.9)   # must warn+ignore, never error
    kw = ag.request_kwargs()
    assert kw["messages"][0] == {"role": "system", "content": "SYSTEM-BLOCK"}
    assert "max_completion_tokens" in kw
    assert "temperature" not in kw and "top_p" not in kw, "sampling knobs are fixed server-side"
    assert "extra_body" not in kw, "effort=max is the server default -- omit (cache-friendly)"
    ag2 = _agent(tmp_path, effort="low")
    assert ag2.request_kwargs()["extra_body"] == {"reasoning_effort": "low"}


def test_cache_prefix_frozen_across_sends(tmp_path):
    calc = [{"type": "function", "function": {"name": "calc", "description": "d",
             "parameters": {"type": "object", "properties": {}}}}]
    ag = _agent(tmp_path, tools_schemas=calc)
    ag.send("one")
    ag.send("two")
    kws = ag._client.calls
    assert len(kws) == 2
    sys0 = kws[0]["messages"][0]
    sys1 = kws[1]["messages"][0]
    assert sys0 == sys1 == {"role": "system", "content": "SYSTEM-BLOCK"}, "prefix must be byte-stable"
    assert json.dumps(kws[0]["tools"]) == json.dumps(kws[1]["tools"]), "tool defs must never mutate"
    # append-only history: request 2 begins with request 1's messages verbatim
    m0, m1 = kws[0]["messages"], kws[1]["messages"]
    assert m1[:len(m0)] == m0, "history must be append-only (cache contract)"


def test_meter_math_both_dialects(tmp_path):
    m = SpendMeter(path=tmp_path / "s.json", budget=105.0)
    assert abs(m.record({"prompt_tokens": 1_000_000, "completion_tokens": 0}) - 3.00) < 1e-6
    assert abs(m.record({"prompt_tokens": 1_000_000, "completion_tokens": 0,
                         "cached_tokens": 1_000_000}) - 0.30) < 1e-6
    assert abs(m.record({"prompt_tokens": 1_000_000, "completion_tokens": 0,
                         "prompt_tokens_details": {"cached_tokens": 1_000_000}}) - 0.30) < 1e-6
    assert abs(m.record({"prompt_tokens": 0, "completion_tokens": 1_000_000}) - 15.00) < 1e-6
    assert m.spent() > 18.0 and not m.warn()
    m.state["spent_usd"] = 96.0
    assert m.warn() and m.exceeded_hard_limit()


def test_meter_durable_across_instances(tmp_path):
    p = tmp_path / "s.json"
    m1 = SpendMeter(path=p, budget=105.0)
    m1.record({"prompt_tokens": 1_000_000, "completion_tokens": 0})
    m2 = SpendMeter(path=p, budget=105.0)
    assert abs(m2.spent() - 3.00) < 1e-6, "spend must survive restarts"


def test_thinking_stripped_and_traced(tmp_path):
    traces = []
    ag = _agent(tmp_path)
    ag.on_trace = lambda kind, text: traces.append((kind, text))
    out = ag.send("hi")
    assert out == "ok", "reasoning_content must never leak into the answer"
    assert ("think", "thought") in traces, "thinking must stream to the trace seam"
