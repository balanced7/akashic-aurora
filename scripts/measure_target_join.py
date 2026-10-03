"""Measure whether the touch plane and the outcome plane can join on a target key.

WHY THIS FILE EXISTS IN THE REPO RATHER THAN IN A SCRATCHPAD. The 2026-10-03 knowledge-plane
census reported "0 of 365 normalised touch target keys appear among recall:outcome's 17,733"
and shipped that number as the load-bearing input to two contracts in
`docs/THE-FILING-SCHEMA.md`. The census's own discipline was "every number with its command".
When Heimdall went to falsify the figure (`fences/filing-schema/half_a.md`, V3) the commands
were GONE -- they had been written to a session-scoped scratchpad -- so the number was
unverifiable by anyone but its author, and its author had claimed to re-verify it and had not.
He refused to re-derive it by guessing at the selectors, which was correct.

So: evidence in scratch is evidence that expires. This script is the repair. Run it and the
number is reproducible by any seat, on any day, with its definitions visible.

WHAT IT MEASURES, and the two sides are genuinely different things:

  OUTCOME keys  `recall:outcome` stream, written via `normalize_target`
                (core/recall/at_action.py) -> "p:" + normcase(abspath(path))
                                           or "c:" + lowercased collapsed command
  TOUCH keys    refs on `events:raw` rows of kind "touch", written via
                core/events/touch.py -> core/coord/target.py `_key_for`
                -> repo-relative path, or "work:<name>:<path>", each
                optionally suffixed ":<line>[:<col>]"

THE THREE QUESTIONS, because "is it zero" is the least interesting one:

  Q1  Do the two key sets intersect AT ALL, raw?
  Q2  Would a NORMALISER fix it -- i.e. do they intersect after the cosmetic folds
      (strip the p:/c: tag, casefold, unify separators, drop :line:col)?
  Q3  Would a TRANSLATION fix it -- i.e. after rewriting each absolute outcome path to
      repo-relative, which is root-dependent and is NOT a spelling fold?

Heimdall's half claims Q2 is no and Q3 is yes-for-paths-but-never-for-commands, because the
`c:` axis has no touch-side counterpart at all. Q3 and the `c:` share below are the test of
that, and they decide whether Contract A2 is salvageable or ships-but-still-zero.

Read-only: xrange replays, no cursor is advanced, nothing is written.

    py scripts/measure_target_join.py [--limit 50000] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List, Set, Tuple

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

OUTCOME_STREAM = "recall:outcome"
EVENTS_STREAM = "events:raw"


def _client():
    from core.comm.bus import Bus
    return Bus("claude")._client


def _rows(client, stream: str, limit: int) -> List[dict]:
    """Replay a stream oldest-first and JSON-decode each entry's single field. Never consumes."""
    out: List[dict] = []
    for _mid, fields in client.xrange(stream, min="-", max="+", count=limit):
        try:
            raw = next(iter(fields.values()))
            out.append(json.loads(raw.decode() if isinstance(raw, bytes) else str(raw)))
        except Exception:                                                 # noqa: BLE001
            continue
    return out


# ----------------------------------------------------------------- the folds
def strip_tag(k: str) -> str:
    """Q2's cosmetic fold: drop the p:/c: address tag the outcome side adds."""
    return k[2:] if len(k) > 2 and k[1] == ":" and k[0] in "pc" else k


def cosmetic(k: str) -> str:
    """Every spelling fold a NORMALISER could legitimately perform, and nothing more:
    tag off, separators unified, case folded, any :line[:col] suffix dropped."""
    s = strip_tag(k).replace("\\", "/").lower().rstrip("/")
    parts = s.split(":")
    while len(parts) > 1 and parts[-1].isdigit():      # drop :line and :col
        parts = parts[:-1]
    return ":".join(parts)


def to_relative(k: str, repo: str) -> str:
    """Q3's TRANSLATION, which a normaliser cannot do: an absolute path under the repo root
    becomes repo-relative. Root-dependent by construction -- that is the whole point."""
    s = cosmetic(k)
    root = repo.replace("\\", "/").lower().rstrip("/") + "/"
    return s[len(root):] if s.startswith(root) else s


