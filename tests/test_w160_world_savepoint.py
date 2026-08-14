"""W160 pins: a world savepoint -- both planes under one name, or neither.

Daniil, 2026-08-14, stating the intent behind the whole three-world arc: "so that we can
test things that could be risky quicker and have A POINT TO RESTORE FROM. I think this
approach should allow us faster iteration even though it is more steps."

THE GAP THIS CLOSES, measured before building:

    code    git checkout <sha>          -> returns to a KNOWN state.
    memory  seed again from prod        -> returns to a FRESH state.

    Alpha was seeded at 05:56 when prod held 6,624 carried keys; prod now holds 20,691.
    Re-seeding does not return the twin to where it was, it returns it to somewhere new.
    deepseek's round-3 distinction, which this makes concrete: RE-CLONABLE means
    re-creatable to FRESH; DISCARDABLE means re-creatable to KNOWN. A restore POINT
    requires the second, and only the code plane had it.

BOTH PLANES OR NEITHER, and this is the pin that matters most. W156h was a tool whose two
planes addressed different worlds and flushed production twice. A savepoint that restored
code but not memory would be the same defect wearing a friendlier name: the checkout would
say one thing, the store another, and the operator would believe the label. So availability
of BOTH planes is verified before either is touched.

A SAVEPOINT OF A DIRTY TREE IS NOT A SAVEPOINT, and says so rather than pretending -- git
can only restore what was committed, so uncommitted work is outside what the label can
promise. Recording that honestly at SAVE time is cheaper than discovering it at restore.
"""
import pytest

from core.coord import world_savepoint as SP


def _sp(world="alpha", label="before-risky-thing", sha="a3c4b038",
        snapshot="20260814_015417", dirty=0):
    return SP.Savepoint(world=world, label=label, git_sha=sha,
                        knowledge_snapshot=snapshot, dirty_at_save=dirty,
                        saved_at="2026-08-14T09:00:00+00:00")


# ------------------------------------------------------------------ both planes or neither

def test_b1_a_savepoint_missing_its_memory_half_is_refused_before_anything_is_touched():
    """The W156h shape: two planes, one restored, the operator believing the label."""
    sp = _sp(snapshot=None)
    ok, why = SP.can_restore(sp, snapshot_exists=lambda n: False, tree_dirty=0)
    assert ok is False
    assert "both" in why.lower() or "memory" in why.lower()


def test_b2_a_savepoint_whose_snapshot_has_been_pruned_is_refused():
    """Snapshots self-prune (KEEP_LAST). A label pointing at a pruned snapshot must fail
    loudly at the gate, not half-restore and leave a twin whose code and memory disagree."""
    ok, why = SP.can_restore(_sp(), snapshot_exists=lambda n: False, tree_dirty=0)
    assert ok is False
    assert "20260814_015417" in why


def test_b3_a_complete_savepoint_passes():
    ok, why = SP.can_restore(_sp(), snapshot_exists=lambda n: True, tree_dirty=0)
    assert ok is True, why


# ------------------------------------------------------------------ blast radius

def test_r1_restoring_prod_is_refused_without_explicit_consent():
    """Same law as the backup door after it flushed prod twice: routing safety is not
    consent, and an operation correctly aimed at prod is still aimed at prod."""
    ok, why = SP.can_restore(_sp(world="prod"), snapshot_exists=lambda n: True,
                             tree_dirty=0, consent=False)
    assert ok is False
    assert "prod" in why.lower() and "consent" in why.lower()


def test_r2_prod_restore_proceeds_with_explicit_consent():
    ok, _ = SP.can_restore(_sp(world="prod"), snapshot_exists=lambda n: True,
                           tree_dirty=0, consent=True)
    assert ok is True


