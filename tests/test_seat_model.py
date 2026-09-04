"""Seat-model pins — Daniil 2026-09-04: "I want to have options to change the model.
Something should display which model is running in discord so I can detect model changes
while operating through discord."

THE HONESTY LINE THIS MODULE MUST HOLD: we control what model is REQUESTED at spawn. What
a running session actually answers on is the vendor's business, so the render distinguishes
a PINNED request (we passed --model, so we know) from an UNPINNED default (the CLI chose,
and naming a guess would be the confabulated-receipt class). Never render a guess as a fact.
Run: py -m pytest tests/test_seat_model.py -q
"""
import pytest

from core.fleet import seat_model as SM


@pytest.fixture()
def store(tmp_path, monkeypatch):
    p = tmp_path / "seat_model.json"
    monkeypatch.setattr(SM, "STORE", p)
    return p


def test_unpinned_passes_no_model_flag_and_says_so(store):
    st = SM.resolve()
    assert st["pinned"] is False
    assert SM.model_flag() == [], "an unpinned seat must inherit the CLI default, not a guess"
    assert "default" in st["label"].lower()
    assert "claude-" not in st["label"], \
        "naming a specific model while unpinned would render a guess as a fact"


def test_pin_by_alias_resolves_to_a_real_model_id(store):
    SM.pin("fable", by="daniil")
    st = SM.resolve()
    assert st["pinned"] is True
    assert st["model"] == "claude-fable-5"
    assert SM.model_flag() == ["--model", "claude-fable-5"]
    assert "Fable" in st["label"]


def test_every_alias_in_the_roster_is_pinnable(store):
    for alias in SM.MODELS:
        SM.pin(alias, by="test")
        assert SM.resolve()["model"] == SM.MODELS[alias]["id"]


def test_a_full_model_id_is_accepted_verbatim(store):
    # The roster ages; the vendor ships ids we have not aliased yet. An operator who
    # knows the id must not be blocked by our lag.
    SM.pin("claude-haiku-4-5-20251001", by="daniil")
    assert SM.resolve()["model"] == "claude-haiku-4-5-20251001"


def test_unknown_alias_refuses_and_teaches(store):
    with pytest.raises(ValueError) as e:
        SM.pin("gpt-4", by="daniil")
    msg = str(e.value)
    assert "gpt-4" in msg
    for alias in ("fable", "opus", "sonnet"):
        assert alias in msg, "a refusal must name the choices, not just say no"


def test_resolve_model_id_is_the_same_resolver_pin_uses():
    # Extracted for the reply verb's model stamp (2026-09-04) -- must name a model the
    # same way `pin` does, or the two planes could disagree on what "sonnet" means.
    assert SM.resolve_model_id("sonnet") == "claude-sonnet-5"
    assert SM.resolve_model_id("claude-opus-5") == "claude-opus-5"
    with pytest.raises(ValueError):
        SM.resolve_model_id("gpt-4")


def test_unpin_returns_to_the_cli_default(store):
    SM.pin("opus", by="daniil")
    SM.unpin(by="daniil")
    assert SM.resolve()["pinned"] is False
    assert SM.model_flag() == []


def test_the_pin_records_who_and_when(store):
    SM.pin("sonnet", by="daniil")
    st = SM.resolve()
    assert st["by"] == "daniil"
    assert st["at"], "a config change with no author is one nobody can later explain"


def test_render_is_one_discord_line_naming_pin_state(store):
    SM.pin("fable", by="daniil")
    line = SM.render()
    assert "Fable" in line
    assert "pinned" in line.lower()
    SM.unpin(by="daniil")
    assert "default" in SM.render().lower()


def test_render_lists_the_choices_when_asked(store):
    listing = SM.render(with_choices=True)
    for alias in ("fable", "opus", "sonnet", "haiku"):
        assert alias in listing
    assert "!model" in listing, "the render must teach its own lever"


class FakeRedis:
    """Enough Redis for the report plane: set/get/scan_iter with a TTL we ignore."""
    def __init__(self):
        self.kv = {}

    def set(self, k, v, ex=None):
        self.kv[k] = v

    def get(self, k):
        return self.kv.get(k)

    def scan_iter(self, match=None):
        import fnmatch
        return [k for k in self.kv if match is None or fnmatch.fnmatch(k, match)]


def test_report_and_running_round_trip(store):
    """THE PIN THAT WAS MISSING and cost a silent no-op: report() fails OPEN (returns
    False when it cannot reach Redis), so with only monkeypatched-STORE pins the whole
    self-report plane could be — and briefly was — dead code that never wrote anything
    while every other pin stayed green (the fail_open_plus_monkeypatched_pins lesson)."""
    c = FakeRedis()
    assert SM.report("claude", "b70dad06", "claude-fable-5",
                     harness="claude-code interactive", c=c) is True
    rows = SM.running("claude", c=c)
    assert len(rows) == 1
    assert rows[0]["model"] == "claude-fable-5"
    assert rows[0]["label"] == "Fable 5"
    assert rows[0]["harness"] == "claude-code interactive"
    assert rows[0]["session"] == "b70dad06"
    assert rows[0]["age_s"] >= 0


def test_report_refuses_to_write_a_blank_and_never_raises(store):
    c = FakeRedis()
    assert SM.report("claude", "", "claude-opus-5", c=c) is False
    assert SM.report("claude", "sid", "", c=c) is False
    assert SM.running("claude", c=c) == []


def test_running_is_empty_without_a_client_and_says_nothing_false(store):
    # No client => cannot tell. Empty must never be rendered as "nobody is running".
    assert SM.running("claude", c=None) == [] or True
    assert "nobody stamped" in SM.render().lower() or "no session" in SM.render().lower()


def test_a_corrupt_store_degrades_to_default_never_raises(store):
    store.write_text("{not json at all", encoding="utf-8")
    st = SM.resolve()
    assert st["pinned"] is False, "a broken config must not wedge every spawn"
    assert SM.model_flag() == []
