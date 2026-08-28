"""T370 Slice 0 RED, reader lane (kimi / Navi) -- bounded no-model shadow-shelf reader.

Pre-registered BEFORE production code exists in ``core.recall.shadow_shelf``. The pilot
category is the sealed behavior contract ``recall.at_action.rank.v1`` (a machine-deciding
contract, NOT the free-form knowledge-record ``category`` field). ``domain``, ``urgency``,
``theme``, ``confidence``, and ``favorite`` are read-time facets: ``with_facets(...)``
returns a NEW contract with the SAME identity, and facets never change identity.

The reader is the ONE bounded no-model surface over two SEPARATE SQLite stores: an
observation register (cohort envelopes, written by observers) and a judgment register
(append-only KEEP/DROP preference, plus seen receipts). ``judgment_store=None`` means the
judgment plane is UNAVAILABLE and the peek is ``partial``; an ``ok`` peek requires a
readable judgment store. Every test is CAUSAL: real stores on ``tmp_path``, real writes,
exact returned dict/state asserted -- never an introspection probe, a swallowed exception,
an empty stub, or a docstring.

Hermetic: SQLite via tmp_path only. No Redis, no model, no Discord/Bifrost/EventLog, no
canonical-store writer. These tests FAIL (RED) until the module ships. Run ONLY this file:
    py -m pytest tests/test_t370_shadow_shelf_reader_red.py -q

Import target: ``core.recall.shadow_shelf`` (intended public module; does not exist yet).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:  # noqa: E402  (RED if absent)
    from core.recall.shadow_shelf import (
        CategoryContract,
        ObservationStore,
        JudgmentStore,
        ShadowShelfReader,
    )
    _HAS = True
except ImportError:
    CategoryContract = ObservationStore = JudgmentStore = ShadowShelfReader = None  # type: ignore[assignment]
    _HAS = False


def _require():
    assert _HAS, (
        "core.recall.shadow_shelf (CategoryContract/ObservationStore/JudgmentStore/"
        "ShadowShelfReader) does not exist yet - RED: implement the reader surface."
    )
    return CategoryContract, ObservationStore, JudgmentStore, ShadowShelfReader


# ---------------------------------------------------------------------------
# Deterministic fixtures (no model). DATA handed to the real stores.
# ---------------------------------------------------------------------------

def _slot(role, terminal, items=(), version=1, error_reason=""):
    """One versioned candidate slot. terminal in {emitted, silent, abstained, error}."""
    return {"role": role, "version": version, "terminal": terminal,
            "items": list(items), "error_reason": error_reason}


def _envelope(cohort_id, champion, challenger, state="agreement", source="evt-1",
              subject="s", purpose="p"):
    """A complete cohort envelope carrying the subject/purpose the peek filters on. Every
    peek in this file filters subject="s", purpose="p", so envelopes default to those."""
    return {"cohort_id": cohort_id, "source": source, "subject": subject,
            "purpose": purpose,
            "category": "recall.at_action.rank.v1",
            "category_contract_hash": "rank-v1-hash-0000", "version": 1,
            "champion": champion, "challenger": challenger, "state": state}


def _control_envelope(cohort_id="ctrl-known-wrong"):
    """Seeded known-wrong unanimous cohort: BOTH slots emit the same wrong item."""
    champ = _slot("champion", "emitted", items=["wrong-K"])
    chall = _slot("challenger", "emitted", items=["wrong-K"])
    env = _envelope(cohort_id, champ, chall, state="agreement", source="ctrl-1")
    env["control"] = True
    env["known_wrong"] = True
    return env


def _ok_reader(tmp_path, Obs, Jud, Reader, *, cohorts=(), judgments=()):
    """Build a reader over a READABLE observation store AND a READABLE judgment store, so
    peek may reach status=ok. Seeds any envelopes + appends any judgments first."""
    obs = Obs(str(tmp_path / "obs.sqlite"))
    jud = Jud(str(tmp_path / "jud.sqlite"))
    for env in cohorts:
        obs.write_envelope(env)
    for j in judgments:
        jud.append(**j)
    return ShadowShelfReader(obs, jud), obs, jud


# ---------------------------------------------------------------------------
# Pin 1 -- CategoryContract identity vs facets (facets never change identity).
# ---------------------------------------------------------------------------

def test_facets_do_not_change_category_identity(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    cat = Cat(input_schema={"kind": "action"}, candidate_schema={"outcome": "ranked"},
              comparison="bounded-id-set", retention="visible-death",
              writers=("observer", "judge"), reader="disagreements-first", delivery="none")
    base_id = cat.identity()
    faceted = cat.with_facets(domain="drafting", urgency="low", theme="review",
                              confidence=0.5, favorite=False)
    assert faceted is not cat, "with_facets returns a new contract object"
    assert faceted.identity() == base_id, "facets must not change category identity"


def test_two_contracts_same_tuple_are_one_identity(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    a = Cat(input_schema=1, candidate_schema=2, comparison=3, retention=4,
            writers=5, reader=6, delivery=7)
    b = Cat(input_schema=1, candidate_schema=2, comparison=3, retention=4,
            writers=5, reader=6, delivery=7).with_facets(theme="different-facet")
    assert a.identity() == b.identity(), "same tuple == same identity, facets excluded"


# ---------------------------------------------------------------------------
# Pin 5 -- observation and judgment are separate stores, separate files, and
#          same-path cross-type construction refuses loudly.
# ---------------------------------------------------------------------------

def test_observation_and_judgment_require_separate_existing_paths(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    obs = Obs(str(tmp_path / "obs.sqlite"))
    jud = Jud(str(tmp_path / "jud.sqlite"))
    assert type(obs) is not type(jud), "observation and judgment are different classes"
    assert obs.path != jud.path, "stores must be on different resolved paths"
    assert os.path.realpath(obs.path) != os.path.realpath(jud.path)
    assert os.path.exists(obs.path), "observation DB file must exist after construction"
    assert os.path.exists(jud.path), "judgment DB file must exist after construction"


def test_same_path_across_store_types_refuses(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    shared = str(tmp_path / "same.sqlite")
    Obs(shared)
    try:
        Jud(shared)
        assert False, "opening a judgment store on the observation path must refuse loudly"
    except (ValueError, RuntimeError, IOError, OSError):
        pass


def test_observation_write_then_peek_roundtrips(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    env = _envelope("c-1", _slot("champion", "emitted", items=["A"]),
                    _slot("challenger", "emitted", items=["A"]), state="agreement")
    obs.write_envelope(env)
    got = reader.peek(subject="s", purpose="p", limit=10)
    assert got["status"] == "ok", got
    assert got["rows"], "a written cohort must surface in peek rows"


def test_judgment_append_persists_exact_version_verbatim(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    jud = Jud(str(tmp_path / "jud.sqlite"))
    jud.append(cohort_id="c-1", candidate_id="champion", candidate_version=7,
               principal="evaluator", pref="KEEP")
    jud.append(cohort_id="c-1", candidate_id="challenger", candidate_version=7,
               principal="evaluator", pref="DROP")
    # Persistence asserted through a real read, not the append return value.
    rows = jud.list() if hasattr(jud, "list") else jud.judgments() if hasattr(jud, "judgments") else None
    assert rows is not None, "JudgmentStore must expose a real read (list()/judgments())"
    by_candidate = {r["candidate_id"]: r for r in rows}
    assert by_candidate["champion"]["candidate_version"] == 7, "exact version persisted verbatim"
    assert by_candidate["champion"]["pref"] == "KEEP"
    assert by_candidate["challenger"]["pref"] == "DROP"


def test_judgment_missing_version_refuses(tmp_path):
    """Missing/None/empty candidate_version must refuse; a supplied exact version is the
    only accepted target. JudgmentStore has no observation authority, so it validates the
    version is PRESENT and well-formed, never that it names a real observation slot."""
    Cat, Obs, Jud, Reader = _require()
    jud = Jud(str(tmp_path / "jud.sqlite"))
    for bad_version in (None, "", 0, -1):
        try:
            jud.append(cohort_id="c", candidate_id="champion", candidate_version=bad_version,
                       principal="e", pref="KEEP")
            assert False, f"candidate_version {bad_version!r} must be rejected"
        except (ValueError, TypeError):
            pass


def test_judgment_appends_only_keep_or_drop(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    jud = Jud(str(tmp_path / "jud.sqlite"))
    for bad in ("ADOPT", "PROMOTE", "useful", "", None, 1):
        try:
            jud.append(cohort_id="c", candidate_id="champion", candidate_version=1,
                       principal="e", pref=bad)
            assert False, f"pref {bad!r} must be rejected"
        except (ValueError, TypeError):
            pass


def test_judgment_has_no_promotion_or_usefulness_surface(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    jud = Jud(str(tmp_path / "jud.sqlite"))
    for forbidden in ("promote", "promote_candidate", "set_useful", "claim_usefulness"):
        assert not hasattr(jud, forbidden), f"judgment must not advertise {forbidden}"


# ---------------------------------------------------------------------------
# Pin 6 -- every numerator carries its denominator; no naked win/keep rate.
# ---------------------------------------------------------------------------

def test_peek_counters_carry_numerator_and_denominator(tmp_path):
    """Seed two cohorts + one KEEP judgment, then require peek()['counters'] to expose
    processing, comparison, and judgment counts -- each as an explicit numerator/denominator
    pair, never a naked rate."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(
        tmp_path, Obs, Jud, Reader,
        cohorts=[
            _envelope("c-1", _slot("champion", "emitted", items=["A"]),
                      _slot("challenger", "emitted", items=["A"]), state="agreement"),
            _envelope("c-2", _slot("champion", "emitted", items=["B"]),
                      _slot("challenger", "silent", items=[]), state="disagreement"),
        ],
        judgments=[dict(cohort_id="c-1", candidate_id="champion", candidate_version=1,
                        principal="evaluator", pref="KEEP")],
    )
    got = reader.peek(subject="s", purpose="p", limit=10)
    counters = got["counters"]

    # processing: persisted / eligible denominator
    assert counters["processing"]["persisted"] == 2, counters
    assert counters["processing"]["eligible"] == 2, counters

    # comparison: each comparison count paired with its cohort denominator
    assert counters["comparison"]["agreement"] == 1
    assert counters["comparison"]["disagreement"] == 1
    assert counters["comparison"]["cohorts"] == 2, "comparison counts carry the cohort denominator"

    # judgments: judged / candidate_slots / coverage, plus keep/drop
    assert counters["judgment"]["judged"] == 1
    assert counters["judgment"]["candidate_slots"] == 4, "2 cohorts x 2 slots = 4 candidate slots"
    assert counters["judgment"]["keep"] == 1
    assert counters["judgment"]["drop"] == 0

    # coverage is a STRUCTURED rate: {numerator, denominator}, never a naked number that
    # would masquerade as a coverage value.
    cov = counters["judgment"]["coverage"]
    assert cov == {"numerator": 1, "denominator": 4}, cov

    # ANY rendered rate (key ending in _rate, plus the structured coverage/keep/drop family)
    # must be a {numerator, denominator} dict -- with an optional rate float inside -- and
    # never a bare float/int. Walk every counter section.
    for section in counters.values():
        for key, val in section.items():
            if key.endswith("_rate") or key in ("coverage", "keep_rate", "drop_rate",
                                                "agreement_rate", "disagreement_rate"):
                assert isinstance(val, dict), f"rate '{key}' must be a dict, got {val!r}"
                assert "numerator" in val and "denominator" in val, (
                    f"rate '{key}' must carry numerator AND denominator, got {val!r}"
                )
                assert isinstance(val["numerator"], int) and isinstance(val["denominator"], int), (
                    f"rate '{key}' components must be integers, got {val!r}"
                )


