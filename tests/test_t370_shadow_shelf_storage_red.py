"""T370 Slice 0 -- RED pins, storage/cohort/comparison side (deepseek).

Pre-registered BEFORE any production code exists. Target module:
`core.recall.shadow_shelf`. Owned by deepseek; lane is pins 1-4 and 9-12 only
(reader/state/control/authority pins 5-8 belong to kimi's separate file).

RED discipline (M3 pre-registration, same shape as test_app_package_rung.py and
test_t366_fanout_evidence.py): every test below FAILS today because the module does
not resolve, and each failure names a SPECIFIC missing behavior rather than one
opaque collection error. To keep one missing import from hiding the suite, symbols
are resolved LAZILY per test via a tiny _resolve() helper -- so adding the module
piecemeal turns pins GREEN one at a time in dependency order, never all-at-once.

Do not "fix" these by making them pass trivially; a RED pin is the contract. Sunshine
integrates the spec, then turns these GREEN by building the module.

Isolation: every test that touches a store path uses tmp_path. No fixture here imports
or exercises model/Bifrost/Discord/EventLog/canonical-Store writers, and pin 12 proves
that property of the replay path itself by design.
"""
from __future__ import annotations

import importlib
import json
import sqlite3

import pytest

MODULE = "core.recall.shadow_shelf"


def _resolve(*names):
    """Resolve dotted symbols from the TARGET module, raising a Pytest skip-scoped
    error that names exactly which symbol is absent. Lazy so one missing import does
    not collapse every pin into a single collection failure."""
    try:
        mod = importlib.import_module(MODULE)
    except ImportError as exc:                      # module does not exist yet
        raise AssertionError(
            f"RED: {MODULE} does not import yet (reason: {exc}). "
            f"Expected a storage/cohort module; build it to turn these pins RED->GREEN."
        ) from exc
    missing = [n for n in names if not hasattr(mod, n)]
    if missing:
        raise AssertionError(
            f"RED: {MODULE} exists but is missing required symbol(s): "
            f"{', '.join(missing)}"
        )
    return mod


# ---------------------------------------------------------------- pin 1


def test_p1_contract_identity_is_a_stable_hash_of_the_tuple():
    """Pin 1: a behavior contract's identity hashes the 7-member tuple and is STABLE
    across process boundaries -- two constructions with identical tuple members yield
    the same id, and reordering any member changes it."""
    ss = _resolve("contract_id", "register_contract")
    c1 = ss.contract_id(
        input_kind="recall.at_action.rank.v1",
        outcome_schema=("emitted", "silent", "abstained", "error"),
        comparison="same_identity_set",
        retention="beta-14d",
        writers=("watcher", "evaluator"),
        reader="disagreements_first",
        delivery=None,
    )
    c2 = ss.contract_id(
        input_kind="recall.at_action.rank.v1",
        outcome_schema=("emitted", "silent", "abstained", "error"),
        comparison="same_identity_set",
        retention="beta-14d",
        writers=("watcher", "evaluator"),
        reader="disagreements_first",
        delivery=None,
    )
    assert c1 == c2, "same tuple -> same id (stable identity, not an object address)"

    # The STATED second half, made real: change ONE tuple member and the id changes.
    c3 = ss.contract_id(
        input_kind="recall.at_action.rank.v1",
        outcome_schema=("emitted", "silent", "abstained", "error"),
        comparison="score_comparable",          # <- the ONLY member that changed
        retention="beta-14d",
        writers=("watcher", "evaluator"),
        reader="disagreements_first",
        delivery=None,
    )
    assert c1 != c3, "changing one tuple member (comparison semantics) must change the id"


def test_p1_alias_same_tuple_second_name_refused():
    """Pin 1: two NAMES over one contract tuple are aliases; the registry refuses the
    second registration rather than minting a ghost category."""
    ss = _resolve("register_contract", "ContractAliasRefused")
    kwargs = dict(
        input_kind="recall.at_action.rank.v1",
        outcome_schema=("emitted", "silent", "abstained", "error"),
        comparison="same_identity_set",
        retention="beta-14d",
        writers=("watcher", "evaluator"),
        reader="disagreements_first",
        delivery=None,
    )
    ss.register_contract("rank-beta", **kwargs)
    with pytest.raises((ValueError, getattr(ss, "ContractAliasRefused", ValueError))):
        ss.register_contract("rank-beta-alias", **kwargs)


