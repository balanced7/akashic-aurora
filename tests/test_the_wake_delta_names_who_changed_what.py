"""RED pins: the planes and the disk disagree, and nothing in the house reconciles them.

PRE-REGISTRATION (M3). RED at this commit; the organ follows separately.

DANIEL, 2026-10-07, after the `find` sort fix landed: "a quick heads up look after wake to see
what files changed and we could possibly expand it to show who changed it if it was an agent."

PRIOR ART, AND THIS IS NOT A SECOND COPY OF IT. `py agent_cli.py delta` (T052, the delta door)
already answers "what moved since I was last here", and it is good: a per-agent seen mark over
FOUR positions -- git_commit, ledger_seq, notes_head, promoted_id -- with a mark-lag contract so a
crash redelivers the gap. That verb owns the question on the AURORA PLANES and this organ must not
re-answer it. touch.py states the hazard directly: "One fact on the spine twice under two names
would be a second writer for one transition, which is the rival assembler both maps warn about."

WHAT T052 STRUCTURALLY CANNOT SEE, which is the entire gap this organ is for:

  1. UNCOMMITTED WORK. Its position is `git_commit`, so anything written and not yet committed is
     invisible. Right now that is ~60 modified tracked files belonging to other seats, plus 300+
     untracked paths.
  2. ANYTHING OUTSIDE THE REPO. agent/harness/delta.py pins REPO to the repo directory. Today's
     artifacts landed in three trees: the repo, the PRIVATE Desktop/!Documents tree (which must
     never be committed), and the volatile TEMP/claude tree.
  3. PER-FILE ATTRIBUTION. Git groups by author and every seat here commits as `balanced7`, so
     "who changed this" is unanswerable from the plane T052 reads.

So this organ is a RECONCILIATION -- the drift between what the planes believe happened and what
the disk shows -- not a rival delta. The door therefore belongs on the EXISTING verb as a plane
(`delta --disk`) rather than under a new name. That is pinned below, and it is the one design
choice here that is Daniel's to overrule: if he prefers a separate verb, that pin moves and
nothing else does.

WHY NOW AND NOT BEFORE. `find` is backed by the Everything index and answers in ~0.64 s where a
tree walk takes 10.4 s and issues 172,070 stat() calls -- but until ddc0e734 every `--sort` key and
every `--preset` was silently inert, so "what changed, newest first" had no fast answer anywhere in
the house. Date ordering is the hinge: a delta is a question about TIME, and the only instrument
that could answer it across the machine was returning results ordered by path length.

WHAT IS ACTUALLY MISSING, measured 2026-10-07:

  * BOOT TELLS A SEAT NOTHING ABOUT DISK. `boot` surfaces lessons, the handoff, the roster, mail
    and the chronicle. It does not say which files moved. Today two Vandor seats (claude#428ba6c4
    and claude#81efa6f6) edited one tree in one evening and each had to reconstruct the other's
    work from `git log` after the fact -- one of them thanked the other for a commit it had
    authored itself, and objected to a sentence in its own wish. Attribution by archaeology.

  * THE WORK IS NOT ALL IN THE REPO. Today's artifacts landed in at least three trees:
    E:\\AI-Setup (committed), C:\\Users\\L5\\Desktop\\!Documents (private, and NEVER to be
    committed), and %TEMP%\\claude (volatile). A census of the last 24 h found **167
    authored-shaped files** (.md/.py/.txt/.json/.jsonl/.ps1/.sh) sitting in %TEMP%\\claude alone,
    including `ccna_v2_raw.txt` -- the fetched Cisco blueprint that a load-bearing claim in
    Daniel's career research rests on, held nowhere else.

  * THE CORPUS ALREADY CITES PATHS THAT ARE GONE. 302 citations to volatile paths across 268
    committed markdown docs. Four were confirmed dead by direct check -- `critic_stats.py`,
    `quant.mjs`, `tracker.mjs`, `choices-straight-portrait.jpg`, cited by three
    research/in-flight documents from mid-September, whose scratchpad has since been cleared.
    (The *count* of broken citations is NOT established: a crude regex produced junk captures and
    is not reported as a measurement. Direction certain, magnitude not -- the same discipline the
    affordance-layer addendum cost to learn.)

TWO FACTS THE ORGAN MUST NOT PRETEND AWAY, both measured today:

  1. THE ATTRIBUTION SOURCE IS LOSSY AND SAYS SO. `core/events/touch.py` is the right join -- it
     carries `(session_id, agent_id, action, key)` and its own docstring explains why it exists:
     of 6,918 records in `events:raw`, only 89 carried a session_id. But `touch.drops()` reads
     **214** right now. Its Law 2 is already written: "a swallowed failure that is not COUNTED is
     just a lie with better manners." A delta built on it inherits that and must surface it.

  2. THE ROOT REGISTRY IS 73% DEBRIS. `touch.default_roots()` returns **63** worktrees. **46** of
     them are `season_dryrun_*` / `probe_*` / `t187_*` temp shadows from test runs. All 63 still
     exist on disk, so a naive sweep does not fail -- it quietly scans 46 trees of test garbage
     and reports the result as the house's activity.

Run::

    py -m pytest tests/test_the_wake_delta_names_who_changed_what.py -q
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLI = str(ROOT / "agent_cli.py")

try:                                        # deliberately NOT importorskip: the module's absence
    from core.provenance import delta       # is the first RED pin, and a skipped pin reads green
    _IMPORT_ERROR = None                    # forever. (Written as importorskip on the first pass,
except Exception as exc:                    # which skipped the WHOLE file silently -- the third
    delta = None                            # time today this class bit, and the second time it
    _IMPORT_ERROR = exc                     # bit me after I had written the warning against it.)


@pytest.fixture(autouse=True)
def _require_the_module():
    if delta is None:
        pytest.fail("core/provenance/delta.py does not import: %r" % (_IMPORT_ERROR,))


def _run(*args, timeout=120):
    return subprocess.run([sys.executable, "-X", "utf8", CLI, *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=str(ROOT), timeout=timeout, stdin=subprocess.DEVNULL)


# ------------------------------------------------------------------ the organ and its door
def test_the_module_exists():
    """FAIL, never skip, while the organ is unbuilt -- a pre-registered pin that skips when its
    subject is missing is indistinguishable from a passing one in CI output."""
    import importlib
    m = importlib.import_module("core.provenance.delta")
    for fn in ("since", "classify_tree", "attribute"):
        assert hasattr(m, fn), f"core.provenance.delta has no {fn}()"


def test_the_door_is_a_plane_on_the_EXISTING_delta_verb():
    """NOT A RIVAL ASSEMBLER. T052's `delta` already owns "what moved since I was here"; this is
    the same question on a plane it cannot see, so it belongs on that door rather than under a
    second name. This is the one design choice here that is Daniel's to overrule -- if he prefers
    a separate verb, only this pin moves."""
    r = _run("delta", "--help")
    out = r.stdout + r.stderr
    assert "--disk" in out, (
        "`delta` has no --disk plane. The filesystem gap is the same continuity question T052 "
        "answers for git/ledger/notes/promoted, and splitting it under a new verb mints a second "
        "writer for one transition -- the rival assembler touch.py warns about.")


def test_it_does_not_re_render_what_T052_already_reports():
    """The reconciliation reports the GAP, not the overlap. Re-listing committed git history would
    duplicate the delta door and double the reader's cost for nothing."""
    src = inspect.getsource(delta)
    assert "render_full" not in src, (
        "the disk plane calls T052's renderer -- that is the rival-assembler shape")


