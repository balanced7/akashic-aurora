"""T081-W5 pins (safety-critical) -- the honest heal's 3-way orphan classification.

Reconciled 2026-07-16 (docs/library/report/20260716_w5-honest-heal-reconciliation-build-spec_c2d63e.md) from deepseek's
roster half + claude's empirical keyspace census. The invariant under test: the roster can NEVER
silence a real orphan -- durable-family check runs before the roster (File is truth), unknowns
stay loud, and any failure fails OPEN (all loud).
"""
from core.comm.packet_spec import is_ephemeral_key
from core.foundation.store import HybridStore

R = HybridStore._render_orphans   # pure classmethod: (orphans, file_fams) -> lines


# --- the roster predicate (packet_spec) ---
def test_ephemeral_matches_transport_ns_agnostic():
    assert is_ephemeral_key("bifrost:cursor:abc")
    assert is_ephemeral_key("rb25drill3:cursor:xyz")     # different namespace, same family
    assert is_ephemeral_key("bifrost:presence:claude")
    assert is_ephemeral_key("bifrost:turn_metrics:2026")
    assert is_ephemeral_key("bifrost_t039a_deadbeef:trace")  # drill namespace


def test_ephemeral_rejects_durable_knowledge_families():
    # the safety core: durable knowledge must NOT read as ephemeral
    for k in ("learn:experiment:foo", "narr:beat:123", "mem:decisions:x",
              "events:raw:9", "recall:use:q", "knowledge_map:nodes:n"):
        assert not is_ephemeral_key(k), k


# --- the 3-way classification (pure) ---
def test_unknown_is_loud():
    out = "\n".join(R(["weird:unmapped:1"], set()))
    assert "UNKNOWN" in out and "INVESTIGATE" in out


def test_ephemeral_is_quiet():
    out = "\n".join(R(["bifrost:cursor:1"], set()))
    assert "expected Redis-only" in out and "no action" in out
    assert "INVESTIGATE" not in out


def test_durable_family_is_calm_not_loud():
    out = "\n".join(R(["events:raw:9"], {"events:raw"}))
    assert "durable-family" in out and "Redis-ahead" in out
    assert "investigate only if growing" in out
    assert "INVESTIGATE" not in out   # calm, not the loud unknown signal


def test_durable_check_wins_over_roster_file_is_truth():
    # a key that BOTH matches the roster AND whose family is Store-owned -> durable, never silenced
    out = "\n".join(R(["bifrost:delta:1"], {"bifrost:delta"}))
    assert "durable-family" in out
    assert "expected Redis-only" not in out   # NOT classified ephemeral


def test_allowlist_gap_stays_loud():
    # a brand-new subsystem's keys, not in the roster and not Store-owned -> UNKNOWN (safe)
    out = "\n".join(R(["newsubsys:thing:1"], {"events:raw"}))
    assert "UNKNOWN" in out


def test_fail_open_none_file_fams_flags_all():
    out = "\n".join(R(["events:raw:1", "bifrost:cursor:2"], None))
    assert "2 Redis-only key(s)" in out
    assert "classification unavailable" in out   # everything loud when we can't classify


def test_empty_orphans_no_lines():
    assert R([], set()) == []


def test_counts_are_lossless_and_ordered_most_severe_first():
    orphans = (["weird:a:1", "weird:a:2"]                         # 2 unknown
               + ["events:raw:1", "events:raw:2", "events:raw:3"]  # 3 durable
               + ["bifrost:cursor:1", "bifrost:presence:2",
                  "bifrost:work:3", "bifrost:runner:4"])           # 4 ephemeral
    lines = R(orphans, {"events:raw"})
    text = "\n".join(lines)
    assert "2 UNKNOWN" in text and "3 durable-family" in text and "4 expected Redis-only" in text
    # 2 + 3 + 4 == 9 == len(orphans): nothing dropped
    assert 2 + 3 + 4 == len(orphans)
    # most-severe first: unknown line precedes durable precedes ephemeral
    assert text.index("UNKNOWN") < text.index("durable-family") < text.index("expected Redis-only")