def shape(k: str) -> str:
    if k.startswith("p:"):
        return "p: absolute path (outcome)"
    if k.startswith("c:"):
        return "c: command (outcome)"
    if k.startswith("work:"):
        return "work:<name>:<path> (touch)"
    if "/" in k or "\\" in k:
        return "repo-relative path (touch)"
    return "other"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="measure the touch<->outcome target join")
    ap.add_argument("--limit", type=int, default=50000)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        c = _client()
    except Exception as e:                                                # noqa: BLE001
        print("ERROR: no store client (%s: %s)" % (type(e).__name__, e))
        return 2

    outcome_rows = _rows(c, OUTCOME_STREAM, a.limit)
    event_rows = _rows(c, EVENTS_STREAM, a.limit)

    out_keys: Set[str] = {str(r.get("t") or r.get("target") or "").strip()
                          for r in outcome_rows}
    out_keys.discard("")

    touch_rows = [r for r in event_rows if str(r.get("kind") or "") == "touch"]
    touch_keys: Set[str] = set()
    for r in touch_rows:
        for ref in (r.get("refs") or []):
            s = str(ref or "").strip()
            if s:
                touch_keys.add(s)

    raw_hit = out_keys & touch_keys
    cos_out = {cosmetic(k) for k in out_keys}
    cos_tch = {cosmetic(k) for k in touch_keys}
    cos_hit = cos_out & cos_tch
    rel_out = {to_relative(k, _REPO) for k in out_keys}
    rel_hit = rel_out & cos_tch

    c_share = sum(1 for k in out_keys if k.startswith("c:"))
    p_share = sum(1 for k in out_keys if k.startswith("p:"))
    # the ceiling a translation could ever reach: path-keyed outcome rows only
    rel_hit_p = {to_relative(k, _REPO) for k in out_keys if k.startswith("p:")} & cos_tch

    rep: Dict[str, object] = {
        "outcome_rows_replayed": len(outcome_rows),
        "event_rows_replayed": len(event_rows),
        "touch_rows": len(touch_rows),
        "distinct_outcome_keys": len(out_keys),
        "distinct_touch_keys": len(touch_keys),
        "outcome_shapes": dict(Counter(shape(k) for k in out_keys)),
        "touch_shapes": dict(Counter(shape(k) for k in touch_keys)),
        "Q1_raw_intersection": len(raw_hit),
        "Q2_after_cosmetic_folds": len(cos_hit),
        "Q3_after_abspath_to_relative_translation": len(rel_hit),
        "Q3_path_keyed_only": len(rel_hit_p),
        "outcome_c_axis_rows": c_share,
        "outcome_p_axis_rows": p_share,
        "repo_root_used": _REPO,
    }
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0

    print("target join -- touch plane vs outcome plane")
    print("  replayed: %d outcome rows, %d event rows (%d touches)   limit=%d"
          % (len(outcome_rows), len(event_rows), len(touch_rows), a.limit))
    print("  distinct keys: %d outcome, %d touch" % (len(out_keys), len(touch_keys)))
    print()
    print("  OUTCOME key shapes:")
    for s, n in Counter(shape(k) for k in out_keys).most_common():
        print("     %-34s %6d" % (s, n))
    print("  TOUCH key shapes:")
    for s, n in Counter(shape(k) for k in touch_keys).most_common():
        print("     %-34s %6d" % (s, n))
    print()
    print("  Q1  raw intersection                      %6d" % len(raw_hit))
    print("  Q2  after cosmetic folds (a NORMALISER)   %6d   <- A2 as written buys this" % len(cos_hit))
    print("  Q3  after abspath->relative TRANSLATION   %6d   <- what A2 would need to do" % len(rel_hit))
    print("        of which, path-keyed outcome rows   %6d" % len(rel_hit_p))
    print()
    print("  THE CEILING ON ANY FIX: %d of %d outcome keys are c: (command-keyed) and the touch"
          % (c_share, len(out_keys)))
    print("  side mints no c: axis at all, so those rows cannot join under ANY key normalisation.")
    if len(out_keys):
        print("  Command-keyed share: %.1f%% -- unreachable until `c:` is redefined as the file"
              % (100.0 * c_share / len(out_keys)))
        print("  targets touch.py already extracts.")
    print()
    print("  Repo root used for the translation: %s" % _REPO)
    print("  (Q3 is root-dependent BY CONSTRUCTION -- that is why it is a translation and not")
    print("   a spelling fold, and why a normaliser alone cannot perform it.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