# ------------------------------------------------------------------ it must use the index
def test_the_sweep_uses_the_everything_index_not_a_tree_walk():
    """THE PERFORMANCE PIN, and the reason this organ is newly possible. Measured 2026-10-06 on
    this machine: `find` via the Everything index answers in 0.64 s; the equivalent GNU tree walk
    took 10.4 s and issued 172,070 stat() calls to return six rows, 8.0 s of it in the kernel.

    A delta that walks the filesystem is a delta nobody will run at wake, and an organ nobody runs
    is the `capability_without_a_door` shape wearing a performance costume."""
    src = inspect.getsource(delta)
    assert ("everything" in src.lower() or "resolve_es" in src), (
        "the delta does not reach for the Everything index")
    for walker in ("os.walk(", "Path.rglob(", ".rglob(", "glob.glob("):
        assert walker not in src, (
            f"the delta uses {walker} -- a tree walk. The index exists precisely so a wake-time "
            f"question does not cost 172,070 stat() calls.")


def test_it_asks_find_for_a_date_order_rather_than_sorting_afterwards():
    """The fix that made this buildable is `--sort`/`--preset` actually reaching es.exe. Re-sorting
    in Python would re-create the defect ddc0e734 removed -- and would also discard the index's
    ordering, which is the only part that is free."""
    src = inspect.getsource(delta)
    assert ("date-modified" in src or "recent" in src), (
        "the delta never names a date order, so it is relying on whatever order it happens to get")


