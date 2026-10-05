#!/usr/bin/env python3
"""Turn a pre-rewrite commit SHA back into the commit it became.

WHY (T410, measured 2026-09-26). This repo has run THREE history rewrites -- the 2026-07-23
Apple/Samsung reference purge, the 2026-08-12 third-party-PII redaction, and a third after
2026-08-16 that we kept no map for at all, found only because it left a refs/original ref
behind. Each one gave every later commit a new SHA, and our corpus cites SHAs constantly:
the chronicle, the task ledger, lessons, failure ledgers, fence reconciliations.

    1,436 commit SHAs cited across tracked docs resolve in this checkout
      877 of them (61%) resolve ONLY here, pinned by local refs -- pre-rewrite-backup and
          refs/original -- that a clone never receives
      806 of those 877 become resolvable again by chaining the two surviving maps

The 07-23 purge closed with "every commit SHA in the repo changed -- that's clean for a solo
repo like this one". True when written. What falsified it was our own corpus learning to cite
SHAs, which is why this module exists rather than a note saying to be careful.

ZERO IS NOT NO. Every answer here is labelled: CURRENT (already the live SHA), TRANSLATED
(with the hops that got there), DROPPED (a rewrite deliberately removed this commit -- a real
answer, not a failure), AMBIGUOUS (an abbreviation matching two successors; refusing is the
only honest move) and UNKNOWN (no map covers it). A resolver that guessed would be worse than
one that says it cannot tell, because a wrong successor rewrites history a second time.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ZERO = "0" * 40
MAX_HOPS = 12  # three rewrites so far; a cap that can never loop forever

CURRENT = "current"
TRANSLATED = "translated"
DROPPED = "dropped"
AMBIGUOUS = "ambiguous"
UNKNOWN = "unknown"
# The chain ended somewhere, but the clone-visible probe could not run, so nothing
# confirms the endpoint is fetchable. NOT ok: an unverified claim must never wear a
# success label.
UNVERIFIED = "unverified"
_PROBE_LIMIT = 3  # retries before this Resolver gives up asking git
_VISIT_BUDGET = 4096  # DFS node visits; a pathological map graph must not hang a verb


@dataclass
class RewriteMap:
    """One rewrite's old->new table."""

    label: str
    path: Path
    durable: bool  # committed, so it reaches every clone
    method: str = "recorded"  # "recorded" by the rewrite tool, or "reconstructed" after
    rows: dict = field(default_factory=dict)
    dropped: set = field(default_factory=set)
    _prefix: dict = field(default_factory=dict, repr=False)

    @property
    def shown(self):
        """How this map names itself in a hop. An inference must never read as a record."""
        return self.label if self.method == "recorded" else f"{self.label}, inferred"

    def index(self):
        self._prefix = {}
        for old in self.rows:
            self._prefix.setdefault(old[:7], []).append(old)
        return self

    def lookup(self, sha):
        """(new_sha, status) for a full or abbreviated old SHA; status None when unmatched."""
        if sha in self.rows:
            return self.rows[sha], TRANSLATED
        if sha in self.dropped:
            return None, DROPPED
        if len(sha) < 40:
            hits = {self.rows[k] for k in self._prefix.get(sha[:7], ()) if k.startswith(sha)}
            if len(hits) == 1:
                return hits.pop(), TRANSLATED
            if len(hits) > 1:
                return None, AMBIGUOUS
            if any(k.startswith(sha) for k in self.dropped):
                return None, DROPPED
        return None, None


def _parse(path, label, durable, method="recorded"):
    rows, dropped = {}, set()
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or len(parts[0]) != 40 or len(parts[1]) != 40:
            continue  # filter-repo writes a header line; skip anything that is not a pair
        if parts[1] == ZERO:
            dropped.add(parts[0])
        else:
            rows[parts[0]] = parts[1]
    if not rows and not dropped:
        return None
    return RewriteMap(label=label, path=Path(path), durable=durable, method=method, rows=rows, dropped=dropped).index()


def _method_of(meta_path):
    """'recorded' or 'reconstructed', from the map's own meta.json. Defaults to recorded only
    when a meta file is absent -- an unreadable meta is treated as unknown provenance."""
    try:
        import json

        return str(json.loads(meta_path.read_text(encoding="utf-8")).get("method", "recorded"))
    except FileNotFoundError:
        return "recorded"
    except Exception:
        return "provenance unreadable"


def repo_root(repo=None):
    return Path(repo or os.environ.get("AKASHIC_REPO") or Path(__file__).resolve().parents[2])


