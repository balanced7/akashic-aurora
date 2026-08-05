"""The canary oracle -- the control that separates "the system improved" from "the attackers tired".

WHY THIS EXISTS. kimi's convergence objection (adopted 2026-08-04): a pool of same-checkpoint
players cannot certify its own completeness. Role hats decorrelate the PROMPTS; ensemble error
covariance lives in the INDUCTION, and a hat is data, not architecture. So a declining find-rate
has two causes the board burn-down cannot separate -- the system ran out of holes, or the pool ran
out of ideas -- and they are observationally identical on that metric. A5 is the live proof: a
fourth gate hole found AFTER a three-round streak, by a lens the streak did not contain.

THE INSTRUMENT. Ground truth the players did not generate and cannot see: defects PLANTED by the
adjudicator, in a SHADOW copy, with answers sealed before the round. Because the key is drawn by
the adjudicator, the pool's correlation structure is irrelevant to whether the canaries are there
-- they are there by construction. A tired pool stops catching planted canaries too, so the
catch-rate falls WITH the find-rate and exhaustion cannot masquerade as completeness.

THREE CLASSES, and the distinction is the whole point:
  catchable     the T143 compound-statement shape, which the CURRENT gate should find.
                Measures DETECTOR HEALTH. This is the only number that may go on a headline.
  undetectable  the A5 string-dispatch shape, which the gate structurally CANNOT see.
                Measures COVERAGE HONESTY -- does the season report the class it cannot see, or
                does it call the board clean? Never scored as a miss: punishing the pool for the
                gate's blind spot is the dishonesty this module exists to prevent.
  bait          a genuinely LIVE function planted to look dead. Measures PRECISION.

TWO SAFETY PROPERTIES, both structural rather than procedural:

  THE LIVE TREE IS NEVER WRITTEN. `plant()` refuses any path inside the real repository. The
  operator's standing scope for the season is live store READ-ONLY, and a planting bug that wrote
  into the working tree would be the worst thing this module could do.

  THE KEY NEVER ENTERS A RETRIEVAL PLANE. Learned the hard way (lesson
  `answer_keys_never_enter_retrieval_planes`, 2026-08-01): an answer key was sealed by ORDERING
  inside a document and then adopted into the library, so lookback indexed every byte and a cold
  runner asking the trap question got the battery itself as its top source. The trap identities
  ALSO leaked through the pre-registration COMMIT MESSAGE, and commit messages are a retrieval
  layer visible from any worktree through shared refs. So: `seal()` refuses to write anywhere
  git tracks, the key rides untracked, and only its sha256 belongs in a commit as the integrity
  receipt. Commit the QUESTIONS and the gates; never the answers.

HONEST LIMITATION, stated because a silent one would be worse. Players can read this file. The
planted shapes are drawn from a pool and varied by seed, so grepping one signature does not find
them all -- but an adversary who reads this module and greps the shadow tree for its templates can
beat the oracle without doing any analysis. The mitigation is that this module must NOT be present
in the tree the players are given (`exclude_self()` below), and the seed stays sealed. Against a
player doing ordinary analysis the oracle is sound; against one attacking the oracle itself it is
not, and that is a Red Team bounty in its own right rather than a property to claim.
"""
import hashlib
import json
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Shapes are varied so a single grep signature cannot harvest a whole round. Each entry is a
# template plus the verdict the gate SHOULD return for it.
# T186: EVERY TEMPLATE DOCSTRING IS NEUTRAL AND IDENTICAL, and that is load-bearing.
# They used to describe their own class -- "Registered in a table that nothing ever invokes",
# "Fan-out path -- unreachable", "Looks dead; is called below". Measured 2026-08-05: the first
# LLM player's correct verdict on an undetectable canary cited "The comment states the
# registration table is never invoked". It quoted the fixture. Stripping the docstrings and
# re-asking still gave 7/7 with structural reasoning, so that result was not manufactured -- but
# a weaker player WOULD have been flattered, and a harness that grades on label-reading measures
# reading, not analysis. The class must be inferable ONLY from code structure.
#
# COMPARABILITY: catch_rate figures recorded BEFORE this change were taken on an easier board.
# Do not compare across this line.
_CATCHABLE = [
    ('if {flag}:\n    def {name}():\n        """Helper."""\n        return None\n',
     'compound-statement def (T143 shape)'),
    ('try:\n    import json as _j\n\n    def {name}():\n        """Helper."""\n        return _j\nexcept ImportError:\n    pass\n',
     'try-block def (T143 shape)'),
    ('for _ in range(1):\n    def {name}():\n        """Helper."""\n        return 0\n',
     'loop-scoped def (T143 shape)'),
]
_UNDETECTABLE = [
    ('def {name}():\n    """Helper."""\n    return 1\n\n\n_DISPATCH = {{"{name}": {name}}}\n',
     'string-dispatch only (A5 shape)'),
    # CALIBRATED TWICE, 2026-08-04, and the second failure taught the real lesson: I had the
    # detector's semantics INVERTED. This gate does not ask "is the function reachable"; it asks
    # "does any production path NAME it". So a runtime-assembled name -- my first attempt at
    # invisibility -- is MORE visible to it, not less: nothing names the function, so the gate
    # flags it correctly and my "undetectable" label was the error, twice.
    #
    # A genuine A5-class defect is the opposite shape: code that is DEAD but carries a FALSE
    # WIRING SIGNAL, so the gate sees a mention and waves it through. Both templates here do
    # that -- a dispatch table and a handler list, each naming the function, neither ever
    # invoked. That is the class the season must report it cannot see.
    ('def {name}():\n    """Helper."""\n    return 2\n\n\n'
     '_HANDLERS = [{name}]\n',
     'registered-never-invoked (A5 shape)'),
]
_BAIT = [
    ('def {name}():\n    """Helper."""\n    return 3\n\n\n_USED = {name}()\n',
     'live function that reads dead'),
]