# ------------------------------------------------------------------ the three trees
def test_every_change_is_classified_by_tree():
    """REPO / PRIVATE / VOLATILE are not cosmetic labels -- they are three different fates.
    Repo work is durable and reviewable. Private work is durable and MUST NEVER be committed.
    Volatile work disappears on a reboot or a temp sweep, and is the only class that is an alarm.
    """
    for p, expect in (
        (r"E:\AI-Setup\core\tools\everything.py", "repo"),
        (r"C:\Users\L5\Desktop\!Documents\Tax Documents\CATCH-UP-TRACKER.md", "private"),
        (r"C:\Users\L5\AppData\Local\Temp\claude\E--\x\scratchpad\ccna_v2_raw.txt", "volatile"),
        (r"X:\wt-baseline-682c5cf8\scripts\x.py", "volatile"),
    ):
        got = delta.classify_tree(p)
        assert got == expect, f"{p} classified {got!r}, expected {expect!r}"


def test_volatile_authored_work_is_the_headline_not_a_footnote():
    """The whole point. 167 authored-shaped files sat in %TEMP%\\claude in a single day, one of
    them the only copy of a fetched primary source a committed conclusion rests on. A delta that
    lists volatile changes alongside everything else buries the only class that is losable."""
    src = inspect.getsource(delta)
    assert "volatile" in src.lower(), "the delta has no notion of volatile storage"


def test_the_private_tree_never_leaks_into_a_repo_bound_artifact():
    """STANDING CONSTRAINT, not a preference: the job-hunt folder and the tax documents are
    private and must never reach the public repo. The delta READS that tree to report on it and
    must never write its contents anywhere under the repo."""
    src = inspect.getsource(delta)
    assert "private" in src.lower(), "the delta cannot distinguish the private tree at all"
    sig = inspect.signature(delta.since)
    assert "roots" in sig.parameters or "scopes" in sig.parameters, (
        "since() takes no explicit roots, so a caller cannot bound what it reads")


# ------------------------------------------------------------------ attribution, honestly
def test_attribution_is_typed_and_unknown_is_a_value():
    """THE PIN DANIEL ASKED FOR, with the honesty clause attached. 'Who changed this' has three
    answers, not two: a named seat, nobody-we-can-see, and NOT-ATTRIBUTABLE. Collapsing the last
    two is how a file written by a human reads as a file written by an agent.

    `touch.py` already holds this discipline for its own records -- an unattributed touch is
    emitted but 'must not be indistinguishable from an attributed one' -- and the delta inherits
    it rather than inventing a weaker one."""
    out = delta.attribute(r"E:\AI-Setup\does-not-exist-anywhere-xyz.py", since_ts=0)
    assert hasattr(out, "seat") and hasattr(out, "source"), (
        "attribute() must return a typed result carrying the seat AND where that claim came from")
    assert out.seat is None and out.source in ("unattributed", None), (
        "a file nothing touched came back attributed to %r via %r -- a guess wearing a "
        "measurement's clothes" % (out.seat, out.source))


