"""RED pins: the eye drops 89 of 90 workflow journals, then reports a healthy corpus.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

DANIEL, going to sleep 2026-10-07: "See if you can't continue working on making our best knowledge
reach us when we need it or at least be easy to find. Perhaps we need to run some kind of index on
our transcripts and atoms so that we know what we have and where its supposed to live."

The answer turned out not to be a new index. It is a whole plane the index we already have was
discarding without saying so.

WHAT THE PLANE IS. A workflow run writes
``.claude/projects/<proj>/<session>/subagents/workflows/wf_<id>/journal.jsonl`` -- ``started`` and
``result`` records, where ``result`` carries the agent's actual return value. The workflow-authoring
reference points at this file by name as the place to look when a fan-out returns something
unexpected. It is the only record of what each fanned-out agent CONCLUDED, as opposed to what it
said on the way there.

MEASURED 2026-10-07, all [CERTAIN] from my own commands:

  * **90 journals**, 13.30 MB, holding **870 agent results** with **0 null/empty**, 13.12 MB of
    returned verdict text, spanning 2026-08-01 -> 2026-10-07. It is still growing.
  * ``session_id_for()`` over those 90 paths returns **1 distinct id**: the string ``"journal"``,
    ninety times. The parent directory name gives **90 distinct of 90**.
  * ``_take()`` dedups by that id against a ``seen`` set, so **89 files are discarded before ingest
    ever opens them** -- no counter moves, no line is printed.
  * ``eye ingest`` reports ``1515/1515 files | 55,470 events | unparsed 0`` and
    ``corpus: live 1367 ... = 1515 file(s)``. Both numbers count what SURVIVED dedup, so a plane
    deleted at enumeration is indistinguishable from a plane that does not exist.
  * The single survivor is in ``ingest_state`` with ``lines=26`` and contributed
    ``select count(*) from events where session='journal'`` -> **0**. A journal record is
    ``{type, key, agentId, result}``, not the ``user``/``assistant`` shape the parser reads, so it
    yields nothing -- and ``unparsed 0`` cannot tell "parsed fine, produced nothing" from "empty".

  So **0 of 870 agent verdicts are searchable**, and every instrument involved says clean.

THIS EXACT DEFECT IS ALREADY DOCUMENTED IN THE FUNCTION THAT HAS IT. ``session_id_for``'s docstring
(core/eye/index.py:162) describes T406 verbatim:

    "silently wrong for DSH, where all 25 transcripts are named `session.jsonl.zstd` and `.stem` is
    the constant 'session.jsonl' for every one of them. The damage of getting this wrong is not a
    missing session, it is LOST EVENTS."

And ``_take``'s own comment adds: "the proxy would have discarded 24 sessions as duplicates of each
other -- silently, and reported as a healthy corpus." That is a precise description of what is
happening to the journals right now.

WHY IT RECURRED, which is the part worth fixing. The repair was
``_GENERIC_TRANSCRIPT_STEMS = {"session", "transcript", "conversation", "chat"}`` -- a hand-enumerated
list of four names someone had already been bitten by. ``"journal"`` is not among them, so the fix
covered the instance and not the class. The house has a standing finding about exactly this shape,
in core/trust/private_plane.py: "MARKERS ARE DERIVED, NEVER DECLARED ... A hand-maintained denylist
rots the moment someone adds a file." Genericness is derivable: a stem claimed by more than one file
in more than one directory IS generic, and the corpus already knows which those are at the moment it
enumerates them.

THE SEVENTH TODAY, one family. ``find --sort`` re-sorted in Python after asking es.exe for an order.
A pin of mine compared only the YEAR when every row was 2026. ``--verify`` compared two recorded
shas and hashed nothing. The zone-README write could not tell its own output from a human's. A leak
guard reported a clean sweep because its import failed. Two pins in that guard's own file matched the
docstring instead of the code. And now a corpus report that counts survivors and calls it coverage.
Every one reports green by comparing a thing to itself, or by counting only what it managed to keep.

Run::

    py -m pytest tests/test_the_eye_does_not_silently_discard_a_plane.py -q
"""
from __future__ import annotations

