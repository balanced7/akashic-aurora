"""W156c pins: state flows DOWN, and the seed says what it refused to carry.

The empty-brain problem: alpha booted with 0 keys against prod's 19,850. Every recall
returns nothing, every boot renders empty, and the behaviours most worth exercising in a
twin are exactly the ones that need a populated memory.

The asymmetry these pins protect: downward is a COPY (the higher tier is authoritative by
definition); upward is a CLAIM. The round-1 fence landed the reason -- a lesson is not a
replayable input, because it is already the result of folding an input through the twin's
code and the twin's memory. "claude concluded that recall-at arms too hot" contains alpha.
So the upward path is re-litigation, not bulk state, and `--to prod` must be refused by the
mechanism rather than merely discouraged by a docstring.
"""
import pytest

from core import world_seed as S


# ---------------------------------------------------------------- direction

def test_d1_refuses_to_seed_into_prod():
    """The load-bearing refusal. Not a warning, not a flag -- a refusal."""
    with pytest.raises(S.SeedRefusal) as e:
        S.plan("alpha", "prod")
    msg = str(e.value)
    assert "re-litigation" in msg          # names the correct path, not just 'no'
    assert "grounded:false" in msg or "rumour" in msg


def test_d2_refuses_upward_between_twins():
    with pytest.raises(S.SeedRefusal):
        S.plan("alpha", "beta")


def test_d3_refuses_sideways():
    with pytest.raises(S.SeedRefusal):
        S.plan("alpha", "alpha")


def test_d4_allows_the_two_legal_directions():
    assert S.plan("prod", "beta").target == "beta"
    assert S.plan("prod", "alpha").target == "alpha"
    assert S.plan("beta", "alpha").target == "alpha"


def test_d5_unknown_world_is_refused_not_guessed():
    with pytest.raises(S.SeedRefusal) as e:
        S.plan("prod", "staging")
    assert "staging" in str(e.value)


# ---------------------------------------------------------------- what rides

def test_k1_transport_never_rides_and_can_never_be_opted_into():
    """bifrost:* is 7,740 keys of cursors, presence and runner locks. An alpha that
    inherits prod's cursors believes it consumed mail it never saw. There is no flag
    for this, deliberately."""
    p = S.plan("prod", "alpha", include=["events", "recall"])
    assert not any(x.startswith("bifrost") for x in p.prefixes)
    assert "bifrost:" in p.excluded

    with pytest.raises(S.SeedRefusal):
        S.plan("prod", "alpha", include=["bifrost"])


def test_k2_lessons_ride_by_default():
    """The whole point of seeding: a twin that behaves like the house."""
    assert "learn:" in S.plan("prod", "alpha").prefixes
    assert "mem:" in S.plan("prod", "alpha").prefixes


def test_k3_allowlist_not_denylist():
    """A denylist ships every future prefix nobody classified. Assert the shape:
    an invented prefix is absent from a default plan without anyone denying it."""
    assert "wormhole:" not in S.plan("prod", "alpha").prefixes


def test_k4_optional_classes_are_out_by_default_and_in_on_request():
    default = S.plan("prod", "alpha")
    assert "events:" not in default.prefixes
    assert "events:" in default.excluded
    opted = S.plan("prod", "alpha", include=["events"])
    assert "events:" in opted.prefixes
    assert "events:" not in opted.excluded


# ---------------------------------------------------------------- the report

def test_r1_the_report_names_what_was_refused_not_only_what_was_carried():
    """Dawe Test on our own instrument. 'Copied 3,397 keys' is fluent and tells you
    nothing about whether your twin will behave. The excluded half is the half that
    surprises someone at 3am."""
    out = S.plan("prod", "alpha").render()
    assert "REFUSED" in out
    assert "bifrost:" in out
    assert "consumed mail it never saw" in out


def test_r2_every_exclusion_carries_a_reason():
    p = S.plan("prod", "alpha")
    for prefix, why in p.excluded.items():
        assert why and len(why) > 20, f"{prefix} excluded with no usable reason"


def test_r3_a_dry_run_says_it_is_a_dry_run():
    """A plan that renders identically whether or not it wrote is how someone believes
    they seeded when they did not."""
    p = S.plan("prod", "alpha")
    assert "dry run" in p.render(applied=False).lower()
    assert "dry run" not in p.render(applied=True).lower()


