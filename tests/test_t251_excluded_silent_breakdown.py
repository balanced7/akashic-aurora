"""T251 -- the recall instrument cannot say WHICH suppression rule fired.

MEASURED 2026-08-08, seven days of outcome rows:

    5851 calls | 1673 fired | 4178 silent
        excluded_silent  3309   (79% of silences)
        floor_silent      863   (21%)

`excluded_silent` means a lesson PASSED the relevance floor and was then deliberately
discarded. That happens four times more often than ranking fails to find anything -- which
inverted the working hypothesis. The trigger was assumed too weak; it is not. It finds the
right lessons and the exclusion layer throws them away.

BUT THAT NUMBER MERGES TWO RULES WITH OPPOSITE FIXES, both bumping `stats_out["excluded"]`:

  ANTI-REPEAT (at_action.py:1363) -- source in `exclude_sources`, a per-SESSION seen-set. In a
    twelve-hour session a lesson surfaced at hour one can never fire again at hour eight.
  SELF-ECHO   (at_action.py:1367) -- authored by the calling agent within 2h. It mutes exactly
    the lesson its author most recently learned, which mechanically explains the sharpest miss
    on record: a lesson written and then violated two commits later.

Intra-call dedup correctly does NOT increment (the `and src in excl` guard), so the merge is
genuinely two-way and not three.

THE REASON STRING STAYS `excluded_silent` ON PURPOSE. Renaming it would orphan the seven days
of rows that produced this finding, and an instrument that loses its own baseline when improved
is worse than the ambiguity it fixes. The breakdown rides a NEW field.

Daniil, 2026-08-08, asked for hints "with the ability to tune them or adjust". You cannot tune
what you cannot measure separately. This is the measurement that makes the tuning decision
possible; it is not the tuning.
"""
import json

import pytest

from core.recall import at_action as AA