import ast
import collections
import glob
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INDEX_PY = ROOT / "core" / "eye" / "index.py"
#: Where a workflow run writes its orchestration record. Not repo-relative: this plane lives in the
#: harness's own tree, which is part of why nothing in the repo was watching it.
JOURNAL_GLOB = str(Path.home() / ".claude" / "projects" / "*" / "*" / "subagents" / "workflows"
                   / "*" / "journal.jsonl")


def _journals() -> list:
    return sorted(glob.glob(JOURNAL_GLOB))


def _code_of(func_name: str) -> str:
    """The function's executable source, docstring dropped.

    The lesson from tonight's other pin file, applied up front: ``session_id_for``'s docstring
    DESCRIBES this very defect, so any pin that greps raw source matches the account of the bug
    instead of the bug. Parsing is the only way to ask about behaviour.
    """
    tree = ast.parse(INDEX_PY.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            return "\n".join(ast.unparse(s) for s in body)
    raise AssertionError("no function named %r in %s" % (func_name, INDEX_PY))


# ------------------------------------------------------------------ the defect
def test_session_ids_do_not_collide_across_the_workflow_journals():
    """THE PIN. 90 files, 1 id. Every colliding pair is a file the dedup throws away.

    This is measured against the live plane rather than a fixture, because the defect is precisely
    that the live plane has a shape no fixture had.
    """
    from core.eye.index import session_id_for
    paths = _journals()
    if not paths:
        pytest.skip("no workflow journals on this box (measured 90 on 2026-10-07)")
    ids = collections.Counter(session_id_for(p) for p in paths)
    worst, n = ids.most_common(1)[0]
    assert len(ids) == len(paths), (
        "%d journal(s) collapse to %d distinct session id(s) -- %r is claimed by %d files, so "
        "_take()'s `seen` dedup discards %d of them before ingest opens any. The parent directory "
        "name gives %d distinct ids for the same files."
        % (len(paths), len(ids), worst, n, len(paths) - len(ids),
           len({os.path.basename(os.path.dirname(p)) for p in paths})))


def test_genericness_is_derived_not_a_hand_enumerated_list():
    """THE PIN THAT MATTERS, because it is the difference between fixing the instance and fixing
    the class.

    ``_GENERIC_TRANSCRIPT_STEMS = {"session","transcript","conversation","chat"}`` is four names
    someone was already bitten by. It cannot know about the fifth. A stem claimed by several files
    in several directories is generic BY OBSERVATION, and the enumeration already holds the file
    list when it needs the answer.
    """
    code = _code_of("session_id_for")
    literal_set = ("_GENERIC_TRANSCRIPT_STEMS" in code
                   and "derive" not in code.lower() and "collide" not in code.lower())
    assert not literal_set, (
        "session_id_for decides genericness by membership in a hand-maintained literal set. "
        "'journal' is not in it, which is why 89 of 90 workflow journals were discarded silently. "
        "core/trust/private_plane.py states the rule this violates: markers are DERIVED, NEVER "
        "DECLARED -- a hand-maintained denylist rots the moment someone adds a file.")


def test_the_corpus_report_states_how_many_files_it_DROPPED():
    """A coverage contract that counts survivors is not a coverage contract.

    ``eye ingest`` prints ``1515/1515 files`` and ``corpus: live 1367 ... = 1515 file(s)``. Both are
    post-dedup. 89 files were found, matched the glob, and were deleted from the list, and no number
    in the report moved. The drop must be a figure the reader sees, which is the same discipline
    delta --disk already follows (roots scanned/skipped, files examined, touch.drops()).

    THIS PIN WAS VACUOUS ON ITS FIRST DRAFT, for the fourth time tonight and by the same move. It
    searched the source for the token ``dedup`` -- and ``corpus_coverage()`` returns
    ``'dedup': 'by session id; precedence live > archive > rescued > dsh > seat'``, a string that
    DESCRIBES the policy and counts nothing. The pin passed by reading a label. So it now CALLS the
    function and demands a number, which is the only form of this question that cannot be answered
    by prose.
    """
    from core.eye.index import corpus_coverage
    cov = corpus_coverage()
    numeric = {k: v for k, v in cov.items() if isinstance(v, int)}
    dropped = [k for k in numeric
               if any(t in k.lower() for t in ("drop", "shadow", "collid", "discard", "found"))]
    assert dropped, (
        "corpus_coverage() returns no INTEGER count of files removed by dedup -- only %r and the "
        "descriptive string %r, which names the policy and measures nothing. A plane deleted at "
        "enumeration therefore reads exactly like a plane that does not exist. Found-vs-taken is "
        "the honest denominator." % (sorted(numeric), cov.get("dedup")))
    total_dropped = sum(cov[k] for k in dropped)
    assert total_dropped >= 89, (
        "the drop count reports %d, but 89 workflow journals collapse into one session id on this "
        "box alone -- so the number exists and is not measuring the collision."
        % total_dropped)


def test_a_file_recorded_as_ingested_that_yielded_nothing_is_reported():
    """``unparsed 0`` is the wrong instrument for this failure.

    The one journal that survived dedup sits in ``ingest_state`` with ``lines=26`` and contributed
    0 rows to ``events``, because a journal record is ``{type, key, agentId, result}`` and the
    parser reads ``user``/``assistant``. It did not fail to parse. It parsed and meant nothing to
    the reader, and the report has no word for that -- so a file format the eye cannot read is
    counted among its successes.
    """
    src = INDEX_PY.read_text(encoding="utf-8", errors="replace")
    i = src.index("def ingest")
    block = src[i:i + 9000].lower()
    for token in ("yielded", "no_events", "zero_event", "empty_yield", "barren", "silent_file"):
        if token in block:
            break
    else:
        pytest.fail(
            "ingest() counts files and unparsed lines but never notices a file that parsed "
            "cleanly and produced no events. Measured: journal.jsonl, 26 lines recorded in "
            "ingest_state, 0 rows in events, reported inside 'unparsed 0'.")


# ------------------------------------------------------------------ the plane itself
def test_every_workflow_journal_is_reachable_by_a_distinct_address():
    """REGRESSION GUARD on the loss, stated in its own units: 870 agent verdicts over 90 runs.

    Phrased as reachability rather than as a row count, so it holds whichever way the fix routes
    them -- indexed as events, or given their own plane -- and fails only if they are once again
    addressable only as a single file called "journal".
    """
    from core.eye.index import session_id_for
    paths = _journals()
    if not paths:
        pytest.skip("no workflow journals on this box (measured 90 on 2026-10-07)")
    ids = {session_id_for(p) for p in paths}
    assert len(ids) >= len(paths), (
        "only %d of %d workflow journals have a distinct address. 870 agent results, 13.12 MB of "
        "returned verdict text, 0 of them searchable." % (len(ids), len(paths)))


# ------------------------------------------------------------------ ratchets: keep what works
def test_the_dsh_plane_still_resolves_to_one_address_per_session():
    """RATCHET. T406's fix is real and must survive: DSH names all 25 of its transcripts
    `session.jsonl.zstd`, and resolving those by stem would collapse them to one.

    THIS PIN'S FIRST DRAFT ASSERTED A FIXTURE AND THE FIXTURE WAS THE WRONG SHAPE. It built
    `/tmp/dsh-run-7/session.jsonl` and demanded the directory be used -- but every real DSH session
    directory is a UUID (`session-7968a54a-40ff-...`, `1c6f4c4a-34da-...`), and `dsh-run-7` is a name
    I invented. When the fix landed, the pin failed and the live plane was fine: I had pinned my
    guess about the plane instead of the plane. Measuring the 25 real files is both stronger and
    cheaper, and it cannot drift from what DSH actually writes.
    """
    from core.eye.index import session_id_for
    files = sorted(glob.glob(str(Path.home() / ".dsh" / "sessions" / "**" / "session.jsonl*"),
                             recursive=True))
    if not files:
        pytest.skip("no DSH plane on this box (measured 25 transcripts on 2026-10-07)")
    ids = {session_id_for(p) for p in files}
    assert len(ids) == len(files), (
        "%d DSH transcripts collapse to %d address(es). They are all named session.jsonl.zstd, so "
        "resolving them by stem makes line 12 of one session and line 12 of another the same row."
        % (len(files), len(ids)))


def test_a_readable_but_unique_stem_is_not_treated_as_generic():
    """RATCHET, added because the fix's FIRST version broke this and tests/test_t278_s0_eye_indexer.py
    caught it.

    Asking only "is the stem an identifier?" and using the directory otherwise collapsed the
    indexer fixture's `corpus/session_alpha.jsonl` and `corpus/session_beta.jsonl` onto `corpus`,
    merging two distinct sessions and taking events_total from 11 to 7. A readable name can still be
    a unique one, and a rule that cannot tell those apart loses sessions the eye already holds --
    strictly worse than the plane it was fixing. Guarded here so the three-step order (stem-is-id ->
    parent-is-id -> stem) cannot quietly collapse back to two steps.
    """
    from core.eye.index import session_id_for
    a = session_id_for(Path("/tmp/corpus/session_alpha.jsonl"))
    b = session_id_for(Path("/tmp/corpus/session_beta.jsonl"))
    assert a == "session_alpha" and b == "session_beta" and a != b, (
        "two distinct readable session names resolved to %r and %r -- a non-id directory must not "
        "become the address, or distinct sessions merge" % (a, b))


def test_claude_code_uuid_stems_are_unchanged():
    """RATCHET, and the constraint any fix has to respect. event_id is "<session>:<line>", so
    changing the id of an already-indexed session re-keys 55,470 rows. A UUID stem names its own
    session and must keep resolving to itself."""
    from core.eye.index import session_id_for
    uuid = "428ba6c4-2217-4008-a2be-ecd9901cc3b2"
    got = session_id_for(Path("/c/Users/L5/.claude/projects/E--/%s.jsonl" % uuid))
    assert got == uuid, (
        "session_id_for changed the address of a normal Claude Code transcript (%r). The 55,470 "
        "rows already indexed are keyed on these ids." % got)


def test_the_compressed_suffix_handling_survives():
    """RATCHET. DSH's files end `.jsonl.zstd`; the suffix strip is what lets the stem be recognised
    as a non-identifier at all. Uses a UUID directory because that is what DSH actually writes --
    the lesson from the pin above."""
    from core.eye.index import session_id_for
    got = session_id_for(Path("/tmp/session-7968a54a-40ff-4256-90e8-6173d40aa338/session.jsonl.zstd"))
    assert got == "session-7968a54a-40ff-4256-90e8-6173d40aa338", (
        "compressed-suffix handling regressed: got %r" % got)


def test_no_existing_address_moves():
    """THE MIGRATION RATCHET, and the constraint the fence named as non-negotiable.

    `event_id = "<session>:<line>"` over 55,470 rows. If a fix changes the address of a session that
    already has rows, `INSERT OR IGNORE` re-files its events under a new key and says nothing. This
    compares every file in the corpus against the OLD rule -- reimplemented here rather than
    imported, so deleting the old code cannot make the pin vacuous -- and requires that no file
    which already has rows resolves differently. Measured 0 of 1,997 when the fix landed.
    """
    import sqlite3
    from core.eye.index import session_id_for, _corpus_roots
    db = ROOT / "state" / "eye" / "eye.db"
    if not db.is_file():
        pytest.skip("no eye.db on this box")
    rows, drops = _corpus_roots(with_drops=True)
    files = [Path(d["path"]) for d in drops] + [p for _l, _b, f in rows for p in f]
    con = sqlite3.connect(str(db))
    try:
        known = {r[0] for r in con.execute("SELECT DISTINCT session FROM events")}
    finally:
        con.close()

    legacy_generic = {"session", "transcript", "conversation", "chat"}

    def old_rule(p: Path) -> str:
        name = p.name
        for suf in (".zstd", ".zst"):
            if name.lower().endswith(suf):
                name = name[: -len(suf)]
                break
        stem = name[:-6] if name.lower().endswith(".jsonl") else Path(name).stem
        return (p.parent.name or stem) if stem.lower() in legacy_generic else stem

    moved = [(old_rule(p), session_id_for(p)) for p in files
             if old_rule(p) in known and session_id_for(p) != old_rule(p)]
    assert not moved, (
        "%d file(s) with rows already in `events` would resolve to a NEW address, re-keying their "
        "history silently. First few: %r" % (len(moved), moved[:5]))