# ---------------------------------------------------------------- the copy

class _FakeRedis:
    def __init__(self, keys=None):
        self.data = dict(keys or {})
        self.restored = {}
        self.strings = {}

    def set(self, key, value):
        self.strings[key] = value

    def get(self, key):
        return self.strings.get(key)

    def scan_iter(self, match="*", count=100):
        stem = match.rstrip("*")
        return [k for k in self.data if k.startswith(stem)]

    def dump(self, key):
        return self.data.get(key)

    def pttl(self, key):
        return -1

    def restore(self, key, ttl, payload, replace=False):
        self.restored[key] = payload


def test_c1_dry_run_counts_without_writing():
    src = _FakeRedis({"learn:a": b"1", "learn:b": b"2"})
    dst = _FakeRedis()
    assert S.copy_prefix(src, dst, "learn:", apply=False) == 2
    assert dst.restored == {}


def test_c2_apply_writes_every_key():
    src = _FakeRedis({"learn:a": b"1", "learn:b": b"2", "mem:x": b"3"})
    dst = _FakeRedis()
    assert S.copy_prefix(src, dst, "learn:", apply=True) == 2
    assert set(dst.restored) == {"learn:a", "learn:b"}      # mem: not swept by this call


def test_c3_a_key_that_expired_mid_scan_is_skipped_not_crashed():
    """DUMP returns None for a key that vanished between SCAN and DUMP. On a live prod
    with TTLs that is a normal Tuesday, and a seed that dies on it is a seed nobody runs."""
    src = _FakeRedis({"learn:a": b"1", "learn:gone": None})
    dst = _FakeRedis()
    assert S.copy_prefix(src, dst, "learn:", apply=True) == 2   # seen
    assert set(dst.restored) == {"learn:a"}                     # written


# ---------------------------------------------------------------- provenance

def test_m1_a_seeded_world_records_what_it_inherited():
    """Corpus-level provenance. A seeded lesson is byte-identical to a native one -- same
    schema, same id, same agent name -- so without this, "which institution learned this?"
    has no answer at all the moment a key leaves here. The fence named the concrete road:
    scripts/ops/snapshot_knowledge.py is a shipped dump/restore of the whole knowledge
    layer, i.e. a one-command way to make a twin's lessons indistinguishable from prod's."""
    dst = _FakeRedis()
    plan = S.plan("prod", "alpha")
    doc = S.write_manifest(dst, plan, {"learn:": 1056, "mem:": 559}, "2026-08-14T02:00:00+00:00")
    assert doc["source_world"] == "prod" and doc["target_world"] == "alpha"
    assert doc["total_carried"] == 1056 + 559
    assert S.read_manifest(dst) == doc


def test_m2_the_manifest_states_its_own_limit():
    """It answers at CORPUS level, not per key. A provenance record that does not say how
    far it reaches invites exactly the over-trust it was built to prevent."""
    dst = _FakeRedis()
    doc = S.write_manifest(dst, S.plan("prod", "alpha"), {}, "2026-08-14T02:00:00+00:00")
    assert "corpus-level" in doc["caveat"]
    assert "indistinguishable" in doc["caveat"]


def test_m3_the_manifest_records_the_REFUSED_half_too():
    doc = S.write_manifest(_FakeRedis(), S.plan("prod", "alpha"), {}, "t")
    assert any(p.startswith("bifrost") for p in doc["refused"])


def test_m4_a_world_with_no_manifest_reads_None_not_a_guess():
    """Absence must stay legible as absence. A manifest that defaults to something makes an
    un-seeded world claim a lineage it does not have."""
    assert S.read_manifest(_FakeRedis()) is None


def test_m5_the_manifest_key_never_rides_down_to_the_next_world():
    """Otherwise a world seeded FROM a seeded world inherits its parent's manifest and
    reports an ancestry that skips a generation."""
    assert not any(S.MANIFEST_KEY.startswith(p) for p in S.KNOWLEDGE_PREFIXES)
    assert not any(S.MANIFEST_KEY.startswith(p) for p, _ in S.OPTIONAL_PREFIXES.values())
