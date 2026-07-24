"""Pins for core.library.taxonomy (A1 constants -- homes-and-order reconciliation)."""

from core.library import taxonomy as tx


def test_roster_is_capped_at_24():
    assert len(tx.CATEGORY_ROSTER) == 24
    assert len(set(tx.CATEGORY_ROSTER)) == 24


def test_roster_is_plane_clean():
    # A category never names a TYPE (LIBRARY canon) or an arc id.
    types = {"contract", "map", "design", "brief", "report", "chronicle", "ledger",
             "agent-contract", "skill", "pin", "receipt", "fossil", "ruling"}
    assert not types & set(tx.CATEGORY_ROSTER)
    assert not any(c.startswith("t1") or c.startswith("t0") for c in tx.CATEGORY_ROSTER)


def test_every_roster_entry_has_classifier_rules():
    assert set(tx.CATEGORY_KEYWORDS) == set(tx.CATEGORY_ROSTER)


def test_folds_resolve_into_roster_only():
    assert all(target in tx.CATEGORY_ROSTER for target in tx.CATEGORY_FOLDS.values())
    assert not set(tx.CATEGORY_FOLDS) & set(tx.CATEGORY_ROSTER)


def test_classify_caps_and_orders():
    got = tx.classify("bus security audit drift on the packet lane")
    assert 1 <= len(got) <= tx.CATEGORY_CAP_PER_ATOM
    assert "bus" in got and "audit" in got


def test_classify_known_examples():
    assert "substrate" in tx.classify("artifact-substrate blind half: atoms and projection")
    assert "wiki" in tx.classify("super-wiki graph backlinks and hierarchy trees")
    assert "recall" in tx.classify("recall funnel curator vNext")
    assert tx.classify("") == []


def test_classify_is_deterministic():
    text = "migration census enrichment of the library shelves"
    assert tx.classify(text) == tx.classify(text)


def test_resolve_folds_and_identity():
    assert tx.resolve("spend") == "performance"
    assert tx.resolve("reasoning") == "memory"
    assert tx.resolve("wiki") == "wiki"
    assert tx.resolve("nonsense-category") is None


def test_rel_roster_excludes_supersession():
    # Supersession rides first-class fields, never a rel edge (reconciliation section 7).
    assert "supersedes" not in tx.REL_ROSTER
    assert tx.REL_DEFAULT_BACKFILL in tx.REL_ROSTER