def test_p1_same_name_two_tuples_is_a_version_conflict_refused():
    """Pin 1: ONE name with TWO different tuples is a contract-version conflict, not a
    silent overwrite; it is refused so a name cannot silently re-point at new semantics."""
    ss = _resolve("register_contract")
    # Use a tuple distinct from the alias fixture above.  The contract registry is
    # intentionally process-lifetime state: reusing that fixture here would demand
    # both that its second name be refused (the preceding pin) and accepted (this pin).
    a = dict(input_kind="recall.at_action.rank.v1",
             outcome_schema=("emitted", "silent", "abstained", "error"),
             comparison="same_identity_set", retention="conflict-fixture-14d",
             writers=("watcher", "evaluator"), reader="disagreements_first", delivery=None)
    b = dict(a, comparison="score_comparable")          # differs ONLY in comparison semantics
    ss.register_contract("rank", **a)
    with pytest.raises(ValueError):
        ss.register_contract("rank", **b)


# ---------------------------------------------------------------- pin 2


def test_p2_one_envelope_is_atomic_and_carries_both_terminal_slots(tmp_path):
    """Pin 2: one transaction persists one complete cohort envelope for one source event,
    with terminal slots for BOTH champion and challenger -- including silence/abstained/
    error, which are real slots, never omitted rows."""
    ss = _resolve("open_observation", "record_envelope")
    db = ss.open_observation(tmp_path / "obs.sqlite")
    env = ss.record_envelope(
        db,
        source_fingerprint="sha256:abc",
        subject="sol", purpose_id="recall-at-action",
        contract_id="rank-beta", cohort_version=7, watcher_incarnation="host-1",
        decisions={
            "champion": {"outcome": "emitted", "items": [{"ref": "learn:experiment:x"}]},
            "challenger": {"outcome": "silent", "items": []},
        },
    )
    # Both slots are terminal -- a silent challenger is a PRESENT row, not absent.
    slots = env["decisions"]
    assert set(slots) == {"champion", "challenger"}
    assert slots["champion"]["outcome"] == "emitted"
    assert slots["challenger"]["outcome"] == "silent"


def test_p2_duplicate_source_cohort_write_is_idempotent(tmp_path):
    """Pin 2: re-recording the same source/cohort does not mint a second envelope."""
    ss = _resolve("open_observation", "record_envelope", "count_envelopes")
    db = ss.open_observation(tmp_path / "obs.sqlite")
    common = dict(subject="sol", purpose_id="recall-at-action",
                  contract_id="rank-beta", cohort_version=7, watcher_incarnation="host-1",
                  decisions={"champion": {"outcome": "emitted", "items": []},
                             "challenger": {"outcome": "abstained", "items": []}})
    ss.record_envelope(db, source_fingerprint="sha256:dup", **common)
    ss.record_envelope(db, source_fingerprint="sha256:dup", **common)
    assert ss.count_envelopes(db) == 1


# ---------------------------------------------------------------- pin 3


def test_p3_comparison_state_matrix_exact():
    """Pin 3: the comparison state matrix is EXACT -- six states, including unevaluated
    (all abstained) and unavailable (all errored), which must NEVER collapse into
    agreement or silence. Agreement requires BOTH candidates to emit the SAME bounded
    item identities; emitted-and-different-items is DISAGREEMENT, not agreement."""
    ss = _resolve("compare")
    # Slots use the SAME schema P2 declares: {"outcome": ..., "items": [...]} -- the
    # role (champion/challenger) is the caller's key, not a field inside the slot.
    # emitted/emitted with the SAME item identities -> agreement
    agree = ss.compare(
        {"outcome": "emitted", "items": [{"ref": "learn:experiment:x"}]},
        {"outcome": "emitted", "items": [{"ref": "learn:experiment:x"}]},
    )
    # emitted/emitted with DIFFERENT item identities -> disagreement (not agreement)
    disagree_items = ss.compare(
        {"outcome": "emitted", "items": [{"ref": "learn:experiment:x"}]},
        {"outcome": "emitted", "items": [{"ref": "learn:experiment:y"}]},
    )
    # emitted vs deliberate silence -> disagreement
    disagree = ss.compare({"outcome": "emitted"}, {"outcome": "silent"})
    abst_delta = ss.compare({"outcome": "emitted"}, {"outcome": "abstained"})
    incomplete = ss.compare({"outcome": "emitted"}, {"outcome": "error"})
    unevaluated = ss.compare({"outcome": "abstained"}, {"outcome": "abstained"})
    unavailable = ss.compare({"outcome": "error"}, {"outcome": "error"})
    assert agree == "agreement"
    assert disagree_items == "disagreement"      # same terminal, different identity
    assert disagree == "disagreement"            # emitted vs deliberate silence
    assert abst_delta == "abstention_delta"
    assert incomplete == "incomplete"
    assert unevaluated == "unevaluated"          # all-abstained is NOT agreement
    assert unavailable == "unavailable"          # all-error is NOT silence


