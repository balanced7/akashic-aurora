"""W159 pins: what differs between two worlds, minus what SHOULD differ.

Daniil, 2026-08-14: "should we have some kind of snapshot delta comparison tool between
prod, beta and alpha? so we can tell at a glance what is the same and what isn't?"

WHY A RAW DIFF IS WORSE THAN NOTHING HERE, measured before building:

    prefix       prod    alpha
    learn:       1061     1060     <- 1 key of real divergence
    mem:          563      559     <- 4
    narr:        3730     3725     <- 5
    artifact:    1264     1264     <- 0
    bifrost:     8276        0     <- EXPECTED: the seed refuses transport
    events:      4884        0     <- EXPECTED: opt-in
    recall:       803        0     <- EXPECTED: opt-in

A naive differ reports ~14,060 differences and buries ~10 real findings under 13,963
expected ones. core/coord/compare.py already names this failure in its own docstring --
"a large, confident, meaningless difference -- worse than an error, because it looks like
a finding" -- and this slice is that warning applied to the world axis.

THE ORACLE FOR "EXPECTED" ALREADY EXISTS: the seed manifest (W156g) records which prefixes
were carried and which were refused, so the tool does not need a hand-maintained list of
what ought to differ. A world that was never seeded has no oracle, and says so rather than
guessing.

THE TWO-SIDED RULE, which is the whole reason this earns its keep. A refused prefix that is
ABSENT in the target is expected and silent. A refused prefix that is PRESENT is the loudest
finding the tool can make -- something bypassed the seed. That is not hypothetical: on
2026-08-14 a restore drill wrote prod's full snapshot into alpha and imported 7,870
bifrost:* keys the seed exists to refuse. Nothing noticed until a human looked.
"""
import pytest

from core.coord import world_diff as WD


# ------------------------------------------------------------------ the oracle

def _manifest(carried=("learn:", "mem:"), refused=("bifrost:", "events:")):
    return {
        "source_world": "prod", "target_world": "alpha",
        "seeded_at": "2026-08-14T02:00:00+00:00",
        "carried": {p: 100 for p in carried},
        "refused": {p: "reason" for p in refused},
        "total_carried": 100 * len(carried),
    }


def test_o1_a_refused_prefix_absent_in_the_target_is_EXPECTED():
    v = WD.classify("bifrost:", present_in_target=False, manifest=_manifest())
    assert v.expected is True
    assert v.severity == "silent"


def test_o2_a_BULK_import_into_a_refused_plane_is_the_loudest_finding():
    """The restore-contamination case, 2026-08-14: a full-fidelity restore into a twin
    imported 7,870 bifrost:* keys against prod's 8,276, and nothing noticed."""
    v = WD.classify("bifrost:", present_in_target=True, manifest=_manifest(),
                    n_source=8276, n_target=7870)
    assert v.expected is False
    assert v.severity == "alarm"
    assert "bulk" in v.why.lower()


def test_o2b_a_LIVE_twins_own_transport_is_not_an_alarm():
    """FOUND BY RUNNING IT on the second world. Presence alone was the original rule, and
    it cried wolf within minutes: booting one seat in beta created bifrost:seatseen:<its
    own sid> and a handful of events -- the twin having a life, which is the whole point of
    standing it up. An alarm that fires on normal operation trains the reader to ignore it,
    which is the same argument that shaped last night's env guard."""
    v = WD.classify("bifrost:", present_in_target=True, manifest=_manifest(),
                    n_source=8281, n_target=2)
    assert v.severity == "report"
    assert "own activity" in v.why.lower()


def test_o2c_name_overlap_is_NOT_the_discriminator():
    """Recorded as a pin because it was my second wrong theory. Structural key names like
    events:raw exist in BOTH worlds independently -- same schema, not same data -- so an
    overlap test would have flagged a clean twin just as loudly. Proportion is the signal;
    this pin exists so nobody re-derives the overlap idea and 'fixes' it back."""
    clean = WD.classify("events:", True, _manifest(), n_source=4884, n_target=4)
    dirty = WD.classify("events:", True, _manifest(), n_source=4884, n_target=4700)
    assert clean.severity == "report" and dirty.severity == "alarm"


def test_o3_a_carried_prefix_that_differs_is_ordinary_divergence():
    """learn: was carried, so the twin having drifted from prod is the NORMAL state of two
    institutions -- reportable, not alarming."""
    v = WD.classify("learn:", present_in_target=True, manifest=_manifest())
    assert v.expected is False
    assert v.severity == "report"


def test_o4_a_carried_prefix_MISSING_entirely_is_a_finding():
    """Carried at seed time and gone now means the twin lost something it was given."""
    v = WD.classify("mem:", present_in_target=False, manifest=_manifest())
    assert v.expected is False
    assert v.severity == "alarm"


def test_o5_an_unknown_prefix_is_never_silently_expected():
    """A prefix in neither list postdates the seed. It may be perfectly fine, but the
    manifest cannot vouch for it, so it is reported rather than assumed."""
    v = WD.classify("wormhole:", present_in_target=True, manifest=_manifest())
    assert v.expected is False
    assert v.severity == "report"
    assert "manifest" in v.why.lower()


def test_o6_no_manifest_means_no_oracle_and_the_tool_says_so():
    """An unseeded world has no expectation to measure against. Guessing here would
    reproduce the confident-meaningless-difference failure this slice exists to prevent."""
    v = WD.classify("bifrost:", present_in_target=False, manifest=None)
    assert v.expected is False
    assert v.severity == "unknown"
    assert "no seed manifest" in v.why.lower()


