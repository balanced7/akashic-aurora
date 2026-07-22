"""W54 pins (kimi F3): the activation gauge -- injections grouped by lesson family.

The claim class this guards: "organ X is proven/LIVE" must read the instrument. The gauge
renders conductor-first (the stance family is the reason W54 exists), counts an injection
once per family regardless of how many of that family's lessons it carried, and keeps
'conductor' visible even at zero.
"""
import agent_cli
from core.recall.at_action import injections_by_family


def _inj(*sources):
    return {"at": 1.0, "alt": "action", "t": "p:x", "chars": 100, "s": list(sources)}


def test_p1_conductor_counted_over_total():
    g = injections_by_family(injections=[
        _inj("learn:experiment:conductor_brief_intent_law"),
        _inj("learn:experiment:fix_setup_claude_settings"),
        _inj("learn:experiment:fix_location_setup_pytest"),
    ])
    assert g["total"] == 3
    assert g["families"]["conductor"] == 1
    assert g["families"]["fix"] == 2


def test_p2_multi_source_injection_counts_once_per_family():
    g = injections_by_family(injections=[
        _inj("learn:experiment:conductor_red_is_a_gem",
             "learn:experiment:conductor_brief_intent_law",
             "learn:experiment:wake_watcher_insta_fires_lane_divergence"),
    ])
    assert g["total"] == 1
    assert g["families"]["conductor"] == 1   # once, not twice
    assert g["families"]["wake"] == 1


def test_p3_conductor_present_even_at_zero():
    g = injections_by_family(injections=[_inj("learn:experiment:fix_setup_docs_wishlist")])
    assert g["families"]["conductor"] == 0


def test_p4_empty_ledger_safe():
    g = injections_by_family(injections=[])
    assert g["total"] == 0
    assert g["families"] == {"conductor": 0}
    assert "conductor 0/0" in agent_cli._family_gauge_render(g)


def test_p5_render_conductor_first():
    g = injections_by_family(injections=[
        _inj("learn:experiment:fix_a_thing"), _inj("learn:experiment:fix_b_thing"),
        _inj("learn:experiment:conductor_no_is_information"),
    ])
    line = agent_cli._family_gauge_render(g)
    assert line.startswith("conductor 1/3")
    assert "fix 2/3" in line


def test_p6_hyphen_families_group():
    g = injections_by_family(injections=[_inj("learn:experiment:census-claims-vs-listings")])
    assert g["families"]["census"] == 1


def test_p7_draft_carries_activation_line():
    draft = agent_cli.build_session_draft(
        commits=[], lessons=[], notes=[],
        injections=[_inj("learn:experiment:conductor_brief_intent_law")])
    assert ("Recall activation by family (1 injection(s) this session): conductor 1/1"
            in draft)