# ---------------------------------------------------------------------------
# Pin 7 -- peek status transitions, exercised causally.
# ---------------------------------------------------------------------------

def test_first_peek_is_unpeeked_then_mark_peeked_makes_fresh(tmp_path):
    """The first peek of a real cohort is 'unpeeked'; mark_peeked writes a seen receipt and
    the NEXT peek reports 'fresh' -- the state transition, not a set-membership guess."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    obs.write_envelope(_envelope("c-1", _slot("champion", "emitted", items=["A"]),
                                 _slot("challenger", "emitted", items=["A"])))
    first = reader.peek(subject="s", purpose="p", limit=10)
    row = first["rows"][0]
    assert row["peek_state"] == "unpeeked", row

    reader.mark_peeked(cohort_id="c-1", principal="evaluator")
    second = reader.peek(subject="s", purpose="p", limit=10)
    row2 = second["rows"][0]
    assert row2["peek_state"] == "fresh", row2


def test_compacted_cohort_surfaces_stale_when_included(tmp_path):
    """After compaction, a normal peek omits (or renders stale) the cohort, but
    peek(..., include_stale=True) must include a 'stale' manifest row."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    obs.write_envelope(_envelope("c-1", _slot("champion", "emitted", items=["A"]),
                                 _slot("challenger", "emitted", items=["A"])))
    obs.compact(cohort_id="c-1", reason="expired")
    got = reader.peek(subject="s", purpose="p", limit=10, include_stale=True)
    stale_rows = [r for r in got["rows"] if r.get("peek_state") == "stale"]
    assert stale_rows, "include_stale=True must surface the compacted cohort as stale"