def load_maps(repo=None):
    """Every map we can find, oldest first so a chase composes in rewrite order.

    Two sources, and the distinction matters. state/rewrites/<date>/commit-map is COMMITTED,
    so it reaches every clone. .git/filter-repo/commit-map is whatever the last filter-repo run
    left behind: read opportunistically and marked NOT durable, because the next rewrite
    overwrites it -- which is how the 07-23 map came within one command of being lost while
    supplying most of our recovery coverage.
    """
    root = repo_root(repo)
    found = []
    archive = root / "state" / "rewrites"
    if archive.is_dir():
        for d in sorted(p for p in archive.iterdir() if p.is_dir()):
            m = _parse(d / "commit-map", label=d.name, durable=True, method=_method_of(d / "meta.json"))
            if m:
                found.append(m)
    volatile = root / ".git" / "filter-repo" / "commit-map"
    if volatile.is_file():
        m = _parse(volatile, label=".git/filter-repo (volatile)", durable=False)
        # Skip it when an archived map already holds all of its rows; keep it otherwise, since
        # an unarchived rewrite is exactly the case where it is the only surviving copy.
        if m and not any(set(m.rows.items()) <= set(o.rows.items()) for o in found):
            found.append(m)
    return found


@dataclass
class Resolution:
    cited: str
    status: str
    sha: str = None
    hops: list = field(default_factory=list)
    note: str = ""

    @property
    def ok(self):
        return self.status in (CURRENT, TRANSLATED)

    def line(self):
        if self.status == TRANSLATED:
            via = " -> ".join(f"{new[:12]} [{label}]" for _, new, label in self.hops)
            tail = f"  ({self.note})" if self.note else ""
            return f"{self.cited}  TRANSLATED  {via}{tail}"
        if self.status == UNVERIFIED:
            via = " -> ".join(f"{new[:12]} [{label}]" for _, new, label in self.hops)
            return f"{self.cited}  UNVERIFIED  {via}  ({self.note})"
        return f"{self.cited}  {self.status.upper()}  {self.note}".rstrip()