def test_attribution_names_its_source_so_a_reader_can_weigh_it():
    """git author is `balanced7` for EVERY seat and the agent id is `claude` for both Vandors
    (W254), so 'git says claude' and 'the touch stream says claude#428ba6c4' are not the same
    claim. The source must travel with the answer."""
    src = inspect.getsource(delta.attribute)
    assert "touch" in src.lower(), "attribution never consults the touch stream, the only plane "\
                                   "that carries (session_id, agent_id) per action"


def test_the_report_surfaces_the_touch_streams_drop_count():
    """HONEST DENOMINATOR. touch.drops() reads 214 right now. An attribution built on a lossy
    stream that does not say it is lossy is the 'quiet and wrong' failure this house ranks below
    'loud and wrong'. touch.py's own Law 2 already says the counter is not optional."""
    src = inspect.getsource(delta)
    assert "drops" in src, (
        "the delta never reads touch.drops(), so it cannot tell a reader how much of the "
        "attribution stream was lost before it ran")


# ------------------------------------------------------------------ the roots are dirty
def test_the_sweep_does_not_scan_46_dry_run_shadows():
    """MEASURED: touch.default_roots() returns 63 worktrees and 46 of them are season_dryrun_* /
    probe_* / t187_* temp shadows from test runs. All 63 still EXIST, so a naive sweep does not
    fail -- it quietly reports test garbage as the house's activity, which is worse."""
    sig = inspect.signature(delta.since)
    assert "roots" in sig.parameters or "scopes" in sig.parameters, (
        "since() cannot be told which roots to read, so it will inherit all 63")
    src = inspect.getsource(delta)
    assert ("dryrun" in src.lower() or "season_dryrun" in src.lower()
            or "default_roots" not in src), (
        "the delta takes default_roots() wholesale, which is 46 parts test debris to 17 parts "
        "real work")


def test_the_report_states_what_it_examined_and_what_it_skipped():
    """A coverage number without its denominator is the cheapest lie a tool can tell, and this
    house has a lesson on exactly that. The delta must say how many roots it read, how many it
    skipped and why -- otherwise 'no changes' and 'nothing was looked at' render identically."""
    src = inspect.getsource(delta)
    for token in ("examined", "scanned", "skipped"):
        if token in src:
            break
    else:
        pytest.fail("the delta reports no denominator -- a reader cannot tell an empty result "
                    "from an empty scan")


# ------------------------------------------------------------------ metadata only
def test_the_delta_never_reads_file_CONTENTS():
    """touch.py's Law: 'NOTHING RAW IS STORED. Not the command text, not file contents, not a
    URL's query.' The delta runs over the PRIVATE tree -- tax documents, a resume, a divorce-era
    note -- so metadata-only is not a style choice here, it is the reason it is safe to point at
    that directory at all."""
    src = inspect.getsource(delta)
    body = inspect.getsource(delta)
    for reader in ("read_text(", "open(", ".read()"):
        assert reader not in body, (
            f"the delta calls {reader} -- it must work from name, size and mtime only. It is "
            f"pointed at a folder containing tax returns and identity documents.")


# ------------------------------------------------------------------ determinism
def test_the_same_window_gives_the_same_answer():
    """A delta that cannot be re-run is a delta that cannot be audited -- the same rule
    recall-audit's seeded sample already follows."""
    a = delta.since(hours=0.01, roots=[str(ROOT)])
    b = delta.since(hours=0.01, roots=[str(ROOT)])
    assert [getattr(x, "path", x) for x in a] == [getattr(x, "path", x) for x in b], (
        "two identical queries returned different results")