# ---------------------------------------------------------------- pin 4


def test_p4_oversize_output_becomes_a_visible_error_slot_preserving_cohort(tmp_path):
    """Pin 4: the 8 KiB cap turns oversize candidate output into a terminal `error` slot
    WITH a reason -- it does not disappear, and it does not block the complete envelope
    from committing."""
    ss = _resolve("open_observation", "record_envelope", "ENVELOPE_CAP")
    db = ss.open_observation(tmp_path / "obs.sqlite")
    big = "x" * (ss.ENVELOPE_CAP * 2)              # well over cap
    env = ss.record_envelope(
        db, source_fingerprint="sha256:big", subject="sol", purpose_id="recall-at-action",
        contract_id="rank-beta", cohort_version=7, watcher_incarnation="host-1",
        decisions={"champion": {"outcome": "emitted", "items": [{"ref": big}]},
                   "challenger": {"outcome": "emitted", "items": []}},
    )
    assert env["decisions"]["champion"]["outcome"] == "error"
    assert env["decisions"]["champion"].get("reason")
    # The complete cohort still committed -- one slot erred, the envelope is intact.
    assert set(env["decisions"]) == {"champion", "challenger"}


# ---------------------------------------------------------------- pin 9


def test_p9_compaction_writes_a_visible_manifest_before_deletion(tmp_path):
    """Pin 9: compaction records a manifest (identity, content hash, reason, timestamps)
    BEFORE removing expired raw envelopes, so death is visible, never a silent vanish."""
    ss = _resolve("open_observation", "compact", "read_manifest")
    db = ss.open_observation(tmp_path / "obs.sqlite")
    # Seed one envelope, then force compaction past its TTL.
    ss.record_envelope(
        db, source_fingerprint="sha256:old", subject="sol", purpose_id="recall-at-action",
        contract_id="rank-beta", cohort_version=7, watcher_incarnation="host-1",
        decisions={"champion": {"outcome": "emitted", "items": []},
                   "challenger": {"outcome": "silent", "items": []}},
    )
    manifest = ss.compact(db, before_hours=0)
    assert manifest, "compaction must return/record a manifest, never silently delete"
    assert manifest.get("removed", 0) >= 1
    rows = ss.read_manifest(db)
    assert rows, "manifest rows must be readable after the fact"
    assert "sha256:old" in json.dumps(rows)


def test_p9_judgments_survive_compaction(tmp_path):
    """Pin 9: judgments live in a separate register the observation writer cannot reach,
    and they survive compaction of the raw envelope they point at."""
    ss = _resolve("open_observation", "open_judgment", "append_judgment", "compact")
    obs = ss.open_observation(tmp_path / "obs.sqlite")
    jud = ss.open_judgment(tmp_path / "jud.sqlite")
    env = ss.record_envelope(
        obs, source_fingerprint="sha256:keep", subject="sol", purpose_id="recall-at-action",
        contract_id="rank-beta", cohort_version=7, watcher_incarnation="host-1",
        decisions={"champion": {"outcome": "emitted", "items": [{"ref": "learn:experiment:y"}]},
                   "challenger": {"outcome": "silent", "items": []}},
    )
    env_id = env["evaluation_id"]
    ss.append_judgment(jud, target_evaluation=env_id, candidate_id="champion",
                       candidate_version=7, verdict="KEEP", principal="operator:daniel")
    ss.compact(obs, before_hours=0)                # raw envelope expires
    # Judgment must still resolve, because it carries its own bounded evidence snapshot.
    assert ss.list_judgments(jud), "judgments survive compaction"


# ---------------------------------------------------------------- pin 10