class Resolver:
    """Chase a SHA forward through every rewrite until it stops moving."""

    def __init__(self, maps=None, repo=None, remote=None):
        self.repo = repo_root(repo)
        self.maps = load_maps(self.repo) if maps is None else list(maps)
        # `remote` is a test seam: the clone-visible set, supplied instead of shelling out.
        # Passing an EMPTY set deliberately means "could not check", matching the live failure.
        self._remote = None if remote is None else set(remote)
        self._probe_failures = 0

    # --- reachability -------------------------------------------------------------------
    def remote_set(self):
        """Commits a fresh clone would receive, or None when the probe could not run.

        This is the whole difference between "resolves" and "resolves for anyone else":
        without it, all 877 of our broken citations look healthy from this machine.

        NONE AND AN EMPTY SET ARE DIFFERENT OBSERVATIONS and this returns them differently --
        an empty set means checked, nothing is pushed; None means we could not look. The first
        draft collapsed both into an empty set AND cached it, so a single transient git failure
        silently turned every later answer into an unverified claim wearing a success label:
        the exact defect this module's own docstring lectures about, committed inside it.
        Found by Heimdall's review, 2026-09-26. A failure is therefore not cached, so a
        transient one cannot poison the instance -- bounded by _PROBE_LIMIT so a permanently
        broken repo does not re-shell on every lookup.
        """
        if self._remote is not None:
            return self._remote
        if self._probe_failures >= _PROBE_LIMIT:
            return None
        try:
            p = subprocess.run(
                ["git", "-C", str(self.repo), "rev-list", "--remotes"], capture_output=True, text=True, timeout=180
            )
            if p.returncode != 0:
                self._probe_failures += 1
                return None
            self._remote = set((p.stdout or "").split())
        except Exception:
            self._probe_failures += 1
            return None
        return self._remote

    def visible(self, sha):
        """True when a clone can see this commit; None when we could not check at all."""
        rs = self.remote_set()
        if rs is None:
            return None
        if len(sha) == 40:
            return sha in rs
        return any(o.startswith(sha) for o in rs)

    def live_matches(self, sha):
        """How many clone-visible commits a (possibly abbreviated) citation names.

        `visible()` answers a boolean, so it cannot say "several" -- and a short citation that
        names two live commits would read as CURRENT, a confident wrong status. Counting is the
        only way to tell an unambiguous hit from a collision. Heimdall's review, 2026-09-26.
        """
        rs = self.remote_set()
        if rs is None:
            return None
        if len(sha) == 40:
            return 1 if sha in rs else 0
        n = 0
        for o in rs:
            if o.startswith(sha):
                n += 1
                if n > 1:
                    break
        return n

    # --- the walk -----------------------------------------------------------------------
    def resolve(self, sha, check_remote=True):
        sha = (sha or "").strip().lower()
        if not sha or any(c not in "0123456789abcdef" for c in sha) or not 7 <= len(sha) <= 40:
            return Resolution(sha, UNKNOWN, note="not a commit SHA (need 7-40 hex characters)")

        if check_remote:
            # COUNT, do not assert. An abbreviation that names two live commits is AMBIGUOUS,
            # and answering CURRENT there is a confident wrong status -- the caller would stop
            # looking. live_matches() exists for exactly this and must be CALLED, not merely
            # defined: the wiring checker caught the first version of this fix, where the
            # function was added and the decision below still used the boolean.
            hits = self.live_matches(sha)
            if hits and hits > 1:
                return Resolution(
                    sha,
                    AMBIGUOUS,
                    note="this abbreviation names more than one commit a clone can see; cite more characters",
                )
            if hits == 1:
                return Resolution(sha, CURRENT, sha=sha, note="a clone can see this commit")

        # A definitive answer about the CITED sha beats any chase. Ambiguity can only arise
        # here, because every map target is a full 40-char oid.
        for m in self.maps:
            _new, status = m.lookup(sha)
            if status == DROPPED:
                return Resolution(sha, DROPPED, note=f"removed from history by the {m.shown} rewrite")
            if status == AMBIGUOUS:
                return Resolution(
                    sha,
                    AMBIGUOUS,
                    note=f"the abbreviation matches several successors in {m.shown}; cite more characters",
                )

        ends, truncated = self._endpoints(sha)
        if not ends:
            if check_remote and self.remote_set() is None:
                return Resolution(
                    sha,
                    UNKNOWN,
                    note="no map covers it, and the clone-visible set could not "
                    "be read -- this is 'could not check', not 'clean'",
                )
            return Resolution(sha, UNKNOWN, note="no map covers it")

        # RANK THE ENDPOINTS; DO NOT TAKE THE FIRST VISIBLE ONE. Returning on the first visible
        # target makes MAP ORDER decide the answer, and map order is by date ascending -- so an
        # EARLIER rewrite's target wins even when a LATER rewrite moved it again. Measured here:
        # 43 old SHAs get different targets from different maps. None of them currently has two
        # clone-visible targets, so this was latent rather than live -- but it becomes live
        # during exactly the operation this module exists for, because a rewrite's superseded
        # targets stay visible locally until the remote is updated. Heimdall's review, 2026-09-26.
        #
        # Preference order: reachable by a clone, then the FARTHEST forward (later rewrites sit
        # deeper in the chain), then the fewest inferred hops -- a record beats a deduction.
        def rank(end):
            tip, path, inferred = end
            return (1 if (check_remote and self.visible(tip)) else 0, len(path), -inferred)

        tip, path, inferred = max(ends, key=rank)
        vis = self.visible(tip) if check_remote else None
        if check_remote and vis is None:
            return Resolution(
                sha,
                UNVERIFIED,
                sha=tip,
                hops=path,
                note="the chain ends here, but the clone-visible set could not be "
                "read, so nothing confirms this commit is fetchable -- could "
                "not check, NOT clean",
            )
        note = ""
        if check_remote and not vis:
            note = (
                "chain ends on a commit no clone can fetch -- a later rewrite moved it and "
                "left no map (try: rewrite_recover.py reconstruct)"
            )
        elif truncated:
            note = "search budget reached; a longer chain may exist"
        return Resolution(sha, TRANSLATED, sha=tip, hops=path, note=note)

    def _endpoints(self, start):
        """Every terminal SHA reachable by chaining maps, as (tip, hops, inferred_count).

        DFS with a PER-PATH visited set. A single global `seen` set pruned any node a second
        chain reached later, so a re-convergent history was collapsed onto the FIRST route that
        touched it -- which made the old code's "the longest chain went as far as the maps
        allow" comment false, and truncated the hops any auditor would read. Per-path is safe
        here because fan-out is bounded by the number of maps; _VISIT_BUDGET stops a pathological
        graph regardless, and the caller is told when it bit.
        """
        out, stack, visits = [], [(start, [], frozenset((start,)), 0)], 0
        while stack and visits < _VISIT_BUDGET:
            cur, path, seen, inferred = stack.pop()
            visits += 1
            nxt = []
            for m in self.maps:
                new, status = m.lookup(cur)
                if status == TRANSLATED and new and new != cur and new not in seen:
                    nxt.append((new, m))
            if not nxt or len(path) >= MAX_HOPS:
                if path:
                    out.append((cur, path, inferred))
                continue
            for new, m in nxt:
                # An IDENTITY row reached through an abbreviation is an EXPANSION, not a
                # rewrite: "f94c1368 -> f94c1368dbe2" reads as though the 07-23 purge moved
                # that commit when all it did was leave it alone. Continue from the full oid
                # without recording a hop, so the chain shows only real rewrites -- and so a
                # spurious hop cannot inflate a path's length in the ranking.
                expansion = len(cur) < 40 and new.startswith(cur)
                stack.append(
                    (
                        new,
                        path if expansion else path + [(cur, new, m.shown)],
                        seen | {new},
                        inferred + (0 if expansion or m.method == "recorded" else 1),
                    )
                )
        return out, visits >= _VISIT_BUDGET


def resolve(sha, repo=None, check_remote=True):
    """One-shot convenience. Build a Resolver directly when resolving many."""
    return Resolver(repo=repo).resolve(sha, check_remote=check_remote)
