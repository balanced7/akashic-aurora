"""T081-W4 pins (claude / sync surface) -- the SHARED trace-collapse helper.

Reconciled 2026-07-16 to deepseek's consecutive-run algorithm (rsyslog pmlastmsg): the helper
agent/bifrost_pull.render_collapsed is shared by the CLI bifrost-sync AND the runner's
bifrost_inbox, so the two surfaces never diverge. Distinct filename (sync) after the concurrent
two-writer clobber on the generic test_t081_w4_trace_collapse.py (lesson: concurrent_test_file_clobber).
"""
from agent import bifrost_pull as bp


def _m(kind, frm="deepseek", content="x", meta=None):
    return {"kind": kind, "frm": frm, "content": content, "meta": meta or {}}


def _join(msgs, **kw):
    return "\n".join(bp.render_collapsed(msgs, **kw))


def test_all_work_verbatim_in_order():
    out = bp.render_collapsed([_m("handoff", content="a"), _m("reply", content="b")])
    assert out == ["[handoff] from deepseek: a", "[reply] from deepseek: b"]


def test_consecutive_traces_first_shown_rest_counted():
    out = _join([_m("trace", content=f"t{i}") for i in range(5)])
    assert "[trace] from deepseek: t0" in out
    assert "4 more trace(s) from deepseek" in out
    assert "t1" not in out and "t4" not in out
    assert "--traces to expand" in out


def test_singleton_trace_no_more_line():
    out = _join([_m("trace", content="lone")])
    assert "lone" in out and "more" not in out


def test_work_breaks_trace_run():
    msgs = [_m("trace", content="a1"), _m("trace", content="a2"), _m("trace", content="a3"),
            _m("handoff", frm="claude", content="H"),
            _m("trace", content="b1"), _m("trace", content="b2")]
    out = _join(msgs)
    assert "[handoff] from claude: H" in out
    assert "2 more trace(s) from deepseek" in out
    assert "1 more trace(s) from deepseek" in out
    assert "a2" not in out and "a3" not in out


def test_mixed_trace_kinds_separate_runs():
    out = _join([_m("thinking", frm="claude", content="k1"),
                 _m("thinking", frm="claude", content="k2"),
                 _m("tool", frm="claude", content="l1")])
    assert "1 more thinking(s) from claude" in out
    assert "l1" in out          # a fresh run for the tool kind
    assert "k2" not in out


def test_show_traces_expands_in_original_order():
    msgs = [_m("handoff", content="H"), _m("trace", content="t1"), _m("trace", content="t2")]
    assert bp.render_collapsed(msgs, show_traces=True) == [
        "[handoff] from deepseek: H", "[trace] from deepseek: t1", "[trace] from deepseek: t2"]


def test_work_shown_before_traces():
    out = bp.render_collapsed([_m("trace", content="t1"), _m("handoff", frm="claude", content="H")])
    assert out[0] == "[handoff] from claude: H"
    assert any("t1" in l for l in out)


def test_display_only_meta_folds_even_work_kind():
    out = _join([_m("chat", meta={"display_only": True}, content="c1"),
                 _m("chat", meta={"display_only": True}, content="c2")])
    assert "1 more chat(s)" in out and "c2" not in out


def test_accepts_message_objects_not_just_dicts():
    class Msg:
        def __init__(self, kind, frm, content):
            self.kind, self.frm, self.content, self.meta = kind, frm, content, {}
    out = "\n".join(bp.render_collapsed([Msg("trace", "deepseek", "o1"),
                                         Msg("trace", "deepseek", "o2")]))
    assert "o1" in out and "1 more trace(s) from deepseek" in out


def test_lossless_expand_shows_every_message():
    msgs = [_m("handoff"), _m("reply"), _m("inform")] + [_m("trace", content=f"t{i}") for i in range(4)]
    assert any("3 more trace(s)" in l for l in bp.render_collapsed(msgs))
    assert len(bp.render_collapsed(msgs, show_traces=True)) == 7   # nothing dropped