def test_g1_generated_dirt_does_not_count_as_dirty():
    """FOUND BY RUNNING IT. This repo's working tree is NEVER clean: docs/MAP.md and
    docs/DOORS.md declare themselves auto-generated, and chronicles/memory.md,
    data/corpus-digests/, data/verb-registry/ and state/coord/tasks.json are all rewritten
    by simply operating the system. Counting those as dirt made every savepoint PARTIAL and
    -- far worse -- made can_restore refuse FOREVER, so the feature was unusable on the
    repo it was built for. An always-on caveat is an ignored caveat; a never-satisfiable
    guard is a disabled guard."""
    files = ["docs/MAP.md", "docs/DOORS.md", "chronicles/memory.md",
             "data/corpus-digests/digests.jsonl", "state/coord/tasks.json"]
    assert SP.authored_dirt(files) == []


def test_g2_authored_dirt_still_counts():
    files = ["core/world.py", "docs/MAP.md", "tests/test_x.py"]
    assert sorted(SP.authored_dirt(files)) == ["core/world.py", "tests/test_x.py"]


def test_g3_the_split_is_reported_not_silently_dropped():
    """Ignoring generated files is a judgement, and a judgement nobody can see is one
    nobody can correct."""
    sp = SP.Savepoint(world="alpha", label="x", git_sha="abc", knowledge_snapshot="s",
                      saved_at="t", dirty_at_save=0, generated_at_save=6)
    assert sp.complete is True
    assert "6" in sp.note and "generated" in sp.note.lower()


def test_r3_a_dirty_tree_blocks_restore_because_restoring_would_discard_it():
    """Look at the target before overwriting. Uncommitted work in the twin is real work."""
    ok, why = SP.can_restore(_sp(), snapshot_exists=lambda n: True, tree_dirty=7)
    assert ok is False
    assert "7" in why and ("uncommitted" in why.lower() or "discard" in why.lower())


def test_r4_the_refusal_names_the_way_out():
    ok, why = SP.can_restore(_sp(), snapshot_exists=lambda n: True, tree_dirty=7)
    assert "commit" in why.lower() or "stash" in why.lower()


# ------------------------------------------------------------------ honesty at save time

def test_s1_saving_a_dirty_tree_records_the_dirt_rather_than_hiding_it():
    """git restores what was COMMITTED, so uncommitted work is outside what this label can
    promise. Recording it at save time is cheaper than discovering it at restore."""
    sp = _sp(dirty=4)
    assert sp.complete is False
    assert "4" in sp.caveat


def test_s2_a_clean_savepoint_says_it_is_complete():
    assert _sp(dirty=0).complete is True


def test_s3_a_savepoint_renders_both_plane_identities():
    """A label that cannot be resolved back to a sha AND a snapshot is a name, not a point."""
    out = _sp().render()
    assert "a3c4b038" in out and "20260814_015417" in out and "alpha" in out


def test_s4_savepoints_roundtrip_through_their_file(tmp_path):
    path = tmp_path / "savepoints.json"
    SP.write(path, [_sp(label="one"), _sp(label="two", sha="deadbeef")])
    back = SP.read(path)
    assert [s.label for s in back] == ["one", "two"]
    assert back[1].git_sha == "deadbeef"


def test_s5_the_same_label_supersedes_rather_than_duplicating(tmp_path):
    """Two points with one name is a name that does not point."""
    path = tmp_path / "savepoints.json"
    SP.write(path, [_sp(label="x", sha="aaa")])
    SP.append(path, _sp(label="x", sha="bbb"))
    back = SP.read(path)
    assert len(back) == 1 and back[0].git_sha == "bbb"


def test_s6_a_savepoint_never_crosses_worlds(tmp_path):
    """alpha's savepoint restored into beta would be the cross-world write the whole arc
    exists to prevent."""
    ok, why = SP.can_restore(_sp(world="alpha"), snapshot_exists=lambda n: True,
                             tree_dirty=0, into_world="beta")
    assert ok is False
    assert "alpha" in why and "beta" in why
