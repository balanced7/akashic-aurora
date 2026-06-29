"""ThemeDiscoverer -- embedding theme inference (Spine v2, V6).

Two layers:
  * deterministic unit tests (FakeEmbedder) for the routing logic (threshold, multi-label,
    max-pool over exemplars, hybrid union, keyword fallback);
  * the ABLATION GATE (real model, skipped if absent) -- the hybrid MUST beat the keyword
    baseline on recall AND F1 on the gold fixture, or V6 doesn't ship.

Run: py -m pytest tests/test_theme_discovery.py -q
"""
import math
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative_metrics import multilabel_prf
from fixtures.narrative_fixture import gold_rows
from core.narrative.theme_assigner import ThemeAssigner
from core.narrative.theme_discovery import ThemeDiscoverer, EXEMPLARS, DEFAULT_TAU, _ctfidf_terms
from core.primitives.embedder import get_embedder


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class FakeEmbedder:
    """Maps registered texts to fixed unit vectors; unknown text -> None (model-miss)."""
    def __init__(self, table):
        self.table = {k: _unit(v) for k, v in table.items()}

    def embed(self, text):
        return self.table.get(text)

    def embed_many(self, texts):
        return [self.table.get(t) for t in texts]


class _StubKW:
    def __init__(self, themes):
        self._t = themes

    def assign(self, beat, hint=None):
        return list(self._t)


# --------------------------------------------------------------- routing logic
def test_route_single_and_below_threshold():
    fe = FakeEmbedder({"a1": [1, 0, 0], "b1": [0, 1, 0], "near_a": [1, 0, 0], "far": [0, 0, 1]})
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"], "beta": ["b1"]})
    assert d.available is True
    assert d.route("near_a") == ["alpha"]
    assert d.route("far") == []


def test_route_multilabel():
    fe = FakeEmbedder({"a1": [1, 0, 0], "b1": [0, 1, 0], "ab": [1, 1, 0]})
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"], "beta": ["b1"]})
    assert d.route("ab") == ["alpha", "beta"]      # cos 0.707 to each, both >= 0.5


def test_max_pool_over_exemplars():
    # the matching beat is near the SECOND exemplar; max-pool must still fire the theme
    fe = FakeEmbedder({"a1": [1, 0, 0], "a2": [0, 0, 1], "near_a2": [0, 0, 1]})
    d = ThemeDiscoverer(embedder=fe, tau=0.9, seeds={"alpha": ["a1", "a2"]})
    assert d.route("near_a2") == ["alpha"]
    assert d.scores("near_a2")["alpha"] == pytest.approx(1.0)


def test_assign_is_hybrid_union():
    beat = SimpleNamespace(summary="alpha beat", source="")
    txt = ThemeAssigner._text_of(beat, None)
    fe = FakeEmbedder({"a1": [1, 0, 0], txt: [1, 0, 0]})
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"]},
                        keyword_assigner=_StubKW(["logging"]))
    assert d.assign(beat) == ["alpha", "logging"]   # embedding theme UNION keyword theme


def test_falls_back_to_keyword_when_model_unavailable():
    fe = FakeEmbedder({})                            # nothing embeds -> not available
    d = ThemeDiscoverer(embedder=fe, seeds={"alpha": ["a1"]}, keyword_assigner=_StubKW(["memory"]))
    assert d.available is False
    assert d.assign(SimpleNamespace(summary="x", source="")) == ["memory"]


# --------------------------------------------------------------- ablation gate (real model)
def _fixture_inputs():
    rows = gold_rows()
    beats = [SimpleNamespace(summary=r["summary"], source=r["source"]) for r in rows]
    hints = [SimpleNamespace(task=r["task"], category=r["category"], paths=r["paths"]) for r in rows]
    gold = [r["gold_themes"] for r in rows]
    return beats, hints, gold


def test_ablation_gate_hybrid_beats_keyword_baseline():
    if not get_embedder().available:
        pytest.skip("embedding model unavailable")
    beats, hints, gold = _fixture_inputs()
    kw = ThemeAssigner()
    kw_pred = [kw.assign(b, h) for b, h in zip(beats, hints)]
    disc = ThemeDiscoverer(tau=DEFAULT_TAU)          # real embedder, frozen tau
    d_pred = [disc.assign(b, h) for b, h in zip(beats, hints)]

    kp, kr, kf = multilabel_prf(gold, kw_pred)
    dp, dr, df = multilabel_prf(gold, d_pred)

    assert dr > kr, f"recall must beat keyword baseline: {dr:.3f} vs {kr:.3f}"
    assert df >= kf, f"F1 must not regress: {df:.3f} vs {kf:.3f}"
    assert dp >= 0.80, f"precision must stay high (no spraying): {dp:.3f}"
    recovered = sum(len((set(g) - set(kp_)) & set(dp_))
                    for g, kp_, dp_ in zip(gold, kw_pred, d_pred))
    assert recovered >= 3, f"must recover keyword-miss beats: {recovered}"


def test_seed_vocab_matches_theme_assigner():
    # discovery seeds must cover exactly the keyword theme vocabulary (no orphan themes)
    from core.narrative.theme_assigner import THEME_KEYWORDS
    kw_ids = {tid for _, tid in THEME_KEYWORDS}
    assert set(EXEMPLARS.keys()) == kw_ids


# --------------------------------------------------------------- V6b: residual discovery
def test_ctfidf_picks_distinctive_terms():
    terms = _ctfidf_terms([
        ["whisper voice transcription", "audio voice separation", "speech voice recognition"],
        ["florence vision ocr", "image vision detection", "screenshot vision scan"],
    ])
    assert "voice" in terms[0] and "vision" in terms[1]


def _discovery_fixture():
    # one seed (alpha=[1,0,0,0]); two NET-NEW domains orthogonal to it, separable from each other
    table = {"a1": [1, 0, 0, 0]}
    voice = ["whisper voice transcription", "audio voice separation",
             "speech voice recognition", "voice activity capture"]
    vision = ["florence vision ocr", "image vision detection",
              "screenshot vision scan", "vision model directml"]
    for t in voice:
        table[t] = [0, 0, 1, 0]
    for t in vision:
        table[t] = [0, 0, 0, 1]
    items = ([{"id": f"v{i}", "text": t} for i, t in enumerate(voice)]
             + [{"id": f"w{i}", "text": t} for i, t in enumerate(vision)])
    return FakeEmbedder(table), items


def test_discover_surfaces_net_new_themes_with_labels():
    fe, items = _discovery_fixture()
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"]})
    found = d.discover(items, min_residual=6)
    assert len(found) == 2
    labels = " ".join(f["label"] for f in found)
    assert "voice" in labels and "vision" in labels
    assert all(f["size"] == 4 for f in found)


def test_discover_cold_start_returns_nothing():
    fe, items = _discovery_fixture()
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"]})
    assert d.discover(items[:3], min_residual=6) == []      # below the floor -> no discovery


def test_discover_excludes_beats_a_seed_claims():
    fe, items = _discovery_fixture()
    fe.table["seeded one"] = _unit([1, 0, 0, 0])             # matches seed alpha
    items = items + [{"id": "seeded", "text": "seeded one"}]
    d = ThemeDiscoverer(embedder=fe, tau=0.5, seeds={"alpha": ["a1"]})
    found = d.discover(items, min_residual=6)
    assert "seeded" not in {bid for f in found for bid in f["beat_ids"]}


def test_discover_empty_when_model_unavailable():
    d = ThemeDiscoverer(embedder=FakeEmbedder({}), seeds={"alpha": ["a1"]})
    assert d.discover([{"id": "x", "text": "anything"}] * 8) == []