def test_contract_head_resolver_failure_status_unknown(tmp_path):
    """An injected contract-head resolver that fails must yield a top-level status=unknown
    with a reason -- never a silent ok or a fabricated fresh/stale. A cohort must exist so
    the resolver is actually invoked (a correct reader resolves heads only for returned
    rows), otherwise no reader would ever call it and the test would pass vacuously."""
    Cat, Obs, Jud, Reader = _require()
    obs = Obs(str(tmp_path / "obs.sqlite"))
    jud = Jud(str(tmp_path / "jud.sqlite"))
    # Seed one matching envelope FIRST, so peek has a row whose head it must resolve.
    obs.write_envelope(_envelope("c-1", _slot("champion", "emitted", items=["A"]),
                                 _slot("challenger", "emitted", items=["A"])))
    reader = ShadowShelfReader(obs, jud)

    def failing_resolver(cohort_id):
        raise RuntimeError("contract head unresolved")

    reader.set_contract_head_resolver(failing_resolver)
    got = reader.peek(subject="s", purpose="p", limit=10)
    assert got["status"] == "unknown", got
    assert got["reasons"], "unknown must carry a reason"


def test_peek_is_bounded_by_limit(tmp_path):
    """Seed more rows than limit; the reader must return at most `limit` rows. A reader
    that ignores its bound (returns everything) fails here."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    for i in range(10):
        obs.write_envelope(_envelope(f"c-{i}", _slot("champion", "emitted", items=[f"A{i}"]),
                                     _slot("challenger", "emitted", items=[f"A{i}"])))
    got = reader.peek(subject="s", purpose="p", limit=3)
    assert got["status"] == "ok", got
    assert len(got["rows"]) <= 3, f"peek(limit=3) must return at most 3 rows, got {len(got['rows'])}"


def test_disagreement_ranks_before_agreement_independent_of_order(tmp_path):
    """Disagreements-first: seed an OLDER disagreement and a NEWER agreement, in that
    insertion order; the disagreement must still surface BEFORE the agreement. Ordinary
    newest-first ordering would put the agreement first, so only state priority can pass."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    # Older disagreement inserted first.
    obs.write_envelope(_envelope("c-disagree", _slot("champion", "emitted", items=["X"]),
                                 _slot("challenger", "silent", items=[]), state="disagreement"))
    # Newer agreement inserted second. A recency-only reader would put this first.
    obs.write_envelope(_envelope("c-agree", _slot("champion", "emitted", items=["X"]),
                                 _slot("challenger", "emitted", items=["X"]), state="agreement"))
    got = reader.peek(subject="s", purpose="p", limit=10)
    rows = got["rows"]
    states = [r.get("state") for r in rows]
    assert "disagreement" in states and "agreement" in states, states
    assert states.index("disagreement") < states.index("agreement"), (
        "disagreement must precede agreement regardless of insertion order, got " + str(states)
    )


