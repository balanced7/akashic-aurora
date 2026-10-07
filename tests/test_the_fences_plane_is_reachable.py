"""RED pins: the house's 21 sealed reconciliations are in no searchable corpus.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

DANIEL, going to sleep 2026-10-07: "See if you can't continue working on making our best knowledge
reach us when we need it or at least be easy to find."

CONTRACT B'S ACCEPTANCE TEST WAS RUN, AND IT FAILED. `fences/filing-schema/reconciliation.md` §6
recorded the test and recorded that nobody had run it: *"can a seat that has never seen this tree
retrieve the Wave-0 build spec by what it is about, in one command? Nobody answered that, so B carries
no evidence either way."* The verdict "unproven, do not build" was an absence, not a measurement.

It was run twice on 2026-10-07, by two independent cold readers, different phrasings, neither knowing
of the other, neither told it was a test, neither given the filename, the folder, or the words "fence"
or "reconciliation" -- only what the document is ABOUT, which is the test's own wording. I could not be
the reader: I know where the file is, so any attempt of mine measures my memory, not the index.

Target: ``fences/context-system/reconciliation.md``, H1 *"Reconciliation -- context-system (the Wave 0
build spec)"*.

MEASURED, both readers, independently:

  * Reader A: **15** `agent_cli` invocations to a printed path. Reader B: **11**.
  * The document was **never a result row** for either of them. Both found it only because an
    unrelated note happened to QUOTE its path -- A at invocation 5, B at 6.
  * Both briefly settled on the same wrong answer, `docs/context-system.md`.

THE ROOT CAUSE, named independently by both: **the `fences/` plane is in no searchable corpus.**

  * `lookback`'s LAYERS are `docs, charters, research, notes, promoted, chapters, git`. No `fences`.
  * `knowledge-map` walks lessons, notes and docs. No `fences`.

Those are the two doors that look purpose-built for "find the document that decided X", and a
reconciliation is the most authoritative artifact this house produces -- it is where a contested
question is SETTLED. It is the one class of document no retrieval verb indexes.

AND IT HAD ALREADY BEEN MEASURED. Reader A noticed a row surfaced by its own `knowledge-map` call --
`docs/library/report/20261001_first-pass-easy-vs-thorough` -- independently reporting "other-plane reach
0/62" and "`eye find` returned 0 hits". The gap was quantified before, written down, and nothing
followed. A finding reaching the corpus is not the same as a finding reaching a fix.

THE PRECEDENT THIS FOLLOWS, which is why the fix shape is not in doubt. `_charter_items` exists for
exactly this reason and its docstring says so: *"Intent lived only in charters/ and was reachable ONLY
by already knowing the path, which a newcomer by definition does not."* It was given its OWN layer
rather than folded into `docs`, deliberately, because *"folding it into `docs` would leave it competing
with a far more numerous corpus for the same PER_LAYER slots -- present in the code, still absent in the
answers."* Both halves of that reasoning apply unchanged to `fences/`.

Full evidence, both reports verbatim: `research/reviewed/contract-b-cold-read-test-2026-10-07.md`.

Run::

    py -m pytest tests/test_the_fences_plane_is_reachable.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: The document the cold-read test was run against. Named here because a pin about retrievability
#: must say WHAT it expects to retrieve.
TARGET = "fences/context-system/reconciliation.md"


def _fence_reconciliations() -> list:
    return sorted(p for p in (ROOT / "fences").glob("*/reconciliation.md") if p.is_file())


# ------------------------------------------------------------------ the defect
def test_lookback_has_a_fences_layer():
    """THE PIN. `lookback` is the verb built for 'the strategic WHY' and cannot see where the WHYs
    are written down."""
    from core.recall.lookback import LAYERS
    names = [n for n, _fn in LAYERS]
    assert "fences" in names, (
        "lookback's layers are %r -- there is no `fences` layer, so the house's %d sealed "
        "reconciliations cannot appear as result rows in the one verb built to answer "
        "'why did we decide X'. Both cold readers reached the Wave 0 build spec only because a "
        "note happened to quote its path." % (names, len(_fence_reconciliations())))


def test_the_fences_layer_actually_yields_the_reconciliations():
    """A registered layer that returns nothing is the same silence with a new name.

    Asserts the layer FUNCTION produces rows, and that the target is among them -- behaviour, not
    registration. A layer present in LAYERS and empty at runtime would satisfy the pin above and
    change nothing about what a reader can find.
    """
    from core.recall.lookback import LAYERS
    fn = dict(LAYERS).get("fences")
    if fn is None:
        pytest.fail("no fences layer to exercise (see test_lookback_has_a_fences_layer)")
    items = fn()
    assert items, "the fences layer returned 0 items"
    sources = {i.get("source") for i in items}
    assert TARGET in sources, (
        "the fences layer yielded %d item(s) but not %s. Sample: %r"
        % (len(items), TARGET, sorted(sources)[:5]))


def test_a_cold_question_about_the_wave_0_spec_reaches_it():
    """THE PIN THAT MATTERS, and the one phrased as Contract B phrased it: by what it is ABOUT.

    The question deliberately uses none of the document's addressing vocabulary -- not its filename,
    not "fence", not "reconciliation", not "Wave 0" as a filing term. If the retrieval system needs
    the reader to already know how the thing is filed, it is an index of answers for people who have
    them.

    AT THE DEFAULT DEPTH, and that correction is the point. The first version of this pin passed
    ``per_layer=10`` and went green, which measured a depth no caller uses: ``PER_LAYER = 3``. A fresh
    cold reader run against that supposedly-fixed state then MISSED the document -- `lookback` returned
    the dated ADDENDUM instead, and the reader said plainly "if I had stopped there I would have
    reported the addendum". My pin had bought itself a pass by asking for seven more slots than the
    verb hands out. A pin must use the production call shape; a generous parameter is the same evasion
    as a generous assertion.
    """
    from core.recall.lookback import lookback
    hits = lookback("what did we agree to build first for the context system and what waits")
    sources = [h.get("source") for h in hits]
    assert TARGET in sources, (
        "the Wave 0 build spec is not reachable by a question about what it is about. %d hit(s) "
        "came back and the authoritative document was not among them: %r"
        % (len(hits), sources[:12]))


def test_the_exact_question_a_cold_reader_actually_asked():
    """THE MEASURED PIN, and the one I did not think to write.

    After the fences layer landed, a fresh cold reader was sent in to verify the fix. `knowledge-map`
    found the document as its own row at joint-top relevance (0.704) in 4 commands, down from 11 and
    15. But `lookback` MISSED it, and the reader's own words were: *"it ranked the dated addendum to
    the target above the target and omitted the target entirely. If I had stopped there I would have
    reported the addendum."*

    My own pin above passed at the same moment, because my phrasing happens to contain the words
    "context system" -- which is the ROUND NAME this layer prepends to every row. The reader described
    the same thing as "an agent's working context" and "round one versus later rounds" and got the
    addendum. So the pin I wrote measured my luck at guessing my own index's vocabulary.

    This query is the reader's, verbatim. It is the acceptance test; the other one is a warm-up.

    WHY THE ADDENDUM WINS AND WHY THAT IS A BUG, not a tuning problem: an addendum is SHORTER and more
    focused than the 32,008-byte ruling it annotates, so it scores higher on relevance density while
    being, by construction, a modifier of the answer rather than the answer. The house's own rule is
    that sealed text is never edited and a round that needs revising gets a dated addendum beside it --
    which means the ruling IS reconciliation-plus-its-addenda, one document in several files. Indexing
    them as rivals invents a competition the house does not have.
    """
    from core.recall.lookback import lookback
    hits = lookback("how is an agent's working context assembled, and what was decided for "
                    "round one versus later rounds")
    sources = [h.get("source") for h in hits]
    fences = [s for s in sources if s and s.startswith("fences/")]
    assert TARGET in sources, (
        "the reader's own phrasing does not reach the ruling. fence rows returned: %r "
        "(all %d hits: %r)" % (fences, len(sources), sources[:12]))


def test_an_addendum_never_outranks_the_ruling_it_annotates():
    """The rule, stated as a rule so it cannot regress into a tuning accident.

    A dated addendum folds a later round into a sealed one. It is never the authority on its own, and
    a reader handed the addendum without the ruling has been given a footnote and told it is the law.
    """
    from core.recall.lookback import LAYERS
    fn = dict(LAYERS).get("fences")
    if fn is None:
        pytest.fail("no fences layer")
    sources = [i.get("source", "") for i in fn()]
    stray = [s for s in sources if "addendum" in s.rsplit("/", 1)[-1]]
    assert not stray, (
        "addenda are indexed as rows of their own and so compete with the rulings they annotate: %r. "
        "They belong folded into their reconciliation's row, which is what the house's "
        "never-edit-sealed-text rule already means." % stray[:5])


def test_fence_status_prints_a_path():
    """Both readers hit this independently: the fence door holds the authority and withholds the
    address. `fence status context-system` reports `reconciliation SEALED by claude`, `closed: True`
    and the round's question -- and no filename, so a confirmed document still cannot be opened
    without crossing to a different verb."""
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "agent_cli.py"),
                        "fence", "status", "context-system"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=180)
    out = r.stdout + r.stderr
    if "reconciliation" not in out.lower():
        pytest.skip("fence status does not mention the reconciliation slot on this checkout")
    assert ("fences/" in out or "fences\\" in out), (
        "fence status names the reconciliation as SEALED and never says where it is. Output:\n%s"
        % out[-700:])


# ------------------------------------------------------------------ the plane itself
def test_every_sealed_reconciliation_is_in_the_corpus():
    """REGRESSION GUARD in the units that matter: not "a fences layer exists" but "every ruling is
    reachable". A layer that indexes one directory and misses twenty is the same defect at a smaller
    scale."""
    from core.recall.lookback import LAYERS
    fn = dict(LAYERS).get("fences")
    if fn is None:
        pytest.fail("no fences layer (see test_lookback_has_a_fences_layer)")
    have = {i.get("source") for i in fn()}
    want = {str(p.relative_to(ROOT)).replace("\\", "/") for p in _fence_reconciliations()}
    missing = sorted(want - have)
    assert not missing, (
        "%d of %d sealed reconciliation(s) are absent from the corpus: %r"
        % (len(missing), len(want), missing[:6]))


# ------------------------------------------------------------------ ratchets
def test_docs_stays_the_first_layer():
    """RATCHET, and a constraint the fix must not trip. The comment at the LAYERS declaration says
    lookback's query counter bumps on LAYERS[0][0], and
    tests/test_charters_in_lookback_corpus.py::test_p3 already pins it. A new layer must be
    registered AFTER docs, exactly as `charters` was."""
    from core.recall.lookback import LAYERS
    assert LAYERS[0][0] == "docs", (
        "LAYERS[0] is %r -- the query counter keys off it; a new layer goes after docs, never "
        "before" % (LAYERS[0][0],))


def test_the_existing_layers_all_survive():
    """RATCHET. Adding a layer must not displace one. These seven were the corpus on 2026-10-07."""
    from core.recall.lookback import LAYERS
    names = [n for n, _fn in LAYERS]
    for expected in ("docs", "charters", "research", "notes", "promoted", "chapters", "git"):
        assert expected in names, "the %r layer disappeared: %r" % (expected, names)


def test_the_charters_precedent_still_holds():
    """RATCHET on the precedent this fix copies. If charters stopped yielding, the reasoning cited in
    this file's docstring would be describing something that no longer works."""
    from core.recall.lookback import LAYERS
    fn = dict(LAYERS).get("charters")
    if fn is None:
        pytest.skip("no charters layer on this checkout")
    assert fn(), "the charters layer yields nothing -- the precedent for this fix has regressed"
