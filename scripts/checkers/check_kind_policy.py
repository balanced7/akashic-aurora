"""check_kind_policy -- guard the KIND surface against silent fragmentation (T177).

THE MIRROR OF check_door_parity. That checker guards the agent-facing VERB surface: explicit
manifest, FAIL on a new unclassified verb, ratcheted debt. The KIND surface had no equivalent, and
the census measured what that costs: 31 kinds, 14 hand-maintained policy sets across 11 files, and
17 of 31 kinds (55%) in one set or fewer. Because every policy is a MEMBERSHIP test, a miss is
indistinguishable from a deliberate exclusion -- so an unlisted kind is silently not-an-answer,
not-salient, not-wake-worthy. That already cost a whole peer gate: kind=review was sent to three
seats with reply expectations and all three stayed silent.

THE DOCTRINE THIS MAKES EXECUTABLE. A rule that lives only in a document requires someone to
REMEMBER it, which is the exact failure the rule describes. The bedside test is "when I add this,
must I remember to tell something else?" -- and K-D below is that test automated: add a policy set
without declaring its plane and the CHECKER asks, not a person's memory.

  K-A  FAIL  two files defining the same *KINDS identifier with DIFFERENT membership
  K-B  FAIL  a kind on two planes with no written rationale ('note' is a cue on the bus and a
             durable write-once record -- opposite policies, one word)
  K-C  COUNT bus-plane orphans (a kind in <=1 policy set): the born-silent population, ratcheted
  K-D  FAIL  a *KINDS set with no declared plane
  K-E  ADVISORY ONLY, never gates: redundancy candidates (identical signature within a plane)

WHY K-E MAY NEVER GATE. This instrument was wrong. Run across planes, the identical-signature test
called 10 kinds redundant that were not: command/file_edit/tool_call share a blank row on every bus
axis, yet event_promoter weights them 3/2/1 -- a consumer DOES act on the difference. An instrument
that produced a confident false "merge these" may advise and may never decide. Worse, merging is
irreversible against an append-only substrate and an open boundary (a public repo, an MCP door, and
agents that mint kind strings at runtime): redundancy licenses DEPRECATION -- accept both,
normalize at the door, keep the old resolvable forever -- never a silent merge.

UNRESOLVED SETS ARE REPORTED, NOT SKIPPED. A set this reads statically but cannot evaluate (a
computed membership) is surfaced as UNRESOLVED rather than dropped, because silently omitting a
policy set from a guard against silent omission would be the joke writing itself.

Run:  py scripts/checkers/check_kind_policy.py            # gate
      py scripts/checkers/check_kind_policy.py --report   # full matrix + coverage
"""
import ast
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- MANIFEST: which plane each policy set speaks for -------------------------------------
# "Enumerate the consumers" is a PRECONDITION of judging fragmentation, so it lives here as
# data rather than as a step someone performs from memory. A set absent from this map fails.
PLANES = {
    # the bus plane -- messages between seats
    "ANSWER_KINDS": "bus", "ESCALATE_KINDS": "bus", "LONG_KINDS": "bus",
    "SALIENT_KINDS": "bus", "FLAGGABLE_KINDS": "bus",
    "PENDING_SKIP_KINDS": "bus", "SKIP_KINDS": "bus", "SKIP_KINDS_LANE": "bus",
    "WAKE_WORTHY_KINDS": "bus", "CONSOLE_KINDS": "bus",
    # T332 (Daniil's ruling, 2026-08-17): STALE_ASK_KINDS, ASK_KINDS and _ASK_KINDS were three
    # DIFFERENT questions sharing one word, which is why K-A never saw them -- it compares
    # identical identifiers across files, and these were three distinct identifiers telling the
    # same lie. Renamed for what each actually gates. The registry (core/comm/kinds.py) caught
    # what this checker structurally could not, and its own blind spot is the mirror image:
    # forks() groups by NAME, so it reported one forked concept where there were three honest
    # ones. Neither instrument is wrong; each is blind where the other looks.
    "NEVER_DROP_WHEN_STALE": "bus", "AUTO_REDRIVE_KINDS": "bus",
    "_NEEDS_ATTENTION_KINDS": "bus",
    # T175: was SKIP_KINDS in check_bus_atom_pointers, colliding with bifrost_wake's. Renamed for
    # what it excludes (cargo), not for what the code does with it. K-D caught the rename the
    # moment it landed and demanded this line -- which is the bedside test working: nobody had to
    # REMEMBER to classify the new set.
    "NON_CARGO_KINDS": "bus",
    # T223: the outbound Discord bridge's forward allowlist -- which bus kinds are worth
    # buzzing a phone. Bus plane, same as every other set that filters seat-to-seat messages.
    # K-D caught this the moment the set landed and refused the commit, which is the same
    # bedside test working a second time: I did not have to remember, and I would not have.
    "FORWARD_KINDS": "bus",
    # The remote Akashic<->Akashic bridge allowlist: which bus kinds may cross a FLEET
    # BOUNDARY. Bus plane, and deliberately a SEPARATE SET from FORWARD_KINDS above even
    # though both filter seat-to-seat messages -- the two answer different questions.
    # FORWARD_KINDS asks "worth buzzing the operator's phone?", so it rightly contains halt
    # and nudge; BRIDGE_KINDS asks "safe to accept from ANOTHER FLEET?", where a control verb
    # is the one thing that must never cross. v0.1 imported FORWARD_KINDS to stop the two
    # bridges drifting and silently handed a remote peer two control verbs. Anti-drift now
    # rides a pin (test_bridge_allowlist_contains_no_control_kind) instead of a shared name.
    # K-D caught this set the moment it landed -- the third time the bedside test has worked.
    "BRIDGE_KINDS": "bus",
    # The relay's list: which admitted peer kinds may be SPOKEN TO LOCAL SEATS. Bus plane,
    # and a THIRD set beside FORWARD_KINDS and BRIDGE_KINDS because it answers a third
    # question. FORWARD_KINDS: worth buzzing the operator's phone. BRIDGE_KINDS: safe to
    # accept from another fleet. RELAY_KINDS: safe to put in front of an agent that will act
    # on what it reads. Each is strictly narrower than the last, and collapsing any two would
    # make one of the three questions un-askable -- the exact drift K-D exists to surface.
    # Caught by K-D on the commit that introduced it, the fourth time this test has refused a
    # set nobody remembered to classify.
    "RELAY_KINDS": "bus",
    # the event plane -- what a seat DID
    "EVENT_KINDS": "event",
    # T196a: friction's map of durable terminal-event kinds -> episode outcomes. These are
    # firehose kinds (expectation_settled_answered / expectation_dead /
    # expectation_settled_done_task), so the set lives on the event plane.
    "TERMINAL_KINDS": "event",
    # the narrative plane -- beats on the story spine
    "BEAT_KINDS": "beat", "BOUNDARY_KINDS": "beat",
}

