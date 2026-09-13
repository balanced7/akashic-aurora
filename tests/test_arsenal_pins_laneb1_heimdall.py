"""Blind pins for the Lane B.1 GStreamer D3D12 soak RECEIPT SHAPE.

Written by Heimdall (deepseek) from the actual receipt file and its writer
(arsenal/lanes/gst_d3d12_soak.py), pinning the shape the soak agent must keep emitting so a
future "N dropped" is never again unqualified.

The receipt pinned is the final one:
  state/arsenal/receipts/lane-b1-gst-d3d12-soak-20260913-154253.json

What these pins enforce (the four I asked for, plus the audit trail):
  1. per-source drop counts are recorded SEPARATELY, each with its source
  2. the sink and its drop conditions are recorded, so "0 dropped" is never by construction
  3. the calibration is its own record with drops_observed / gated_count_detected_drops /
     completed / stall -- and does NOT gate the soak verdict
  4. the verdict names the gated count it decided on
  5. amendments keep the earlier FAIL verdict, so the audit trail is append-only truth
"""

import json
from pathlib import Path

import pytest

_THIS = Path(__file__).resolve()
ROOT = _THIS.parents[1]

RECEIPT = ROOT / "state" / "arsenal" / "receipts" / "lane-b1-gst-d3d12-soak-20260913-154253.json"

# The sources every drop count must distinguish. A receipt missing any of these keys
# is silent about a source, which is exactly the failure mode these pins retire.
BY_SOURCE_KEYS = {
    "qos_bus_messages:dec",
    "qos_bus_messages:sink",
    "gst_debug_log:dec",
    "fpsdisplaysink_last_message:fps",
}

SINK_CONDITION_KEYS = {
    "sink",
    "sync",
    "qos",
    "max_lateness_ns",
    "processing_deadline_ns",
    "late_frames_can_drop",
}

CALIBRATION_KEYS = {
    "drops_observed",
    "gated_count_detected_drops",
    "completed",
    "stall",
    "counts_by_source",
    "sink_conditions",
}


@pytest.fixture(scope="module")
def receipt():
    if not RECEIPT.exists():
        pytest.skip(f"receipt not present: {RECEIPT}")
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- top-level identity

def test_receipt_api_and_lane(receipt):
    assert receipt["api"] == "arsenal.receipt/v0"
    assert receipt["lane"] == "B.1"


def test_receipt_has_verdict_summary_calibration(receipt):
    for key in ("verdict", "summary", "calibration"):
        assert key in receipt, f"missing top-level {key!r}"


# ---------------------------------------------------------------- 4. the gated count is named

def test_verdict_names_its_gated_count(receipt):
    v = receipt["verdict"]
    assert "gated_drop_count" in v
    # the gated count must NAME its source, not just be a bare number
    assert isinstance(v["gated_drop_count"], str)
    assert "qos_bus_messages" in v["gated_drop_count"]


def test_verdict_reasons_quote_a_rate_not_a_claim(receipt):
    v = receipt["verdict"]
    # a real "0 dropped" reason says how many, its rate, and its limit, never a bare zero
    drop_reasons = [r for r in v["reasons"] if "drop" in r.lower()]
    assert drop_reasons, "no drop reason in the verdict"
    assert any("rate" in r.lower() and "limit" in r.lower() for r in drop_reasons)


# ---------------------------------------------------------------- 1+2. per-source drops + sink conditions

def test_summary_drops_by_source_is_fully_qualified(receipt):
    by_source = receipt["summary"]["drops"]["by_source"]
    # every drop source is present as a key, so none is silently omitted
    assert set(by_source.keys()) == BY_SOURCE_KEYS


def test_summary_drops_gated_source_matches_verdict(receipt):
    s = receipt["summary"]["drops"]
    v = receipt["verdict"]
    # The gated source in the summary and the gated count in the verdict are the SAME fact
    # ("qos_bus_messages from decoder and sink, synced passes"), so their substance must
    # agree. (The receipt strings currently differ by a trailing "only" on the verdict side:
    # a benign drift, but a future writer should emit one canonical string in both places.)
    core = "qos_bus_messages from decoder and sink, synced passes"
    assert core in s["gated_source"]
    assert core in v["gated_drop_count"]


