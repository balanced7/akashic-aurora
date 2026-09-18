"""floors exemption pins: a declared expected-absence must be DECLARED, COUNTED and still
MEASURED -- never a silent skip.

The live case: `visualizer-builtin` renders an empty canvas because it has no shader source,
so `not_dead` fires on frames that are behaving exactly as designed. Three of the four failures
in the preset-bank census (2026-09-17) were that one class. The cheap wrong fix is a floor
exception list; the disease this house keeps paying for is an absence that renders as normal,
so the mechanism is built the other way round: the floor still runs, the number is still
printed, the frame is labelled `exempt` with its reason and owner, and the summary counts
exemptions SEPARATELY from passes and failures.
"""
from __future__ import annotations

import numpy as np
import pytest

import av

from arsenal import floors as F


def _png(path, array):
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), mode="w", format="image2") as out:
        stream = out.add_stream("png", rate=1)
        stream.width, stream.height, stream.pix_fmt = array.shape[1], array.shape[0], "rgb24"
        for packet in stream.encode(av.VideoFrame.from_ndarray(array, format="rgb24")):
            out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return path


def _black(value=4, shape=(120, 240, 3)):
    return np.full(shape, value, dtype=np.uint8)


def _alive(shape=(120, 240, 3)):
    frame = np.full(shape, 6, dtype=np.uint8)
    frame[40:80, 60:180] = np.array([90, 70, 190], dtype=np.uint8)
    return frame


def _decl(**over):
    base = {
        "match": ["presetbank/visualizer-builtin"],
        "floors": ["not_dead"],
        "reason": "the builtin visualizer has no shader source, so an empty canvas is the "
                  "declared expectation rather than a defect",
        "owner": "asta",
        "date": "2026-09-17",
    }
    base.update(over)
    return {"visualizer-builtin-blank": base}


def test_the_shipped_table_is_empty_until_an_owner_declares_one():
    """The mechanism ships, the exemptions do not. An exemption is a judgement about someone
    else's expected output, so the house ships the shape and the first real entry is the
    owner's act. This pin is the tripwire: adding a declaration means editing this number."""
    assert F.EXEMPTIONS == {}
    assert len(F.EXEMPTIONS) == 0


def test_a_declaration_without_a_reason_is_refused():
    bad = _decl(reason="")
    with pytest.raises(ValueError) as err:
        F.validate_declarations(bad)
    assert "reason" in str(err.value)


def test_a_declaration_without_an_owner_or_date_is_refused():
    with pytest.raises(ValueError):
        F.validate_declarations(_decl(owner=""))
    with pytest.raises(ValueError):
        F.validate_declarations(_decl(date=""))


def test_a_declaration_naming_an_unknown_floor_is_refused():
    """A typo'd floor name must be an ERROR, not a declaration that silently exempts nothing --
    that is the same disease (an absence rendering as normal) wearing a config file."""
    with pytest.raises(ValueError) as err:
        F.validate_declarations(_decl(floors=["not_dead2", "definitely_not_a_floor"]))
    assert "definitely_not_a_floor" in str(err.value)


def test_an_exempted_frame_keeps_its_measurement_and_is_labelled_exempt(tmp_path):
    path = _png(tmp_path / "presetbank" / "visualizer-builtin" / "frame.png", _black())
    receipt = F.check(str(path), floors=["not_dead"], exemptions=_decl())
    entry = next(r for r in receipt["results"] if r["floor"] == "not_dead")
    assert entry["pass"] is False                                   # the measurement stands
    assert entry["measured"]["mean"] < entry["min_mean"]           # and the number is printed
    assert entry["exempt"]["id"] == "visualizer-builtin-blank"     # with its declaration
    assert "no shader source" in entry["exempt"]["reason"]
    assert entry["exempt"]["owner"] == "asta"
    assert receipt["pass"] is False                                 # raw truth is unchanged
    assert receipt["verdict"] == "exempt"                           # the honest label


def test_an_exemption_excuses_only_the_floors_it_names(tmp_path):
    """The same frame's OTHER floors still fail: a declaration is scoped, not a mute button."""
    path = _png(tmp_path / "presetbank" / "visualizer-builtin" / "frame.png", _black())
    receipt = F.check(str(path), floors=["not_dead", "variety"], exemptions=_decl())
    assert receipt["verdict"] == "fail"
    assert next(r for r in receipt["results"] if r["floor"] == "variety")["pass"] is False


def test_an_exemption_does_not_reach_a_frame_it_does_not_match(tmp_path):
    path = _png(tmp_path / "presetbank" / "some-other-preset" / "frame.png", _black())
    receipt = F.check(str(path), floors=["not_dead"], exemptions=_decl())
    assert receipt["verdict"] == "fail"
    assert "exempt" not in receipt["results"][0]


def test_opt_out_is_real(tmp_path):
    """A lane that wants today's raw red passes exemptions=[]; an empty declaration set is
    NOT the same request as the default, and that difference has to be observable."""
    path = _png(tmp_path / "presetbank" / "visualizer-builtin" / "frame.png", _black())
    receipt = F.check(str(path), floors=["not_dead"], exemptions=[])
    assert receipt["verdict"] == "fail"
    assert receipt["exemptions"]["declared"] == []


def test_summarise_counts_exemptions_separately_and_names_its_blind_spot(tmp_path):
    exempted = _png(tmp_path / "presetbank" / "visualizer-builtin" / "frame.png", _black())
    dead = _png(tmp_path / "presetbank" / "other-preset" / "frame.png", _black())
    alive = _png(tmp_path / "presetbank" / "healthy-preset" / "frame.png", _alive())
    receipts = F.check_many([str(exempted), str(dead), str(alive)],
                            floors=["not_dead", "variety"],
                            # the frame-level label is all-or-nothing: a declaration has to
                            # cover EVERY failing floor of the frame for it to read `exempt`
                            exemptions=_decl(floors=["not_dead", "variety"]))
    summary = F.summarise(receipts)
    assert summary["frames"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 2                  # raw failures: the exempted frame is one
    assert summary["exempt"] == 1                  # counted on its own line, never folded in
    assert summary["exempted_floors"] == {"not_dead": 1, "variety": 1}
    assert summary["declarations_used"]["visualizer-builtin-blank"] == 1
    assert any("exempt" in note for note in summary["blind"])


def test_a_declaration_that_matched_nothing_is_reported_not_forgotten(tmp_path):
    """A stale declaration silently doing nothing is the mirror disease of a silent skip:
    the reason it was written may be gone, and nothing would say so."""
    path = _png(tmp_path / "presetbank" / "healthy-preset" / "frame.png", _alive())
    receipts = F.check_many([str(path)], floors=["not_dead"], exemptions=_decl())
    summary = F.summarise(receipts)
    assert summary["declarations_used"] == {}
    assert summary["declarations_unused"] == ["visualizer-builtin-blank"]