# A cross-plane name collision with a WRITTEN rationale is a recorded decision, not drift.
ALLOWED_COLLISIONS = {
    # T332 (Daniil's ruling, 2026-08-17) -- this is the written rationale K-B has been asking
    # for since T177, and it is a RULING, not a suppression. The collision is real and stays:
    # a bus note is a cue skipped from pending, an event note is a captured record, a beat
    # note is narrative. What changed is that the ambiguous QUESTION can no longer be asked --
    # core/comm/kinds.py:resolve() now takes `plane` as a REQUIRED argument, so "is note
    # salient?" is a TypeError and a cross-plane question returns UNCLASSIFIED-with-a-reason
    # instead of a confident False. The house move: make the bad state unrepresentable rather
    # than rename around it. Renaming per plane was the alternative and was rejected because
    # it rewrites the meaning of records already at rest -- a migration event, not a store
    # primitive (note durability-over-legibility-2026-08-16).
    "note": ("three planes, opposite policies, ruled T332: resolve() requires `plane`, so the "
             "ambiguous question cannot be asked. Verified by this checker (bus+event)."),
    # Same ruling, different instrument. THIS CHECKER CANNOT SEE THIS ONE: BEAT_KINDS reads as
    # UNRESOLVED (a computed membership), so K-B never had the beat plane in view. The registry
    # did -- kinds.plane_collisions() reports decision on bus_kind+beat_kind -- which is the
    # complementarity worth keeping: the checker is blind where the registry looks, and the
    # registry groups by name where the checker compares identifiers. Recorded here so that if
    # BEAT_KINDS ever becomes statically resolvable this does not fire as a fresh surprise.
    "decision": ("bus + beat, ruled T332 with `note`; found by kinds.plane_collisions(), NOT "
                 "by this checker -- BEAT_KINDS is UNRESOLVED here."),
}