# ---------------------------------------------------------------------------
# Pin 7b -- healthy-empty / unavailable / partial are three DISTINCT shapes.
# ---------------------------------------------------------------------------

def test_healthy_empty_peek_is_ok_not_failure(tmp_path):
    """An empty but READABLE observation register is status=ok with reasons empty and
    rows=[]. Needs a readable judgment store to be ok."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    got = reader.peek(subject="s", purpose="p", limit=10)
    assert got["status"] == "ok", got
    assert got["reasons"] == [], got
    assert got["rows"] == [], "healthy empty renders empty rows, not a failure"


def test_missing_observation_register_is_unavailable_exact_dict(tmp_path):
    """A degraded observation store (unreadable DB) must yield an EXACT dict with
    status=unavailable, nonempty reasons, rows=[]. Construction returns a degraded store,
    it does not raise, so the reader can render the state."""
    Cat, Obs, Jud, Reader = _require()
    jud = Jud(str(tmp_path / "jud.sqlite"))
    obs = Obs(str(tmp_path / "does_not_exist" / "nope.sqlite"))  # degraded, not raising
    reader = ShadowShelfReader(obs, jud)
    got = reader.peek(subject="s", purpose="p", limit=10)
    assert isinstance(got, dict), "peek must return a dict, never a bare list"
    assert got["status"] == "unavailable", got
    assert got["reasons"], "unavailable must name a reason"
    assert got["rows"] == [], "unavailable renders empty rows, not silent []"


def test_missing_judgment_with_observations_is_partial(tmp_path):
    """Readable observations + judgment_store=None -> status=partial with rows still
    surfacing; the judgment gap is named in reasons."""
    Cat, Obs, Jud, Reader = _require()
    obs = Obs(str(tmp_path / "obs.sqlite"))
    obs.write_envelope(_envelope("c-1", _slot("champion", "emitted", items=["A"]),
                                 _slot("challenger", "emitted", items=["A"])))
    reader = ShadowShelfReader(obs, judgment_store=None)
    got = reader.peek(subject="s", purpose="p", limit=10)
    assert got["status"] == "partial", got
    assert got["rows"], "observation rows still surface under partial"
    assert got["reasons"], "partial must name the judgment gap in reasons"


# ---------------------------------------------------------------------------
# Pin 8 -- seeded known-wrong unanimous cohort appears in the control sample.
# ---------------------------------------------------------------------------

def test_control_sample_returns_labeled_seeded_rows(tmp_path):
    """Control sampling must discriminate, not relabel the whole shelf as control."""
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    obs.write_envelope(_control_envelope("ctrl-known-wrong"))
    obs.write_envelope(_envelope(
        "organic-agreement",
        _slot("champion", "emitted", items=["A"]),
        _slot("challenger", "emitted", items=["A"]),
        state="agreement",
    ))
    ctrl = reader.control_sample(limit=10)
    assert ctrl, "control_sample must return the seeded cohort"
    found = [r for r in ctrl if r.get("cohort_id") == "ctrl-known-wrong"]
    assert found, "the known-wrong cohort must actually appear"
    assert found[0].get("control") is True, found[0]
    assert found[0].get("known_wrong") is True, found[0]
    assert not any(r.get("cohort_id") == "organic-agreement" for r in ctrl), (
        "an ordinary agreement must stay out of the control sample; returning every cohort "
        "with control labels is a false-green"
    )


# ---------------------------------------------------------------------------
# Pin 9 (reader-facing) -- compaction manifest keeps expired cohorts visible.
# ---------------------------------------------------------------------------

def test_compacted_cohort_stays_visible_via_manifests(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    obs.write_envelope(_envelope("c-1", _slot("champion", "emitted", items=["A"]),
                                 _slot("challenger", "emitted", items=["A"])))
    obs.compact(cohort_id="c-1", reason="expired")
    mans = reader.manifests(limit=10)
    m = [x for x in mans if x.get("cohort_id") == "c-1"]
    assert m, "compaction must leave a visible manifest for the cohort"
    row = m[0]
    for field in ("cohort_id", "content_hash", "reason", "observed_at", "compacted_at"):
        assert field in row, f"manifest must carry {field}"


# ---------------------------------------------------------------------------
# Pin 11 (reader-facing) -- health is explicit and complete.
# ---------------------------------------------------------------------------

def test_health_reports_all_required_keys(tmp_path):
    Cat, Obs, Jud, Reader = _require()
    reader, obs, jud = _ok_reader(tmp_path, Obs, Jud, Reader)
    h = reader.health()
    for key in ("rows", "bytes_per_envelope", "db_bytes", "wal_bytes", "backlog"):
        assert key in h, f"health must contain {key}"
    assert "state" in h, "health must carry an explicit state"