def test_p10_kill_between_calc_and_commit_is_zero_or_complete(tmp_path):
    """Pin 10: killing the host between candidate calculation and commit yields either ZERO
    cohort rows or ONE complete envelope -- never a partial cohort with one slot committed
    and the other absent.

    The kill is INJECTED through a test-only before-commit fault seam (dependency
    injection, not partial-row implementation knowledge): record_envelope accepts an
    optional before_commit callable the module invokes after both candidate slots are
    calculated but BEFORE the transaction commits. Raising there models the kill. No
    monkeypatch global or unused local here -- the fault is explicit and observed."""
    ss = _resolve("open_observation", "record_envelope", "count_envelopes", "list_envelopes")
    db = ss.open_observation(tmp_path / "obs.sqlite")

    class Kill(RuntimeError):
        """Models the process dying mid-commit."""

    common = dict(source_fingerprint="sha256:kill", subject="sol",
                  purpose_id="recall-at-action", contract_id="rank-beta",
                  cohort_version=7, watcher_incarnation="host-1",
                  decisions={"champion": {"outcome": "emitted", "items": []},
                             "challenger": {"outcome": "silent", "items": []}})

    # Inject the fault: the cohort is calculated, then the host dies before commit.
    with pytest.raises(Kill):
        ss.record_envelope(db, before_commit=lambda: (_ for _ in ()).throw(Kill()),
                           **common)

    # Zero cohort observable -- the fault must not leave a half-committed envelope.
    assert ss.count_envelopes(db) == 0, \
        "a fault before commit must leave ZERO cohort rows, not a partial one"
    assert ss.list_envelopes(db) == []

    # Retry the SAME cohort cleanly: exactly one complete cohort, both slots terminal.
    ss.record_envelope(db, **common)
    assert ss.count_envelopes(db) == 1
    rows = ss.list_envelopes(db)
    assert len(rows) == 1
    assert set(rows[0]["decisions"]) == {"champion", "challenger"}, \
        "the retried cohort must carry both terminal slots (no half-cohort)"


def test_p10_retry_after_kill_is_idempotent(tmp_path):
    """Pin 10: retrying the same cohort after a kill does not duplicate the envelope
    (idempotency keyed on source/cohort fingerprint, not a backend cursor)."""
    ss = _resolve("open_observation", "record_envelope", "count_envelopes")
    db = ss.open_observation(tmp_path / "obs.sqlite")
    common = dict(subject="sol", purpose_id="recall-at-action", contract_id="rank-beta",
                  cohort_version=7, watcher_incarnation="host-1",
                  decisions={"champion": {"outcome": "emitted", "items": []},
                             "challenger": {"outcome": "silent", "items": []}})
    ss.record_envelope(db, source_fingerprint="sha256:retry", **common)
    ss.record_envelope(db, source_fingerprint="sha256:retry", **common)
    assert ss.count_envelopes(db) == 1


# ---------------------------------------------------------------- pin 11


def test_p11_resource_report_names_rows_bytes_and_backlog(tmp_path):
    """Pin 11: the resource report carries a top-level state/status plus structured
    unavailable reasons; a missing DB path must read UNAVAILABLE, never as healthy
    measured zeros, and a present DB reports its four metrics."""
    ss = _resolve("resource_report")
    db_path = tmp_path / "obs.sqlite"

    # Missing path -> top-level state names it unavailable, metrics are NOT healthy zeros.
    rep_missing = ss.resource_report(db_path)
    assert "status" in rep_missing, "resource report must carry a top-level status/state"
    assert rep_missing["status"] != "ok", \
        "a missing DB must not report status ok"
    for field in ("rows", "bytes_per_envelope", "db_bytes", "wal_bytes", "backlog"):
        assert field in rep_missing, f"resource report must name {field}"
        val = rep_missing[field]
        assert val is None or isinstance(val, (int, float)), f"{field} is a value or None"

    # A present DB: metrics are real numbers and status is not the unavailable state.
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    con.commit()
    con.close()
    rep_ok = ss.resource_report(db_path)
    assert rep_ok["status"] != "unavailable", \
        "a present DB must not report unavailable"
    assert isinstance(rep_ok["rows"], int)
    assert isinstance(rep_ok["db_bytes"], int)
    assert rep_ok["db_bytes"] > 0, "a present non-empty DB reports real bytes"


def test_p11_unavailable_metrics_carry_structured_reasons(tmp_path):
    """Pin 11: an unavailable metric names WHY, structured, never a bare healthy zero."""
    ss = _resolve("resource_report")
    db_path = tmp_path / "absent_obs.sqlite"
    rep = ss.resource_report(db_path)
    # Either the metric is None with an explicit reason, or the report carries an
    # unavailable-reasons map; absence must be attributable to a cause, not silence.
    reasons = rep.get("unavailable") or rep.get("unavailable_reasons") or {}
    if rep.get("status") != "ok":
        assert reasons or rep.get("reason"), \
            "an unavailable report must carry a structured reason for its state"


