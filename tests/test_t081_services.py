"""T081-W3 pins: the doctor's fleet-infrastructure SERVICES block.

Distinct from agent diagnosis (examine): this answers 'what's running?' -- the P2 gap.
Each service renders LIVE (dashboard, no drill) or DOWN (banner, carrying a start command).
"""
from core.comm import doctor


def test_svc_finding_live_has_no_drill():
    f = doctor._svc_finding("ui:8787", True, "console", "start it")
    assert f["grade"] == "dashboard"
    assert "LIVE" in f["line"]
    assert f["drill"] == ""


def test_svc_finding_down_carries_the_remedy():
    f = doctor._svc_finding("ui:8787", False, "console", "py scripts/bifrost_ui.py")
    assert f["grade"] == "banner"
    assert "DOWN" in f["line"]
    assert "bifrost_ui.py" in f["drill"]


def test_tcp_up_false_on_closed_port():
    # port 1 is not accepting connections -- probe must return False fast, never raise
    assert doctor._tcp_up("127.0.0.1", 1, timeout=0.2) is False


def test_examine_services_covers_the_three_and_never_raises():
    svcs = doctor.examine_services()
    assert isinstance(svcs, list)
    names = {f["agent"] for f in svcs}
    assert "redis" in names
    assert any(n.startswith("ui:") for n in names)
    assert "daemon" in names
    for f in svcs:
        assert f["grade"] in ("dashboard", "banner")
        assert f["line"].startswith("service ")
        # DOWN findings must always carry a start command; LIVE ones must not
        if "DOWN" in f["line"]:
            assert f["drill"]
        else:
            assert f["drill"] == ""