ADVISORY = {"redundancy"}


def is_advisory(check: str) -> bool:
    """A check that has produced a confident false positive may advise, never gate."""
    return check in ADVISORY


# --- discovery ----------------------------------------------------------------------------
def _literal(node, seen):
    """Resolve a set/tuple/list literal, frozenset(...), or `NAME | {literal}`. None if not."""
    try:
        return set(ast.literal_eval(node))
    except Exception:
        pass
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("frozenset", "set", "tuple"):
        if len(node.args) == 1:
            return _literal(node.args[0], seen)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left, right = _literal(node.left, seen), _literal(node.right, seen)
        if left is None and isinstance(node.left, ast.Name):
            left = seen.get(node.left.id)
        if right is None and isinstance(node.right, ast.Name):
            right = seen.get(node.right.id)
        if left is not None and right is not None:
            return left | right
    return None


def _python_files(root: str):
    for base in ("core", "scripts", "agent.py", "agent_cli.py"):
        target = os.path.join(root, base)
        if os.path.isfile(target):
            yield target
        elif os.path.isdir(target):
            for dirpath, _, names in os.walk(target):
                for n in names:
                    if n.endswith(".py"):
                        yield os.path.join(dirpath, n)


def _scan(root: str):
    """({(relpath, NAME): set}, [(relpath, NAME) unresolved]) over every *KINDS* constant."""
    found, unresolved = {}, []
    for path in _python_files(root):
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (OSError, SyntaxError):
            continue
        rel, seen = os.path.relpath(path, root).replace("\\", "/"), {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if not (isinstance(t, ast.Name) and "KINDS" in t.id):
                    continue
                members = _literal(node.value, seen)
                if members is None or not all(isinstance(m, str) for m in members):
                    unresolved.append((rel, t.id))
                    continue
                seen[t.id] = members
                found[(rel, t.id)] = members
    return found, unresolved


def discover_kind_sets(root: str):
    """{(relpath, NAME): set} for every statically resolvable *KINDS* constant."""
    return _scan(root)[0]


def discover_with_unresolved(root: str):
    """Both halves. An UNRESOLVED set is reported, never silently dropped -- omitting a policy
    set from a guard against silent omission would be the joke writing itself."""
    return _scan(root)


# --- the checks ---------------------------------------------------------------------------
def duplicate_identifier_conflicts(sets):
    """K-A: one identifier, two memberships. Names the disagreement so it is actionable."""
    by_name = defaultdict(list)
    for (path, name), members in sets.items():
        by_name[name].append((path, members))
    out = []
    for name, entries in sorted(by_name.items()):
        if len(entries) < 2:
            continue
        first = entries[0][1]
        if any(m != first for _, m in entries[1:]):
            disagreement = set()
            for _, m in entries:
                disagreement |= m ^ first
            out.append((name, [p for p, _ in entries], sorted(disagreement)))
    return out


def unassigned_sets(sets, planes=PLANES):
    """K-D: the bedside test, automated. A new policy set must declare its plane."""
    return sorted({name for _, name in sets if name not in planes})


def _signatures(sets, planes, plane):
    cols = [n for _, n in sets if planes.get(n) == plane]
    universe = sorted(set().union(*[m for (_, n), m in sets.items()
                                    if planes.get(n) == plane]) if cols else set())
    return {k: frozenset(n for (_, n), m in sets.items()
                         if planes.get(n) == plane and k in m) for k in universe}


def cross_plane_collisions(sets, planes=PLANES, allowed=ALLOWED_COLLISIONS):
    """K-B: one word, two taxonomies, opposite policies."""
    homes = defaultdict(set)
    for (_, name), members in sets.items():
        for k in members:
            homes[k].add(planes.get(name, "UNASSIGNED"))
    return [(k, sorted(p)) for k, p in sorted(homes.items())
            if len(p) > 1 and k not in allowed]


def orphans(sets, planes=PLANES, plane="bus"):
    """K-C: kinds in <=1 policy set -- born silent, because a miss reads as an exclusion."""
    sig = _signatures(sets, planes, plane)
    return [(k, len(s)) for k, s in sorted(sig.items()) if len(s) <= 1]


def redundancy_candidates(sets, planes=PLANES, plane="bus"):
    """K-E, ADVISORY: identical signature within one plane. Never gates -- see module docstring."""
    groups = defaultdict(list)
    for k, s in _signatures(sets, planes, plane).items():
        groups[s].append(k)
    return [sorted(ks) for s, ks in sorted(groups.items(), key=lambda x: -len(x[1]))
            if len(ks) > 1 and s]


def resolve(kind, set_name, sets):
    """K7: TOTAL resolution. UNCLASSIFIED is a real answer; a bare False is not.

    This is the census finding in one function: today every policy is `kind in SOME_SET`, whose
    miss is indistinguishable from a deliberate exclusion. Here a miss says which it is.
    """
    for (_, name), members in sets.items():
        if name == set_name:
            return (True, "classified") if kind in members else (False, "UNCLASSIFIED")
    return (False, "UNCLASSIFIED")


def main(argv):
    report = "--report" in argv
    sets, unresolved = discover_with_unresolved(ROOT)
    fails = []

    conflicts = duplicate_identifier_conflicts(sets)
    for name, paths, disagreement in conflicts:
        fails.append(f"[same-name-different-membership] {name} in {paths} -- disagree on {disagreement}")

    for name in unassigned_sets(sets):
        fails.append(f"[unassigned-plane] {name} declares no plane -- add it to PLANES "
                     f"(bus / event / beat) so nobody has to REMEMBER to classify it")

    for kind, planes_hit in cross_plane_collisions(sets):
        fails.append(f"[cross-plane-collision] '{kind}' lives on {planes_hit} -- one word, two "
                     f"taxonomies. Name the planes or record a rationale in ALLOWED_COLLISIONS")

    orph = orphans(sets)
    total = len(_signatures(sets, PLANES, "bus"))
    classified = total - len(orph)
    print(f"kind policy coverage (bus plane): {classified}/{total} kinds in 2+ policy sets "
          f"({(100 * classified / total) if total else 0:.0f}%)")
    print(f"orphans (<=1 set, born silent): {len(orph)}")

    if unresolved:
        print(f"UNRESOLVED (reported, never skipped): {[n for _, n in unresolved]}")

    if report:
        print("\n-- orphans --")
        for k, n in orph:
            print(f"   {k:<16} {n} set(s)")
        print("\n-- redundancy CANDIDATES (advisory; this instrument has been wrong) --")
        for g in redundancy_candidates(sets):
            print(f"   {g}")
        print("\n   Redundancy licenses DEPRECATION, never a silent merge: the substrate is "
              "append-only and\n   the boundary is open (public repo, MCP door, agents minting "
              "kinds at runtime).")

    # OUTPUT CONTRACT -- not cosmetic. pre_commit._count_violations enters counting mode on a
    # line starting "VIOLATIONS", then counts lines starting "- [", and treats "PASS" as the
    # end. The first cut of this printed its FAILs BEFORE the VIOLATIONS header and without the
    # colon form, so the ratchet parsed it as ZERO -- a guard against silent omission, silently
    # reporting success. Pinned by K8; change this shape and that pin fails.
    if fails:
        print(f"\nVIOLATIONS ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        print("FAIL: the kind surface drifted. Classify or reconcile before shipping.")
        return 1
    print("\nPASS: no kind-policy drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