def test_p11_auto_pause_at_configurable_thresholds(tmp_path):
    """Pin 11: the watcher auto-pauses at configurable limits; pilot defaults are WAL > 100 MiB
    or backlog > 2x trailing 24h input. The threshold is a parameter, not a hardcoded literal."""
    ss = _resolve("should_pause", "DEFAULT_WAL_PAUSE_BYTES", "DEFAULT_BACKLOG_MULTIPLIER")
    assert ss.DEFAULT_WAL_PAUSE_BYTES == 100 * 1024 * 1024     # 100 MiB
    assert ss.DEFAULT_BACKLOG_MULTIPLIER == 2.0
    # Over the WAL ceiling -> pause.
    assert ss.should_pause(wal_bytes=ss.DEFAULT_WAL_PAUSE_BYTES + 1,
                           backlog_ratio=1.0)
    # Over the backlog multiplier -> pause (configurable multiplier exercised).
    assert ss.should_pause(wal_bytes=0, backlog_ratio=2.5,
                           backlog_multiplier=ss.DEFAULT_BACKLOG_MULTIPLIER)
    # Under both -> run.
    assert not ss.should_pause(wal_bytes=10, backlog_ratio=1.0)


# ---------------------------------------------------------------- pin 12


_FORBIDDEN_P12 = (
    "core.comm.bus",
    "core.comm.bifrost",
    "core.comm.discord",
    "core.events.event_log",
    "core.foundation.store",
    "core.foundation.sqlite_store",
    "core.recall.at_action",
)


def test_p12_module_source_has_no_forbidden_imports():
    """Pin 12a: parse the FULL SOURCE of the shadow_shelf module with inspect.getsource
    + ast and reject any Import/ImportFrom node matching a forbidden module.

    Causal and package-init proof: inspect.getsource returns the module's own text,
    so core/recall/__init__.py's `from core.recall.at_action import ...` is NOT in
    scope. Only what shadow_shelf itself imports is judged."""
    ss = _resolve("replay_fixture")     # proves the module imports at all
    import ast
    import inspect

    src = inspect.getsource(ss)         # the module's own source, init excluded
    tree = ast.parse(src)
    offending = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _FORBIDDEN_P12:
                    offending.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module in _FORBIDDEN_P12:
                offending.append(node.module)
    assert not offending, (
        f"shadow_shelf source imports forbidden writer surface: {sorted(set(offending))}"
    )


def test_p12_replay_causes_no_forbidden_imports(tmp_path, monkeypatch):
    """Pin 12b: wrap builtins.__import__ ONLY around the replay_fixture call and record
    every attempted import; reject any forbidden module name.

    The module is ALREADY loaded before the guard is installed, so the wrapper observes
    only imports the replay call ITSELF triggers -- not package-init, not prior tests,
    not the test harness's own imports. If replay accepts an injected writer argument,
    it is passed a poison stub that raises on any use, so a candidate cannot smuggle a
    writer through a parameter either."""
    ss = _resolve("replay_fixture")
    attempted = []

    real_import = __import__

    def _guarded_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        attempted.append(name)
        # Anything matching a forbidden module OR under its package tree is refused.
        if (name in _FORBIDDEN_P12
                or any(name == f or name.startswith(f + ".") for f in _FORBIDDEN_P12)):
            raise ImportError(f"replay attempted forbidden import: {name}")
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", _guarded_import)

    # Poison any writer the replay might accept as an argument: if it CALLS the writer,
    # the replay path is exercising a wrong-plane side effect and must fail.
    class _PoisonWriter:
        def __getattr__(self, item):
            def _boom(*a, **k):
                raise AssertionError(f"replay called forbidden writer.{item}")
            return _boom

    # replay_fixture signature is not yet fixed; probe by passing a poison writer only
    # if the function accepts an optional writer kwarg, else call it positionally-pure.
    import inspect as _inspect
    params = _inspect.signature(ss.replay_fixture).parameters
    call_kwargs = {}
    if "writer" in params:
        call_kwargs["writer"] = _PoisonWriter()

    result = ss.replay_fixture(str(tmp_path), **call_kwargs)

    forbidden_attempts = {n for n in attempted
                          if n in _FORBIDDEN_P12
                          or any(n.startswith(f + ".") for f in _FORBIDDEN_P12)}
    assert not forbidden_attempts, (
        f"replay_fixture attempted a forbidden import: {sorted(forbidden_attempts)}"
    )
    assert isinstance(result, (list, dict)), "replay returns a bounded result"
