"""T410 pins -- a pre-rewrite SHA must be followable, or our own chronicle cites nothing.

MEASURED 2026-09-26. This repo has rewritten its history three times. 877 of the 1,436 commit
SHAs our tracked corpus cites -- 61% -- resolved on the authoring machine ONLY, because two
local refs (pre-rewrite-backup, refs/original) pinned the pre-rewrite lineage and a clone never
receives them. chronicles/story.md was the worst-affected file in the repository.

    2026-07-23  reference purge     map left only in .git/filter-repo/, overwritten by the next
                                    run, unread for 65 days, and the FIRST link in the chain
    2026-08-12  PII redaction       map archived off-repo to two drives; invisible to clones
    post-08-16  attribution rewrite NO MAP -- 104 commits moved from 'you@email.com' to the
                                    operator's GitHub address, found only via a stray ref

After this slice: 0 stranded citations, 8 accepted-with-reasons.

These pins hold the properties that make recovery trustworthy rather than merely present.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.git import rewrite_map as rm  # noqa: E402

A = "a" * 40  # original
B = "b" * 40  # after rewrite one
C = "c" * 40  # after rewrite two -- the live commit
D = "d" * 40


def _map(tmp_path, name, rows, durable=True, method="recorded"):
    p = tmp_path / name
    p.write_text("".join(f"{o} {n}\n" for o, n in rows), encoding="utf-8")
    return rm._parse(p, label=name, durable=durable, method=method)


def test_a_pre_rewrite_sha_resolves_to_its_successor(tmp_path):
    """The whole point. Without this every SHA in the chronicle is a dead end."""
    r = rm.Resolver(maps=[_map(tmp_path, "one", [(A, B)])], remote={B})
    res = r.resolve(A)
    assert res.status == rm.TRANSLATED, res
    assert res.sha == B
    assert res.ok


def test_chains_compose_across_rewrites(tmp_path):
    """Our maps chain: 07-23's outputs are 08-12's inputs. A citation older than the first
    rewrite needs BOTH applied, which is why keeping only the latest map is not enough --
    measured, one map recovered 86 citations and both recovered 806."""
    maps = [_map(tmp_path, "one", [(A, B)]), _map(tmp_path, "two", [(B, C)])]
    res = rm.Resolver(maps=maps, remote={C}).resolve(A)
    assert res.sha == C, res
    assert len(res.hops) == 2, res.hops


def test_it_prefers_a_live_endpoint_over_a_dead_end(tmp_path):
    """THE BUG THIS SLICE FOUND. Walking maps greedily in order takes the first hop offered and
    stops. Live case: f94c1368 chased 07-23 then 08-12 and halted at 65ba8152cc36 -- a commit
    that no longer exists in the repository at all -- while a third map held the live
    continuation. A resolver must SEARCH and prefer a chain that ends somewhere fetchable."""
    maps = [
        _map(tmp_path, "dead", [(A, D)]),  # offered first, and D is gone
        _map(tmp_path, "live", [(A, C)]),  # the answer
    ]
    res = rm.Resolver(maps=maps, remote={C}).resolve(A)
    assert res.sha == C, f"took the dead branch: {res}"


def test_a_dead_end_is_reported_as_one_not_as_success(tmp_path):
    """When every chain ends somewhere unfetchable, saying TRANSLATED with no caveat would hand
    back a SHA nobody can check out. The note must say so."""
    res = rm.Resolver(maps=[_map(tmp_path, "one", [(A, D)])], remote={C}).resolve(A)
    assert res.status == rm.TRANSLATED
    assert "no clone can fetch" in res.note, res.note


def test_an_ambiguous_abbreviation_refuses(tmp_path):
    """34 keys in our own history are shared by 68 commits. A wrong successor rewrites history a
    second time, so refusing beats guessing."""
    # They must SHARE the queried prefix; the index buckets on the first 7 characters, so two
    # SHAs differing inside those 7 are not ambiguous at all -- the first draft of this fixture
    # tested nothing for exactly that reason.
    m = _map(tmp_path, "one", [("abc1234" + "0" * 33, B), ("abc1234" + "1" * 33, C)])
    res = rm.Resolver(maps=[m], remote={B, C}).resolve("abc1234")
    assert res.status == rm.AMBIGUOUS, res
    assert not res.ok
    assert "cite more characters" in res.note


def test_an_abbreviation_naming_two_LIVE_commits_is_ambiguous(tmp_path):
    """HEIMDALL'S Q1(d). visible() answered a boolean, so a short citation matching two
    clone-visible commits read as CURRENT -- a confident wrong status that stops the caller
    looking. The first version of this fix added live_matches() and never called it; the wiring
    checker caught that, so this pin exercises the DECISION, not the helper."""
    live = {"abc1234" + "0" * 33, "abc1234" + "1" * 33}
    res = rm.Resolver(maps=[], remote=live).resolve("abc1234")
    assert res.status == rm.AMBIGUOUS, res
    assert not res.ok
    one = rm.Resolver(maps=[], remote={"abc1234" + "0" * 33}).resolve("abc1234")
    assert one.status == rm.CURRENT, one


def test_a_dropped_commit_is_a_real_answer(tmp_path):
    """filter-repo writes <old> 0000..0 for a commit it removed. 'Deliberately deleted' is an
    answer; collapsing it into UNKNOWN throws away the only thing the reader wanted."""
    res = rm.Resolver(maps=[_map(tmp_path, "one", [(A, "0" * 40)])], remote={C}).resolve(A)
    assert res.status == rm.DROPPED, res
    assert "removed from history" in res.note


def test_could_not_check_is_not_clean(tmp_path):
    """tmp_path is not a git repo, so the clone-visible probe genuinely FAILS -- the real path,
    not a simulated one. An unknown answer must say it could not look."""
    res = rm.Resolver(maps=[], repo=tmp_path).resolve(A)
    assert res.status == rm.UNKNOWN
    assert "could not" in res.note.lower(), res.note


def test_a_chain_we_cannot_verify_is_not_reported_as_translated(tmp_path):
    """HEIMDALL'S FINDING, 2026-09-26. The dead-end fallthrough used to return TRANSLATED with
    ok=True when the visibility probe had failed, distinguished only by a note string -- so any
    caller testing `res.ok` was handed an unverified claim wearing a success label. That is the
    absence-reads-as-success defect this module's own docstring lectures about, committed
    inside it."""
    m = _map(tmp_path, "one", [(A, B)])
    res = rm.Resolver(maps=[m], repo=tmp_path).resolve(A)  # not a repo: the probe fails
    assert res.status == rm.UNVERIFIED, res
    assert res.ok is False, "an unverified endpoint must never read as ok"
    assert res.sha == B, "the candidate is still worth reporting -- just not as a success"


def test_an_empty_remote_set_is_not_a_failed_probe(tmp_path):
    """The two were collapsed. A repo with no remotes legitimately has nothing clone-visible,
    which is a MEASUREMENT; a probe that could not run is an ABSENCE of one. Only the second
    may produce UNVERIFIED."""
    m = _map(tmp_path, "one", [(A, B)])
    res = rm.Resolver(maps=[m], remote=set()).resolve(A)  # checked; nothing is pushed
    assert res.status == rm.TRANSLATED, res
    assert "no clone can fetch" in res.note, res.note


def test_a_failed_probe_is_not_cached_as_empty(tmp_path):
    """A transient git failure must not poison every later answer from the same Resolver. The
    first draft cached the failure as an empty set, and `self._remote is None` was then False
    forever, so one blip silently downgraded the rest of the session."""
    r = rm.Resolver(maps=[], repo=tmp_path)
    assert r.remote_set() is None
    assert r._remote is None, "a failure was cached, so no retry can ever happen"
    assert r._probe_failures == 1, "failures must be counted, or the retry is unbounded"


def test_an_inferred_hop_never_reads_as_a_record(tmp_path):
    """A reconstructed map is a deduction. A caller deserves to know which kind of claim it is
    looking at, so the provenance rides the hop label, not only the meta file."""
    m = _map(tmp_path, "guess", [(A, C)], method="reconstructed")
    res = rm.Resolver(maps=[m], remote={C}).resolve(A)
    assert "inferred" in res.line(), res.line()


def test_a_map_only_in_dotgit_is_marked_volatile(tmp_path):
    """The 07-23 map lived in .git/filter-repo/commit-map for 65 days. That file is overwritten
    by the next filter-repo run and never reaches a clone, so it must not be mistaken for a
    durable one -- the distinction is what makes the checker able to demand capture."""
    (tmp_path / ".git" / "filter-repo").mkdir(parents=True)
    (tmp_path / ".git" / "filter-repo" / "commit-map").write_text(f"{A} {B}\n", encoding="utf-8")
    maps = rm.load_maps(tmp_path)
    assert len(maps) == 1, maps
    assert maps[0].durable is False, maps


def test_an_archived_map_is_preferred_and_not_duplicated(tmp_path):
    """Once captured, the .git copy is redundant. Loading both would double every hop."""
    d = tmp_path / "state" / "rewrites" / "2026-01-01"
    d.mkdir(parents=True)
    (d / "commit-map").write_text(f"{A} {B}\n", encoding="utf-8")
    (tmp_path / ".git" / "filter-repo").mkdir(parents=True)
    (tmp_path / ".git" / "filter-repo" / "commit-map").write_text(f"{A} {B}\n", encoding="utf-8")
    maps = rm.load_maps(tmp_path)
    assert [m.durable for m in maps] == [True], [(m.label, m.durable) for m in maps]


# ------------------------------------------------- reconstruction must be corroborated
def _rr():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_rr", str(Path(ROOT, "scripts", "rewrite_recover.py")))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_a_name_only_match_is_not_corroborated():
    """HEIMDALL'S Q2, 2026-09-26. (author-date, subject) is a NAME match; 34 keys in this
    history are shared by 68 commits, so the name alone must not license a row a resolver will
    treat as an answer. tree_agree used to be computed, printed, and thrown away."""
    rr = _rr()
    # (tree, author-date, author-email, subject, oid)
    o = ("t1", "100", "a@x", "same subject", "o1")
    n = ("t2", "100", "b@x", "same subject", "n1")
    parents = {"o1": ("po",), "n1": ("pn",)}  # parents correspond to nothing
    assert rr.corroborate(o, n, parents, {}) == set(), "a bare name match claimed support"


def test_tree_agreement_corroborates():
    """A tree-preserving rewrite (author or message only) leaves the tree hash untouched, so
    equality there is real evidence independent of the name."""
    rr = _rr()
    o = ("SAME", "100", "a@x", "s", "o1")
    n = ("SAME", "100", "b@x", "s", "n1")
    assert "tree" in rr.corroborate(o, n, {}, {})


def test_parent_structure_corroborates_and_outranks_the_key_tier():
    """A rewrite preserves parent structure by definition, so a matched parent is the strongest
    signal. The key-only tier is reported SEPARATELY because it is the same name heuristic one
    generation up -- independent of this commit, but not of the method."""
    rr = _rr()
    o = ("t1", "100", "a@x", "s", "o1")
    n = ("t2", "100", "b@x", "s", "n1")
    parents = {"o1": ("po",), "n1": ("pn",)}

    strong = rr.corroborate(o, n, parents, {"po": "pn"})
    assert strong == {"parent"}, strong

    keys = {"po": ("55", "parent subject"), "pn": ("55", "parent subject")}
    weak = rr.corroborate(o, n, parents, {}, key_of=lambda sha: keys.get(sha))
    assert weak == {"parent-key"}, weak
    assert "parent" not in weak, "the weaker tier must not be reported as the strong one"


def test_a_differing_parent_count_corroborates_nothing():
    """A squash or a merge collapse changes the parent count; that is not the same commit's
    shape, so it must not count as agreement."""
    rr = _rr()
    o = ("t1", "100", "a@x", "s", "o1")
    n = ("t1", "100", "a@x", "s", "n1")
    sig = rr.corroborate(o, n, {"o1": ("p1", "p2"), "n1": ("p1",)}, {})
    assert sig == {"tree"}, sig  # the tree still agrees; the parents must not


def test_every_committed_inferred_row_is_corroborated():
    """The live property, not a synthetic one. A reconstructed map in state/rewrites/ whose rows
    rest on the name alone would be exactly the debt this rule exists to refuse -- and the
    one-row cited-gap map WAS name-only until the parent lookup learned to see commits that sit
    on no branch, which is the case a git gc deletes."""
    import json

    rr = _rr()
    for d in sorted((ROOT / "state" / "rewrites").iterdir()):
        if not d.is_dir():
            continue
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        if meta.get("method") != "reconstructed":
            continue
        rows = [ln.split() for ln in (d / "commit-map").read_text(encoding="utf-8").splitlines()]
        pairs = [(a, b) for a, b in (r for r in rows if len(r) == 2)]
        assert pairs, f"{d.name} is an empty reconstructed map"
        info = rr.commit_rows(ROOT, "--all")
        want = [s for pair in pairs for s in pair if s not in info]
        for i in range(0, len(want), 200):
            info.update(rr.commit_rows(ROOT, "--no-walk", *want[i : i + 200]))
        parents = rr.parents_for(ROOT, [s for pair in pairs for s in pair])
        keys = {k: (v[1], v[3]) for k, v in info.items()}
        pwant = [q for ps in parents.values() for q in ps if q not in keys]
        for i in range(0, len(pwant), 200):
            for k, v in rr.commit_rows(ROOT, "--no-walk", *pwant[i : i + 200]).items():
                keys[k] = (v[1], v[3])
        bad = []
        for a, b in pairs:
            if a not in info or b not in info:
                continue  # an unreadable side cannot be judged here
            if not rr.corroborate(info[a], info[b], parents, dict(pairs), key_of=lambda sha: keys.get(sha)):
                bad.append(a[:12])
        assert not bad, f"{d.name} holds name-only rows: {bad}"


# ----------------------------------------------------------- the durability property itself
def _git(*a):
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), *a], capture_output=True, text=True, encoding="utf-8", errors="replace"
        ).stdout
        or ""
    )


def test_the_maps_are_actually_IN_git():
    """The defect in one line: a map on an ignored path is invisible to every clone, so no clone
    can resolve any citation. state/ is ignored wholesale here, so this needs an explicit
    negation -- and a resolver whose maps are untracked is theatre. Same argument as the
    state/drills negation, one plane over."""
    tracked = set(_git("ls-files", "state/rewrites/").split())
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "state" / "rewrites").rglob("*") if p.is_file()}
    assert on_disk, "no maps on disk at all"
    missing = sorted(on_disk - tracked)
    assert not missing, f"rewrite artifacts exist but git cannot see them: {missing}"


def test_every_map_declares_its_provenance():
    """A map with no meta.json is a puzzle: nobody can tell whether it was recorded by the tool
    that did the rewrite or deduced afterwards, and those carry different weight."""
    for d in sorted((ROOT / "state" / "rewrites").iterdir()):
        if not d.is_dir():
            continue
        meta = d / "meta.json"
        assert meta.is_file(), f"{d.name} has a map and no meta.json"
        m = json.loads(meta.read_text(encoding="utf-8"))
        assert m.get("method") in ("recorded", "reconstructed"), f"{d.name}: {m.get('method')}"
        assert (m.get("why") or "").strip(), f"{d.name} does not say what the rewrite was for"


def test_every_accepted_waiver_states_a_reason():
    """An allow-list entry without a reason is indistinguishable from a defect someone got tired
    of. This also caught a real error: two entries were first keyed on 12-char prefixes with
    invented tails, and a waiver keyed on a guessed hash silently waives nothing."""
    p = ROOT / "state" / "rewrites" / "accepted_unresolvable.json"
    if not p.is_file():
        return
    for sha, why in json.loads(p.read_text(encoding="utf-8"))["unresolvable"].items():
        assert len(sha) == 40, f"{sha} is not a full oid"
        assert isinstance(why, str), f"{sha[:12]} has no real reason"
        assert len(why.strip()) > 30, f"{sha[:12]} has no real reason"
        assert _git("cat-file", "-t", sha).strip() == "commit", (
            f"{sha[:12]} does not name a commit in this repo -- a guessed hash waives nothing"
        )


def test_a_bad_waiver_key_is_caught_at_the_GATE_not_only_here(tmp_path):
    """HEIMDALL'S FINDING, 2026-09-26. The length + cat-file guard lived only in this file, and
    a pin does not run at the gate -- so the runtime checker accepted any key with a non-empty
    reason, which is exactly the bug that let two invented hash tails through. The guard now
    lives on the runtime path; this pin proves the runtime path rejects them."""
    import json

    import scripts.checkers.check_rewrite_maps as chk

    bad = {
        "unresolvable": {
            "b18ff3870b71": "a 12-char prefix -- the shape that actually slipped through",
            "z" * 40: "forty characters, but not hex",
            "0" * 40: "well-formed and names no commit in this repo",
        }
    }
    path = tmp_path / "accepted_unresolvable.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    orig = chk.ACCEPTED
    try:
        chk.ACCEPTED = path
        waived, problems = chk.accepted()
    finally:
        chk.ACCEPTED = orig
    assert waived == {}, f"a malformed key was accepted: {waived}"
    assert len(problems) == 3, problems


def test_unpushed_work_is_not_confused_with_lost_history():
    """Cited-and-unfetchable has two causes needing opposite fixes: lost history needs a map,
    unpushed work needs a push. The subtle part is the exclusion -- pre-rewrite-backup IS a
    local branch, so a naive 'reachable from a local branch' test would relabel every rewrite
    orphan as merely unpushed and the gate would go quiet on the whole defect class."""
    import scripts.checkers.check_rewrite_maps as chk

    local = chk.awaiting_push()
    assert local, "no local commits at all -- the helper cannot be exercised here"
    backup = _git("rev-parse", "--verify", "-q", "refs/heads/pre-rewrite-backup").strip()
    if backup:
        assert backup not in local, (
            "pre-rewrite-backup's tip counts as unpushed work, so rewrite orphans would be "
            "silently reclassified and the gate would stop reporting them"
        )
    head = _git("rev-parse", "HEAD").strip()
    assert head in local, "HEAD is not reachable from a local branch -- the helper is broken"


def test_the_verb_exists_on_all_three_doors():
    """A capability reachable only by knowing a script path is not a capability. And a ToolBox
    METHOD without a TOOLS schema entry is not model-reachable, so check both halves: the
    door-parity checker reads the class, the model reads the schema."""
    import agent_cli
    from core.comm.toolbox import TOOLS, ToolBox

    assert callable(getattr(agent_cli, "cmd_sha", None)), "no CLI handler"
    names = [t.get("function", t).get("name") for t in TOOLS]
    assert "sha" in names, "on the ToolBox class but absent from TOOLS -- not reachable"
    assert callable(getattr(ToolBox, "sha", None)), "in TOOLS but not implemented"
    mcp = Path(ROOT, "ai_setup_mcp.py").read_text(encoding="utf-8")
    assert "async def sha(" in mcp, "no MCP tool"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