def _inside_repo(path: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), ROOT]) == ROOT
    except ValueError:
        return False


#: Files the wiring gate actually examines. A "catchable" canary planted anywhere else is a
#: MISLABEL, not a miss -- discovered on the first calibration run, where 3 of 3 catchable
#: canaries landed in tests/ and docs/_archive/ and the gate correctly ignored all of them.
#:
#: T159 is the SECOND time that same defect landed, one level deeper, and the reason it recurred
#: is that the first fix RE-IMPLEMENTED the detector's selector here by walking core/. That copy
#: was right about `core_universe` (151 modules) and wrong about the gate, which filters once more
#: downstream to `cand` (134) -- reachable, minus the module-level EXCEPTIONS backlog. The 17
#: modules in between are territory where a MISS IS CORRECT, because those modules are already
#: reported at module granularity; a canary landing there was scored as detector failure and
#: published 0.67 detector health for a detector that was working.
#:
#: So the rule is now ASK, NEVER RE-IMPLEMENT. A copy of a selector drifts the moment either side
#: moves, and both times it drifted it did so silently and in the direction that flatters nobody.
def _resolve_universe(shadow_root: str):
    """-> (paths, source). Ask the SHADOW'S OWN detector what it examines.

    The shadow is a worktree and may be a DIFFERENT COMMIT than this process is running -- with a
    different EXCEPTIONS list and a different import graph. Asking it across a process boundary is
    the only answer that is true of the tree the canaries actually live in.

    Falls back to the structural walk only when the shadow has no detector to ask (a synthetic
    fixture tree). The fallback is RECORDED, never silent: a round scored against a fallback
    universe is measuring something other than the gate, and the manifest has to say so.
    """
    checker = os.path.join(shadow_root, "scripts", "checkers", "check_wiring.py")
    if os.path.isfile(checker):
        detail = ""
        try:
            r = subprocess.run(
                [sys.executable, os.path.join("scripts", "checkers", "check_wiring.py"),
                 "--candidates"],
                cwd=shadow_root, capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and r.stdout.strip():
                rels = json.loads(r.stdout)
                if rels:
                    return sorted(os.path.join(shadow_root, p.replace("/", os.sep))
                                  for p in rels), "detector"
                detail = "the detector answered with an EMPTY candidate list"
            else:
                detail = (f"--candidates exited {r.returncode} and did not print JSON "
                          f"(first line: {(r.stdout or r.stderr).strip().splitlines()[:1]})")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            detail = f"{type(exc).__name__}: {exc}"

        # A detector EXISTS here and could not answer. Falling back silently is precisely the
        # failure this ticket is made of: the round would be scored against a universe that is
        # not the gate's, and the number would look like a measurement. The usual cause is
        # VERSION SKEW -- a shadow pinned to a commit older than the --candidates door.
        raise RuntimeError(
            f"{checker} exists but could not report its field of view -- {detail}. Refusing to "
            f"guess: a canary planted outside the gate's scope is scored as a detector failure, "
            f"which is how T158 published 0.67 health for a healthy detector (twice). If this "
            f"shadow predates the --candidates door, either rebuild it from a commit that has "
            f"the door or pass targets= explicitly and own the choice.")

    out = []
    core = os.path.join(shadow_root, "core")
    for base, dirs, files in os.walk(core):
        dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
        out += [os.path.join(base, f) for f in files
                if f.endswith(".py") and f != "__init__.py"]
    return sorted(out), "structural-fallback"


def _gate_universe(shadow_root: str):
    """The plantable target set: what the shadow's own wiring gate actually examines."""
    return _resolve_universe(shadow_root)[0]


def plant(shadow_root: str, k: int = 6, seed: int = 0, targets=None) -> dict:
    """Plant k canaries into a SHADOW tree. Returns the manifest (the answer key -- guard it).

    Refuses to write inside the real repository, by construction rather than by care.

    `targets` defaults to the DETECTOR'S OWN SCAN UNIVERSE, and that default is the whole
    difference between an instrument and a decoration. The first calibration run planted into
    whatever .py files existed -- archive copies, test files, package __init__ -- and the gate
    passed clean with 9 canaries in the tree. Not because the gate is blind: because the canaries
    were never in its scope. A canary outside the detector's field of view measures nothing, and
    scoring it as a miss would have reported 0% detector health for a healthy detector.

    T159: that default is now RESOLVED BY ASKING the shadow's own detector, not by re-deriving it
    here. The re-derivation was itself the second occurrence of the same bug. The manifest records
    which universe was used and how big it was, because the tempting fix for a bad detector-health
    number is to quietly narrow what gets measured, and that must not be doable quietly.
    """
    shadow_root = os.path.abspath(shadow_root)
    if _inside_repo(shadow_root):
        raise ValueError(
            f"refusing to plant inside the live repository ({shadow_root}). Canaries go in a "
            f"shadow copy (git worktree); the live tree is READ-ONLY for the season.")
    if not os.path.isdir(shadow_root):
        raise ValueError(f"shadow root does not exist: {shadow_root}")

    if targets is None:
        targets, universe_source = _resolve_universe(shadow_root)
    else:
        universe_source = "caller-supplied"
    targets = [t if os.path.isabs(t) else os.path.join(shadow_root, t) for t in targets]
    targets = sorted(t for t in targets if os.path.isfile(t))
    if not targets:
        raise ValueError(
            f"no plantable target files under {shadow_root}. With the default selector this means "
            f"core/ is missing -- a canary outside the detector's scan universe measures nothing.")

    rng = random.Random(seed)
    plan = ([("catchable", _CATCHABLE)] * ((k + 2) // 3)
            + [("undetectable", _UNDETECTABLE)] * ((k + 1) // 3)
            + [("bait", _BAIT)] * (k // 3))[:k]

    canaries = []
    for i, (cls, pool) in enumerate(plan):
        tmpl, shape = pool[rng.randrange(len(pool))]
        name = f"{rng.choice(['route', 'emit', 'resolve', 'collect', 'apply'])}_{rng.randrange(16**6):06x}"
        target = targets[rng.randrange(len(targets))]
        cut = len(name) // 2
        body = tmpl.format(name=name, flag=f"_FLAG_{rng.randrange(16**4):04x}",
                           half_a=name[:cut], half_b=name[cut:])
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n\n" + body)
        canaries.append({
            "id": f"c{i:02d}_{hashlib.sha256(f'{seed}:{i}:{name}'.encode()).hexdigest()[:8]}",
            "cls": cls, "shape": shape, "name": name,
            "file": os.path.relpath(target, shadow_root).replace("\\", "/"),
        })
    return {"seed": seed, "k": k, "shadow_root": shadow_root, "canaries": canaries,
            # T159 receipt: WHICH universe this round was measured against, and how big it was.
            # Detector health is only interpretable next to the field of view it was scored over
            # -- narrowing the universe raises the number without improving anything.
            "universe": {"source": universe_source, "size": len(targets)}}


def exclude_self(shadow_root: str) -> bool:
    """Remove THIS module from a shadow tree before players see it.

    A player who reads the oracle can grep its templates instead of analysing anything. Removing
    it is not a substitute for the seed staying sealed -- it is the cheap half of the defence.
    """
    p = os.path.join(shadow_root, "scripts", "canary_oracle.py")
    try:
        os.remove(p)
        return True
    except OSError:
        return False


def _digest(manifest: dict) -> str:
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def seal(manifest: dict, path: str) -> str:
    """Write the answer key and return its sha256 -- the ONLY part that may enter a commit.

    Refuses to write anywhere git tracks. The key is the instrument's secret; a tracked key is
    indexed, rendered, and searchable, and a single mention anywhere greppable burns the round.
    """
    path = os.path.abspath(path)
    if _inside_repo(path):
        raise ValueError(
            f"refusing to seal inside the repository ({path}). An answer key must not enter any "
            f"retrieval plane -- not the library, not notes, not a commit message. Keep it "
            f"untracked and commit only the sha256 as the integrity receipt.")
    digest = _digest(manifest)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sha256": digest, "manifest": manifest}, f, sort_keys=True)
    return digest


def verify_seal(path: str) -> bool:
    """True if the key on disk still matches the digest it was sealed with."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        return _digest(doc["manifest"]) == doc["sha256"]
    except Exception:
        return False


def score(manifest: dict, claims) -> dict:
    """Confusion matrix by class, plus the one honest headline number.

    `claims` are canary ids the pool reported. Two rules carry the honesty:
      - catch_rate counts CATCHABLE canaries only; an undetectable canary missed is the gate's
        blind spot, not the pool's failure.
      - a claimed UNDETECTABLE canary VOIDS the round (kimi's K0 tripwire): either the key leaked
        or the instrument is being gamed, and the round's evidence is worthless either way.
    """
    claimed = set(claims or [])
    by_class = {}
    for c in manifest.get("canaries", []):
        b = by_class.setdefault(c["cls"], {"caught": 0, "missed": 0, "total": 0, "ids": []})
        b["total"] += 1
        b["ids"].append(c["id"])
        if c["id"] in claimed:
            b["caught"] += 1
        else:
            b["missed"] += 1
    for cls in ("catchable", "undetectable", "bait"):
        by_class.setdefault(cls, {"caught": 0, "missed": 0, "total": 0, "ids": []})

    undetectable_hits = [c["id"] for c in manifest.get("canaries", [])
                         if c["cls"] == "undetectable" and c["id"] in claimed]
    cat = by_class["catchable"]
    catch_rate = (cat["caught"] / cat["total"]) if cat["total"] else None

    known = {c["id"] for c in manifest.get("canaries", [])}
    return {
        "by_class": by_class,
        "catch_rate": catch_rate,                      # DETECTOR HEALTH -- the only headline
        "coverage_honesty": (by_class["undetectable"]["missed"]
                             / by_class["undetectable"]["total"]) if by_class["undetectable"]["total"] else None,
        "false_positives": by_class["bait"]["caught"],  # bait "caught" is a PRECISION failure
        "unknown_claims": sorted(claimed - known),      # claims naming no canary at all
        "voided": bool(undetectable_hits),
        "void_reason": (f"claimed undetectable canary/canaries {undetectable_hits} -- the key "
                        f"leaked or the instrument is being gamed; this round's evidence is void"
                        if undetectable_hits else ""),
    }
