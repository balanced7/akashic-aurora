"""round_archive -- a round's evidence outlives the round, so a scorer can be replaced (T190).

WHY. Three Season 1 rounds costing $1.069 printed their results and discarded them. When
codex_root proposed "replay the existing three rounds through scoreboard v2 before buying another
model call", the answer was that it cannot be done: the surviving temp directories hold `key.json`
and `shadow`, and no claims. A round produced evidence and threw it away -- this arc's invariant,
applied to the round itself.

WHAT IT UNBLOCKS. A scoreboard rewrite needs an old-score/new-score comparison on IDENTICAL
claims. Without archived rounds the next live round becomes the new scorer's test fixture, which
is an instrument validated on the only data it will ever be judged by.

WHERE IT LIVES, AND WHY THAT IS NOT A PREFERENCE. A round record must carry the claims, and claims
carry `dedupe_key: canary::<name>`. A committed record would therefore publish name->class for
that seed and let anyone replaying it cheat. canary_oracle.seal already refuses to write anywhere
git tracks; this inherits the same rule by construction rather than by care. Because the record
already sits on the key's side of that boundary, it may also carry the manifest -- which is what
makes replay self-contained instead of depending on a temp directory nobody cleaned up.

The repository gets summaries and digests. Never the record.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Run as a script, `scripts` is not an importable package and the default scorer import fails --
# so the module worked under pytest and broke at its own CLI door. Found by dogfooding, not tests.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Default home for round records: outside the repository, stable (not a temp dir that a
#: cleanup sweep will take away with the evidence still in it).
DEFAULT_ROUND_DIR = os.environ.get(
    "AKASHIC_ROUND_DIR", os.path.join(os.path.expanduser("~"), ".akashic", "rounds"))


def _tracked_by_git(path: str) -> bool:
    """True when `path` lies inside a git working tree. Asked of git, not re-derived.

    Re-deriving 'is this the repo' from string prefixes is how the canary planter got its
    universe wrong twice; ask the tool that owns the answer.
    """
    target = os.path.abspath(path)
    probe = target
    while not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            return False
        probe = parent
    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=probe,
                           capture_output=True, text=True, timeout=20)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        # Absence of an answer is not a permission. If git cannot be consulted, fall back to
        # the one thing that is certainly tracked.
        return os.path.abspath(ROOT) == os.path.commonpath([os.path.abspath(ROOT), target])


def round_id(record: dict) -> str:
    seed = record.get("seed", "noseed")
    player = record.get("player_name", "unknown")
    # Colons are legal in an ISO timestamp and illegal in a Windows filename, so the stamp is
    # sanitised rather than trusted. The record keeps its real ended_at; only the NAME is safe.
    stamp = str(record.get("ended_at") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    stamp = "".join(ch if (ch.isalnum() or ch in "-_") else "" for ch in stamp)
    digest = hashlib.sha256(
        json.dumps(record.get("claims", []), sort_keys=True, default=str).encode()
    ).hexdigest()[:8]
    return f"{stamp}_seed{seed}_{player}_{digest}"


def archive_round(record: dict, *, round_dir: str = None) -> str:
    """Write one round record outside git and return its path. Refuses a tracked directory."""
    target_dir = os.path.abspath(round_dir or DEFAULT_ROUND_DIR)
    if _tracked_by_git(target_dir):
        raise ValueError(
            f"refusing to archive a round inside a git working tree ({target_dir}). Claims carry "
            f"canary NAMES, so a committed record leaks name->class for this seed and lets a "
            f"replay of it cheat. Round records live beside the sealed key, outside the repo; "
            f"commit summaries and digests instead.")
    if "claims" not in record:
        raise ValueError("a round record without `claims` cannot be replayed -- refusing to "
                         "archive a record that would read as an empty clean round")

    record = dict(record)
    record.setdefault("ended_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    record["schema"] = "akashic.round/1"
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, round_id(record) + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, default=str)
    return path


def load_round(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        record = json.load(fh)
    if "claims" not in record:
        raise ValueError(
            f"{path} records no `claims`. A round with no claims RECORDED and a round where the "
            f"player found nothing are different facts, and replaying the first as an empty clean "
            f"round is the defect this archive exists to prevent.")
    if not record.get("manifest", {}).get("canaries"):
        raise ValueError(f"{path} records no manifest -- there is nothing to score the claims "
                         f"against, so any verdict would be manufactured")
    return record


def replay_round(path: str, *, score_fn=None) -> dict:
    """Re-score a stored round. NO model call, by construction -- this reads a file.

    `score_fn(manifest, claimed_ids)` defaults to the shipped oracle, so a replay reproduces the
    original verdict. Passing a different one is the whole point: a scoreboard replacement gets
    exercised on real claims before it is ever pointed at a live round.
    """
    record = load_round(path)
    claimed = {c.get("_canary_id") for c in record["claims"] if c.get("_canary_id")}

    if score_fn is None:
        from scripts import canary_oracle as C
        score_fn = C.score

    return {
        "path": path,
        "seed": record.get("seed"),
        "player_name": record.get("player_name"),
        "claims": len(record["claims"]),
        "claimed_ids": sorted(claimed),
        "adjudication": score_fn(record["manifest"], claimed),
        "original_adjudication": record.get("adjudication"),
        # Stated, not implied: a replay that quietly spent money would defeat the purpose.
        "model_calls": 0,
    }


def list_rounds(round_dir: str = None):
    d = os.path.abspath(round_dir or DEFAULT_ROUND_DIR)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="list or replay archived Season rounds")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--replay", default=None, help="path to one round record")
    a = ap.parse_args()
    if a.replay:
        print(json.dumps(replay_round(a.replay), indent=2, default=str))
    else:
        rounds = list_rounds(a.dir)
        print(f"{len(rounds)} archived round(s) in {a.dir or DEFAULT_ROUND_DIR}")
        for p in rounds:
            print("  " + os.path.basename(p))
