"""T090 pins: SolAgent tool loop -- OFFLINE (fake transport, no network, no key)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sol_chat import SolAgent


class _Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _call(call_id, name, arguments):
    return _Item(type="function_call", call_id=call_id, name=name, arguments=arguments)


def _final(text, usage=None):
    r = _Item(output=[_Item(type="message")], output_text=text)
    if usage:
        r.usage = _Item(**usage)
    return r


def _tool_resp(*calls, usage=None):
    r = _Item(output=list(calls), output_text="")
    if usage:
        r.usage = _Item(**usage)
    return r


class FakeTransport:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def respond(self, instructions, history, tools=None):
        self.calls.append({"instructions": instructions, "history": list(history), "tools": tools})
        return self.script.pop(0)


def test_tool_roundtrip_dispatch_and_pairing():
    ft = FakeTransport([_tool_resp(_call("c1", "read_file", '{"path": "x.md"}')),
                        _final("answer done")])
    seen = []
    ag = SolAgent(ft, instructions="SYS", tools_schemas=[{"type": "function", "name": "read_file",
                                                          "description": "", "parameters": {}}],
                  dispatch=lambda n, a: seen.append((n, a)) or "CONTENT", max_hops=5)
    out = ag.send("read x.md")
    assert out == "answer done"
    assert seen == [("read_file", {"path": "x.md"})]
    fco = [h for h in ag.history if isinstance(h, dict) and h.get("type") == "function_call_output"]
    assert len(fco) == 1 and fco[0]["call_id"] == "c1"
    assert fco[0]["output"].startswith("[hop 1/5] CONTENT")
    # stateless resend: the model's function_call item echoed back into history verbatim
    assert any(getattr(h, "type", "") == "function_call" for h in ag.history)


def test_no_tools_returns_final_immediately():
    ft = FakeTransport([_final("plain answer")])
    ag = SolAgent(ft, instructions="SYS")
    assert ag.send("hi") == "plain answer"
    assert len(ft.calls) == 1


def test_interrupt_short_circuits_before_model_call():
    ft = FakeTransport([_final("never reached")])
    ag = SolAgent(ft, instructions="SYS", interrupt=lambda: True)
    out = ag.send("hi")
    assert "paused" in out
    assert ft.calls == []


def test_hop_budget_exhaustion_is_loud():
    ft = FakeTransport([_tool_resp(_call(f"c{i}", "t", "{}")) for i in range(2)])
    ag = SolAgent(ft, instructions="SYS",
                  tools_schemas=[{"type": "function", "name": "t", "description": "", "parameters": {}}],
                  dispatch=lambda n, a: "ok", max_hops=2)
    out = ag.send("go")
    assert "exhausted at 2 hops" in out


def test_dispatch_error_becomes_tool_result_not_crash():
    def boom(n, a):
        raise RuntimeError("nope")

    ft = FakeTransport([_tool_resp(_call("c1", "t", "{}")), _final("recovered")])
    ag = SolAgent(ft, instructions="SYS",
                  tools_schemas=[{"type": "function", "name": "t", "description": "", "parameters": {}}],
                  dispatch=boom, max_hops=3)
    assert ag.send("go") == "recovered"
    fco = [h for h in ag.history if isinstance(h, dict) and h.get("type") == "function_call_output"]
    assert "ERROR: RuntimeError: nope" in fco[0]["output"]


def test_usage_accumulates_responses_shape():
    ft = FakeTransport([_tool_resp(_call("c1", "t", "{}"), usage={"input_tokens": 10, "output_tokens": 2}),
                        _final("done", usage={"input_tokens": 20, "output_tokens": 5})])
    ag = SolAgent(ft, instructions="SYS",
                  tools_schemas=[{"type": "function", "name": "t", "description": "", "parameters": {}}],
                  dispatch=lambda n, a: "ok", max_hops=3)
    ag.send("go")
    assert (ag.input_tokens, ag.output_tokens) == (30, 7)


def test_steer_inject_folds_between_hops():
    facts = [["new constraint"], []]
    ft = FakeTransport([_tool_resp(_call("c1", "t", "{}")), _final("done")])
    ag = SolAgent(ft, instructions="SYS",
                  tools_schemas=[{"type": "function", "name": "t", "description": "", "parameters": {}}],
                  dispatch=lambda n, a: "ok", inject=lambda: facts.pop(0), max_hops=3)
    ag.send("go")
    steers = [h for h in ag.history if isinstance(h, dict) and "STEER" in str(h.get("content", ""))]
    assert len(steers) == 1