@pytest.fixture
def outcomes(tmp_path, monkeypatch):
    """Redirect the outcome log so these pins never touch the live 7-day baseline."""
    monkeypatch.setattr(AA, "_OUTCOME_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(AA, "_OUTCOME_FILE", "outcomes.jsonl", raising=False)
    return tmp_path / "outcomes.jsonl"


def _rows(path):
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_the_recorder_accepts_and_persists_an_exclusion_kind(outcomes):
    """The carrier. Without a field on the row, the breakdown cannot survive the process."""
    AA._record_outcome("silent", "excluded_silent", query="q", excl_kind="self_echo")
    rows = _rows(outcomes)
    assert rows, "no outcome row was written"
    assert rows[0].get("excl_kind") == "self_echo", (
        f"the exclusion kind did not reach the row: {rows[0]}")


def _write_legacy_row(path, **extra):
    """A row in the PRE-T251 shape: no excl_kind key at all.

    Written raw on purpose. Omitting the kwarg no longer produces a legacy row -- the recorder
    now always emits the key -- and a fixture that only SIMULATES the old shape would let the
    unknown/unclassified split pass while being untested against the thing it exists for.
    """
    import time as _t
    row = {"at": _t.time(), "outcome": "silent", "reason": "excluded_silent",
           "q": "q", "n_items": 0, "agent": "", "query_shape": ""}
    row.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def test_existing_rows_without_the_field_still_parse(outcomes):
    """Seven days of history has no excl_kind. It must not become unreadable.

    An instrument that loses its own baseline when improved is worse than the ambiguity it
    was improved to fix -- the baseline IS the finding.
    """
    outcomes.parent.mkdir(parents=True, exist_ok=True)
    _write_legacy_row(outcomes)
    rows = _rows(outcomes)
    assert "excl_kind" not in rows[0], "the fixture must produce a genuinely legacy row"
    assert rows[0]["reason"] == "excluded_silent", "the historical reason string must not move"
    assert AA.silence_rate(window_s=86400.0)["by_reason"]["excluded_silent"] == 1


def test_silence_rate_breaks_excluded_down_by_kind(outcomes):
    """The whole point: which rule do I tune?"""
    for kind, n in (("antirepeat", 3), ("self_echo", 2), ("mixed", 1)):
        for _ in range(n):
            AA._record_outcome("silent", "excluded_silent", query="q", excl_kind=kind)
    AA._record_outcome("silent", "floor_silent", query="q")
    AA._record_outcome("fired", "", query="q", n_items=2)

    r = AA.silence_rate(window_s=86400.0)
    assert r["by_reason"]["excluded_silent"] == 6
    by_kind = r.get("excluded_by_kind") or {}
    assert by_kind.get("antirepeat") == 3, f"expected 3 antirepeat, got {by_kind}"
    assert by_kind.get("self_echo") == 2, f"expected 2 self_echo, got {by_kind}"
    assert by_kind.get("mixed") == 1, f"expected 1 mixed, got {by_kind}"


def test_rows_with_no_kind_are_counted_as_unknown_not_dropped(outcomes):
    """A silent drop in the instrument that measures silent drops would be its own punchline."""
    outcomes.parent.mkdir(parents=True, exist_ok=True)
    _write_legacy_row(outcomes)
    AA._record_outcome("silent", "excluded_silent", query="q", excl_kind="self_echo")

    r = AA.silence_rate(window_s=86400.0)
    by_kind = r.get("excluded_by_kind") or {}
    assert sum(by_kind.values()) == r["by_reason"]["excluded_silent"], (
        f"the breakdown must account for EVERY excluded row: {by_kind} vs "
        f"{r['by_reason']['excluded_silent']}")
    assert by_kind.get("unknown") == 1, f"the pre-T251 row must be visible as unknown: {by_kind}"


def test_an_item_breaking_both_rules_is_counted_under_both(outcomes):
    """composer's finding, and the one that would have broken the tuning decision.

    `if src in excl: continue` ran BEFORE `_self_echo` was ever evaluated, so an item breaking
    both rules was recorded as anti-repeat ONLY. Loosen anti-repeat on that evidence and the
    item is still suppressed by self-echo on the next run -- the instrument's implicit promise,
    that tuning the rule it names will un-silence the call, was false for exactly those items.

    An instrument built to choose between two rules must not hide that both fired.
    """
    stats = {}
    AA._note_exclusion(stats, [AA.EXCL_ANTIREPEAT, AA.EXCL_SELF_ECHO])
    assert stats["excluded"] == 1, (
        f"the TOTAL counts ITEMS, not rule-hits -- it gates the outcome label via "
        f"excluded >= above_floor and must not double-count: {stats}")
    assert stats[f"excluded_{AA.EXCL_ANTIREPEAT}"] == 1, stats
    assert stats[f"excluded_{AA.EXCL_SELF_ECHO}"] == 1, stats


def test_the_row_carries_item_counts_not_only_a_call_level_label(outcomes):
    """composer's finding: 'mixed' is lossy at the call level.

    A call with 99 anti-repeat items and 1 self-echo item is labelled "mixed", identically to
    a 1-and-1 call. The label cannot answer which rule dominates, which is the only question
    the instrument exists to answer.
    """
    AA._record_outcome("silent", "excluded_silent", query="q", excl_kind="mixed",
                       excl_counts={AA.EXCL_ANTIREPEAT: 99, AA.EXCL_SELF_ECHO: 1})
    row = _rows(outcomes)[0]
    assert row.get("excl_counts", {}).get(AA.EXCL_ANTIREPEAT) == 99, (
        f"item-level counts did not reach the row, so 'mixed' stays uninterpretable: {row}")


def test_a_new_unclassified_row_is_not_filed_under_the_old_baseline(outcomes):
    """composer's finding: `row.get(k) or 'unknown'` conflates two different things.

    A pre-T251 row has NO excl_kind key. A future row written with an empty kind -- say a third
    exclusion rule that increments the total without setting either flag -- has the key and an
    empty value. Folding both into "unknown" would hide the new rule inside the historical
    baseline, which is precisely the merge this whole task exists to undo.
    """
    outcomes.parent.mkdir(parents=True, exist_ok=True)
    _write_legacy_row(outcomes)                                                  # genuinely old
    AA._record_outcome("silent", "excluded_silent", query="q", excl_kind="")     # new, unclassified
    by_kind = AA.silence_rate(window_s=86400.0)["excluded_by_kind"]
    assert by_kind.get("unknown") == 1, f"only the pre-T251 row is 'unknown': {by_kind}"
    assert by_kind.get("unclassified") == 1, (
        f"a new row with an empty kind must be visibly UNCLASSIFIED, not folded into the "
        f"historical baseline: {by_kind}")


def test_the_two_rules_increment_separate_counters():
    """At the source. Both sites bumped one counter, which is why the split was impossible.

    Exercised through _lessons' stats_out contract rather than by reading the file, because a
    text-scanning assertion here would pass on the comment that explains the fix.
    """
    stats = {}
    item = {"source": "learn:experiment:x", "text": "t", "trigger": "", "trigger_terms": []}
    AA._note_exclusion(stats, "antirepeat")
    AA._note_exclusion(stats, "self_echo")
    AA._note_exclusion(stats, "antirepeat")
    assert stats.get("excluded") == 3, f"the total must still be maintained: {stats}"
    assert stats.get("excluded_antirepeat") == 2, stats
    assert stats.get("excluded_self_echo") == 1, stats
    assert AA._excl_kind(stats) == "mixed", "both rules fired, so the kind is mixed"

    only_self = {}
    AA._note_exclusion(only_self, "self_echo")
    assert AA._excl_kind(only_self) == "self_echo"
