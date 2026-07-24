"""Fleet dispatch (core/fleet) -- the roster (single source of truth) + the direct caller.

Hermetic: the caller and the availability probe take an injectable `opener`, so no test touches the
network. The roster reads the bundled models.json (local file), so it needs no injection. Design:
docs/library/design/20260709_fleet-dispatch-an-intelligent-easy-struc_303d15.md.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fleet import roster
from core.fleet.caller import call, FleetCallError


# ------------------------------------------------------------------ fake transport
class _FakeResp:
    def __init__(self, body):
        self._b = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(body, capture=None):
    def _open(req, timeout=None):
        if capture is not None:
            capture["url"] = req.full_url
            capture["payload"] = json.loads(req.data.decode("utf-8")) if getattr(req, "data", None) else None
        return _FakeResp(body)
    return _open


def _raising_opener(exc):
    def _open(req, timeout=None):
        raise exc
    return _open


# ------------------------------------------------------------------ roster
def test_roster_loads_and_filters_by_status_and_capability():
    all_rows = roster.models()
    assert len(all_rows) >= 5, "the seeded roster should be non-trivial"
    active = {m["tag"] for m in roster.models(status="active")}
    gated = {m["tag"] for m in roster.models(status="gated")}
    assert "glm-4.7-flash" in active
    assert "gpt-oss:20b" in gated and "qwen3-coder:30b" in gated
    faithful = {m["tag"] for m in roster.models(capability="faithful")}
    assert "granite-4.0-h-small" in faithful and "gemma-3-12b-it" in faithful


def test_get_returns_spec_or_none():
    assert roster.get("glm-4.7-flash")["status"] == "active"
    assert roster.get("does-not-exist") is None
    assert roster.get("") is None


def test_select_picks_active_by_capability_and_skips_gated():
    pick = roster.select("tool-use")            # default status=active
    assert pick and pick["tag"] == "glm-4.7-flash"
    # gpt-oss has 'reasoning' but is GATED -> never selected even when it's the only match
    assert roster.select("reasoning") is None


def test_select_respects_vram_and_context_constraints():
    # among candidates with 'extract', a 5GB cap keeps qwen3.5:4b (4GB, measured) as the top pick
    pick = roster.select("extract", status="candidate", max_vram=5)
    assert pick and pick["tag"] == "qwen3.5:4b"
    # an impossible context requirement excludes the only active model -> None
    assert roster.select("generalist", min_context=10_000_000) is None
    # a capability nobody declares -> None
    assert roster.select("time-travel") is None


def test_select_unknown_vram_is_not_excluded():
    """A candidate with unmeasured VRAM must still be selectable (so it can get a first manual call),
    i.e. unknown vram is NOT treated as too-big."""
    pick = roster.select("faithful", status="candidate", max_vram=1)
    assert pick is not None and pick.get("vram_gb") is None


def test_probe_availability_injected():
    body = json.dumps({"models": [{"name": "glm-4.7-flash:latest"}, {"name": "qwen3.5:9b"}]})
    out = roster.probe_availability(opener=_opener(body))
    assert out["ok"] is True
    assert "glm-4.7-flash" in out["declared_present"] and "qwen3.5:9b" in out["declared_present"]
    assert "gpt-oss:20b" not in out["declared_present"]


def test_probe_availability_fail_soft():
    import urllib.error
    out = roster.probe_availability(opener=_raising_opener(urllib.error.URLError("down")))
    assert out["ok"] is False and out["present"] == []


# ------------------------------------------------------------------ caller
def test_call_returns_response_text():
    out = call("glm-4.7-flash", "ping", opener=_opener(json.dumps({"response": "pong"})))
    assert out == "pong"


def test_call_pins_num_ctx_and_defaults_from_roster():
    cap = {}
    call("glm-4.7-flash", "hi", opener=_opener(json.dumps({"response": "x"}), capture=cap))
    opts = cap["payload"]["options"]
    assert opts["num_ctx"] == 64000, "num_ctx pinned from the glm spec (not the 4K trap)"
    assert opts["temperature"] == 0.2 and opts["num_predict"] == 512
    assert cap["url"].endswith("/api/generate") and cap["payload"]["model"] == "glm-4.7-flash"


def test_call_unknown_tag_uses_safe_ctx_floor():
    cap = {}
    call("mystery:tag", "hi", opener=_opener(json.dumps({"response": "x"}), capture=cap))
    assert cap["payload"]["options"]["num_ctx"] == 32000, "unknown tag falls back to the safe floor"


def test_call_fmt_json_and_system_are_wired():
    cap = {}
    call("qwen3.5:4b", "extract", system="be terse", fmt="json",
         opener=_opener(json.dumps({"response": "{}"}), capture=cap))
    assert cap["payload"]["format"] == "json"
    assert cap["payload"]["system"] == "be terse"


def test_call_raises_on_network_error():
    import urllib.error
    with pytest.raises(FleetCallError):
        call("glm-4.7-flash", "hi", opener=_raising_opener(urllib.error.URLError("boom")))


def test_call_raises_on_ollama_error_field():
    # Ollama returns HTTP 200 with an 'error' field when a model isn't loaded -- must not look like success
    with pytest.raises(FleetCallError):
        call("glm-4.7-flash", "hi", opener=_opener(json.dumps({"error": "model not found"})))


def test_call_raises_on_non_json_body():
    with pytest.raises(FleetCallError):
        call("glm-4.7-flash", "hi", opener=_opener("<html>502</html>"))


def test_call_requires_tag_and_prompt():
    with pytest.raises(FleetCallError):
        call("", "hi", opener=_opener("{}"))
    with pytest.raises(FleetCallError):
        call("glm-4.7-flash", "", opener=_opener("{}"))


# ------------------------------------------------------------------ data integrity
def test_roster_data_is_self_consistent():
    """Every row has a tag + capabilities; gated rows explain WHY (disqualifier), active rows don't."""
    for m in roster.models():
        assert m.get("tag") and isinstance(m.get("capabilities"), list) and m["capabilities"]
        if m["status"] == "gated":
            assert m.get("disqualifier"), f"{m['tag']} is gated but has no disqualifier"
        if m["status"] == "active":
            assert m.get("disqualifier") is None, f"{m['tag']} is active but marked disqualified"
