"""
Regression: the faithfulness metric must handle source pointers that contain parentheses.

A learning recorded with a parenthesised name yields a beat source like
`learn:experiment:...(prior art)`. The old metric regex truncated at the first ')', captured a
partial string that no longer matched the real source, and falsely reported faithful=False.
Surfaced by the S1 dogfood on canonical (the rendered story was actually faithful).

Run: py -m pytest tests/test_chronicler_faithfulness.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint
from core.narrative.chronicler import Chronicler
from core.primitives.distiller import Distiller, Distillation


def _chron(store):
    return Chronicler(beat_log=BeatLog(store), store=store, chronicle_dir=tempfile.mkdtemp(prefix="cf_"))


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def test_source_with_parens_is_faithful():
    store = _store(); bl = BeatLog(store)
    # a learning-style source whose name carries parentheses (the canonical failure case)
    src = "learn:experiment:Salience promotion is the reflection/consolidation layer (prior art)"
    bl.emit("learning", "Salience promotion reflection layer", src,
            at="2026-01-01T01:00:00", hint=RouteHint(category="research"))
    rep = _chron(store).chronicle_all(now="2026-01-02T00:00:00")
    assert rep["total_beats"] == 1
    assert rep["faithful"] is True, "a parenthesised source must still resolve -> faithful"


def test_hallucinated_source_still_caught():
    """The fix must not weaken the gate: a fabricated source still fails faithfulness."""
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "real", "git:real", at="2026-01-01T01:00:00", hint=RouteHint(paths=["core/x.py"]))

    def lying_writer(items, budget, instruction):
        return Distillation(skeleton="- fabricated  (source: git:HALLUCINATED)",
                            entries=[{"summary": "fab", "source": "git:HALLUCINATED"}],
                            included_sources=["git:HALLUCINATED"], dropped_sources=[],
                            approx_tokens=5, critic_ok=True)

    chron = Chronicler(beat_log=BeatLog(store), store=store, distiller=Distiller(writer=lying_writer),
                       chronicle_dir=tempfile.mkdtemp(prefix="cf2_"))
    rep = chron.chronicle_all(now="2026-01-02T00:00:00")
    assert rep["faithful"] is False, "a hallucinated source must still be caught"


if __name__ == "__main__":
    test_source_with_parens_is_faithful()
    test_hallucinated_source_still_caught()
    print("FAITHFULNESS-PARENS REGRESSION TESTS PASSED")