def test_summary_sink_conditions_recorded(receipt):
    sc = receipt["summary"]["drops"]["sink_conditions"]
    assert set(sc.keys()) >= SINK_CONDITION_KEYS
    # these must be truthy and concrete, not defaults left to imply a no-drop sink
    assert sc["sync"] is True
    assert sc["qos"] is True
    assert sc["late_frames_can_drop"] is True
    assert isinstance(sc["max_lateness_ns"], int) and sc["max_lateness_ns"] > 0


def test_total_dropped_consistent_with_sources(receipt):
    s = receipt["summary"]["drops"]
    # total is the sum of the per-source counts (all zeros here), never an unqualified figure
    assert s["total_dropped"] == sum(s["by_source"].values())


# ---------------------------------------------------------------- 3. calibration is its own record

def test_top_level_calibration_keys(receipt):
    assert set(receipt["calibration"].keys()) >= CALIBRATION_KEYS


def test_calibration_counts_by_source_disagrees(receipt):
    # the forced-drop probe MUST show the three instruments disagreeing (the whole point),
    # proving the gated count is a real measurement, not a construction that can't drop
    cbs = receipt["calibration"]["counts_by_source"]
    assert set(cbs.keys()) == BY_SOURCE_KEYS
    assert cbs["qos_bus_messages:dec"] > 0
    assert cbs["qos_bus_messages:sink"] > 0
    # fpsdisplaysink sees fewer drops than the decoder: this disagreement is the signal
    assert cbs["fpsdisplaysink_last_message:fps"] < cbs["qos_bus_messages:dec"]


def test_calibration_detected_drops_true(receipt):
    assert receipt["calibration"]["gated_count_detected_drops"] is True
    assert receipt["calibration"]["drops_observed"] > 0


def test_calibration_stall_recorded_not_erased(receipt):
    cal = receipt["calibration"]
    assert cal["completed"] is False
    assert "stall" in cal and cal["stall"]
    assert "timed_out" in cal["stall"]
    assert cal["stall"]["eos_received"] is False


def test_calibration_does_not_gate_soak_verdict(receipt):
    # the calibration saw drops and stalled; the soak verdict must still be pass
    # (the calibration is evidence the counter works, not a pass/fail of decode)
    v = receipt["verdict"]
    assert v["pass"] is True
    assert v["soak_verdict"] == "pass"
    # and the status must say BOTH halves honestly
    assert v["status"].startswith("soak PASS; calibration saw drops")


def test_verdict_calibration_mirrors_top_level(receipt):
    vc = receipt["verdict"]["calibration"]
    tc = receipt["calibration"]
    for k in ("drops_observed", "gated_count_detected_drops", "completed"):
        assert vc[k] == tc[k]


# ---------------------------------------------------------------- 5. the audit trail

def test_amendments_present(receipt):
    assert "amendments" in receipt and receipt["amendments"]


def test_amendment_keeps_earlier_fail_verdict(receipt):
    # the earlier FAIL verdict is preserved, not overwritten, so the audit trail shows the
    # correction happened rather than silently rewriting history
    am = receipt["amendments"][0]
    assert "previous_verdict" in am
    assert am["previous_verdict"]["pass"] is False
    # the earlier verdict's reason said the calibration did not register drops
    assert any("did not register" in r for r in am["previous_verdict"]["reasons"])


def test_amendment_records_who_and_what_changed(receipt):
    am = receipt["amendments"][0]
    for k in ("at", "by", "changes", "unchanged"):
        assert k in am, f"amendment missing {k!r}"
    assert isinstance(am["changes"], list) and am["changes"]


def test_current_verdict_gated_count_unchanged_by_amendment(receipt):
    # the gated count was always qos_bus_messages; the amendment fixed the calibration
    # interpretation, not the measurement definition
    am = receipt["amendments"][0]
    assert am["previous_verdict"]["gated_drop_count"] == receipt["verdict"]["gated_drop_count"]


# ---------------------------------------------------------------- memory domain claim

def test_receipt_states_memory_domain_at_sink(receipt):
    # the claim "D3D12Memory reached the sink" must be backed by a 4/4 assertion, not absent
    v = receipt["verdict"]
    mem_reasons = [r for r in v["reasons"] if "D3D12Memory" in r]
    assert mem_reasons, "no reason asserting D3D12Memory at the sink"
    assert any("4/4" in r and "pass" in r.lower() for r in mem_reasons)