# ------------------------------------------------------------------ the render

def test_r1_the_render_leads_with_findings_not_with_the_expected_bulk():
    """'At a glance' is the requirement. 13,963 expected differences must not be able to
    push 10 real ones below the fold."""
    rows = [
        WD.PlaneRow("bifrost:", 8276, 0, WD.classify("bifrost:", False, _manifest())),
        WD.PlaneRow("learn:", 1061, 1060, WD.classify("learn:", True, _manifest())),
    ]
    out = WD.render(rows, source="prod", target="alpha")
    findings_at = out.index("learn:")
    expected_at = out.index("bifrost:")
    assert findings_at < expected_at, "expected bulk outranked a real finding"


def test_r2_the_expected_bulk_is_collapsed_but_never_hidden():
    """Silent must mean 'not shouted', never 'not shown' -- a differ that omits what it
    chose to ignore cannot be audited, and its silence stops being evidence."""
    rows = [WD.PlaneRow("bifrost:", 8276, 0, WD.classify("bifrost:", False, _manifest()))]
    out = WD.render(rows, source="prod", target="alpha")
    assert "bifrost:" in out
    assert "8,276" in out or "8276" in out


def test_r3_identical_planes_say_identical_rather_than_going_quiet():
    """Absence of output is indistinguishable from a differ that failed to run."""
    rows = [WD.PlaneRow("artifact:", 1264, 1264, WD.classify("artifact:", True, _manifest()))]
    out = WD.render(rows, source="prod", target="alpha")
    assert "artifact:" in out and ("identical" in out.lower() or "same" in out.lower())


def test_r4_an_alarm_is_visually_distinct_from_ordinary_divergence():
    rows = [
        WD.PlaneRow("learn:", 1061, 1060, WD.classify("learn:", True, _manifest())),
        WD.PlaneRow("bifrost:", 0, 7870, WD.classify("bifrost:", True, _manifest())),
    ]
    out = WD.render(rows, source="prod", target="alpha")
    assert "ALARM" in out
    assert out.index("bifrost:") < out.index("learn:"), "an alarm ranked below a report"


def test_c1_ephemeral_singletons_collapse_into_one_row():
    """FOUND BY RUNNING IT. The first live run put 20 rows of per-test namespaces
    (t-w43-3fd0a1e8, t-w16-c4916333, ...) above the three real findings -- the tool
    reproducing, one level up, the exact burial it was built to prevent. A prefix that is
    tiny AND unnamed by the manifest is not a plane; planes are the recurring structural
    prefixes."""
    rows = [WD.PlaneRow(f"t-w43-{i:08x}", 11, 0, WD.classify(f"t-w43-{i:08x}", False, _manifest()))
            for i in range(20)]
    rows.append(WD.PlaneRow("learn:", 1061, 1060, WD.classify("learn:", True, _manifest())))
    kept, collapsed = WD.collapse_minor(rows, manifest=_manifest())
    assert len(kept) == 1 and kept[0].prefix == "learn:"
    assert collapsed["n_prefixes"] == 20


def test_c2_a_collapsed_group_is_counted_never_dropped():
    """Same law as the expected bulk: not shouted, never not-shown."""
    rows = [WD.PlaneRow(f"t-w43-{i}", 11, 0, WD.classify(f"t-w43-{i}", False, _manifest()))
            for i in range(20)]
    _, collapsed = WD.collapse_minor(rows, manifest=_manifest())
    assert collapsed["n_keys_source"] == 220
    out = WD.render([], source="prod", target="alpha", manifest=_manifest(),
                    collapsed=collapsed)
    assert "20" in out and "220" in out


def test_c3_a_manifest_named_prefix_never_collapses_however_small():
    """knowledge_map: is 2 keys and is structural -- the manifest vouching for it is what
    makes it a plane, not its size."""
    small = WD.PlaneRow("knowledge_map:", 2, 2, WD.classify("knowledge_map:", True, _manifest()))
    m = _manifest(carried=("learn:", "mem:", "knowledge_map:"))
    kept, _ = WD.collapse_minor([small], manifest=m)
    assert [r.prefix for r in kept] == ["knowledge_map:"]


def test_c4_an_alarm_never_collapses_however_small():
    """A single stray key on a refused plane is the whole point of the alarm."""
    row = WD.PlaneRow("bifrost:", 0, 1, WD.classify("bifrost:", True, _manifest()))
    kept, _ = WD.collapse_minor([row], manifest=_manifest())
    assert [r.prefix for r in kept] == ["bifrost:"]


def test_r5_the_render_names_the_oracle_and_its_date():
    """A verdict of 'expected' is only as good as the manifest behind it, so the reader
    must be able to see which seed is doing the vouching, and how stale it is."""
    rows = [WD.PlaneRow("learn:", 1061, 1060, WD.classify("learn:", True, _manifest()))]
    out = WD.render(rows, source="prod", target="alpha", manifest=_manifest())
    assert "2026-08-14" in out


def test_r6_with_no_manifest_the_render_refuses_to_call_anything_expected():
    rows = [WD.PlaneRow("bifrost:", 8276, 0, WD.classify("bifrost:", False, None))]
    out = WD.render(rows, source="prod", target="alpha", manifest=None)
    assert "no seed manifest" in out.lower()
    assert "expected" not in out.lower().split("no seed manifest")[0]
