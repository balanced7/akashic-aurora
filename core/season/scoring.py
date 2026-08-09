"""core.season.scoring -- Season 1 scoring, as a pure function over data (T165).

WHY THIS EXISTS. The rules lived only in a markdown table
(docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md section 1.6) and nothing
executed them. A rule that lives in prose drifts from whatever eventually gets built, and nobody
can tell when it has, because there is nothing to run. It also blocked the W2 queue item: four
AIxCC-derived refinements were proposed, and neither the old rules nor the new ones could be
COMPARED while both were prose.

So the policy is DATA. `v1_doc` reproduces the committed table exactly -- pinned, so a drift
between the design document and this file becomes a test failure instead of an argument.
`v2_aixcc` carries the proposals. The operator rules on a measured diff over the same inputs
rather than on a paragraph, and changing the rules is a config decision with a visible diff
rather than a code edit.

v2_aixcc IS A PROPOSAL AND IS NOT THE DEFAULT. Nothing selects it until Daniil rules; the four
changes and their rationale are documented on the policy itself so the argument travels with the
numbers.

TWO INVARIANTS THAT ARE NOT NEGOTIABLE BY POLICY, because getting them wrong corrupts the
season's EVIDENCE rather than merely mis-ranking a player:

  ORDERING IS BY BUS STREAM ID. Never by the player's `submitted_at`, which the protocol marks
  advisory. Ordering a competition by an attacker-supplied timestamp decides first-finder by
  whoever lies best about their clock.

  UNSCORED IS A THIRD STATE, distinct from zero. Zero says "we weighed this and it was worth
  nothing"; unscored says "this was never evidence". Collapsing them lets an unfalsifiable claim
  earn a rank, which is the failure mode a bounty system exists to avoid.

SCORE IS EVIDENCE, NEVER A KEY (Daniil, L4). This module deliberately imports nothing from the
trust/ACL layer, and a pin enforces that structurally, so a score cannot become an access
decision by accident. A score may make a player ELIGIBLE for a grant that a human then makes.
"""
from __future__ import annotations

#: Base multiplier by confirmed claim class. Identical in both policies -- the classes are the
#: findings the board is made of, and re-weighting them is a different argument than the one W2
#: is making.
_BASE = {
    "new-blind-spot": 6,   # improves the INSTRUMENT rather than the inventory
    "false-positive": 5,   # the list_snapshots class: a gate calling a live door dead
    "structural": 4,       # what actually drained the board (T134c, T144)
    "needs-door": 3,       # the founding defect class (declare_intent)
    "needs-caller": 2,     # real, but the fix is a program not a slice
    "dead": 1,             # weakest claim, never auto-executed
}

POLICIES = {
    "v1_doc": {
        "notes": "Exactly the committed table, section 1.6. Pinned so the design doc stays "
                 "executable.",
        "base": dict(_BASE),
        "refuted": -2,                 # flat
        "refuted_low_confidence": 0,   # honesty floor
        "unverifiable": -1,
        "already_known": 0,
        "duplicate": 0,                # later identical claims: zero, not negative
        "verify_delivered": 1,
        "verify_refuted_upheld": 3,
        "uptime_weighted": False,
        "graduated_penalty": False,
        "duplicate_decay": False,
    },
    "v2_aixcc": {
        "notes": "PROPOSED (W2), not the default. Four changes, each with a reason: "
                 "(1) UPTIME AS A SCORED AXIS -- AIxCC scores availability because a competitor "
                 "that is down contributes nothing; here a wedged seat currently scores the same "
                 "as a live player who found nothing, which is the exact ambiguity T155 was "
                 "filed about. (2) GRADUATED ACCURACY PENALTY replacing the flat -2 -- a flat "
                 "penalty is regressive: it is trivial for a high-volume player and severe for a "
                 "careful one, so it taxes care rather than inaccuracy. Scale by the player's "
                 "own refuted RATE. (3) DUPLICATE DECAY rather than a hard zero -- a hard zero "
                 "makes independent near-simultaneous discovery worthless, which suppresses "
                 "exactly the corroboration that makes a finding trustworthy. (4) VALUE "
                 "WEIGHTING -- a confirmed finding that is later FIXED is worth more than one "
                 "that sits on the board.",
        "base": dict(_BASE),
        "refuted": -2,
        "refuted_low_confidence": 0,
        "unverifiable": -1,
        "already_known": 0,
        "duplicate": 0,
        "verify_delivered": 1,
        "verify_refuted_upheld": 3,
        "uptime_weighted": True,
        "uptime_floor": 0.5,           # a seat down half the round keeps half its score
        "graduated_penalty": True,
        "graduated_penalty_max": -5,   # a player refuted most of the time pays more than -2
        "duplicate_decay": True,
        "duplicate_decay_hours": 6.0,  # an independent find within the window keeps a share
        "duplicate_decay_floor": 0.0,
    },
    "v3_confidence_priced": {
        "notes":
            "PROPOSED 2026-08-07, NOT the default -- same standing as v2_aixcc, and it "
            "carries v2's four changes plus one more. Closes the HEDGE EXPLOIT (T221), "
            "found by attacking this scorer before the season ran: a player with 3 real "
            "finds and THIRTY wrong claims, every one marked low-confidence, outscored a "
            "player with the same 3 finds and one wrong high-confidence claim -- 6 to 4 "
            "under v1_doc, 6 to 5 under v2_aixcc, and unbounded in both (300 wrong claims "
            "cost exactly what 30 do, which is nothing). "
            "CAUSE: refuted_low_confidence=0 gives an honestly-flagged wrong claim downside "
            "protection, which is right; but a CONFIRMED low-confidence claim still earns "
            "FULL points, so the protection is free. In competition terms that is a free "
            "option, and a free option is always exercised -- the dominant strategy becomes "
            "hedge everything, spray, keep the hits. "
            "TWO KNOBS, and they must move together. (1) low_confidence_credit prices the "
            "option: a hedged claim that lands earns less than one its author stood behind, "
            "so confidence becomes a real trade rather than a free put. (2) "
            "low_confidence_free_misses bounds the volume: the first few honest misses stay "
            "free -- that is the whole point of the floor and it must survive -- but the "
            "exemption stops being infinite. "
            "WHY BOTH: pricing alone still lets a hedger spray at zero downside, and "
            "bounding alone makes honest uncertainty expensive without making confidence "
            "worth anything. The failure mode to avoid is over-correcting into punishing "
            "flagged doubt, which buys FALSE CONFIDENCE -- strictly worse than noise, "
            "because noise is filterable and false confidence is not.",
        "base": dict(_BASE),
        "duplicate": 0,
        "refuted": -2,
        "refuted_low_confidence": 0,
        "unverifiable": 0,
        "already_known": 0,
        "verify_delivered": 1,
        "verify_refuted_upheld": 3,
        "uptime_weighted": True,
        "uptime_floor": 0.5,
        "graduated_penalty": True,
        "graduated_penalty_max": -5,
        "duplicate_decay": True,
        "duplicate_decay_hours": 6.0,
        "duplicate_decay_floor": 0.0,
        # T221. A hedged find is worth half a find its author stood behind.
        "low_confidence_credit": 0.5,
        # The first N honestly-flagged misses per player are free; beyond that the ordinary
        # refuted penalty applies. Set to 3 so a careful player is never taxed for doubt.
        "low_confidence_free_misses": 3,
    },
}

#: T254 -- the outcomes that constitute a TRUTH VERDICT about a claim, and therefore the only
#: universe a refuted RATE may be computed over. A named constant rather than an inline test,
#: because the set IS the policy decision: anything added here becomes free dilution for the
#: graduated penalty, and anything removed becomes free severity.
#:
#: `unverifiable` and `already-known` are excluded on purpose. "We could not determine this"
#: and "true but not novel" are both silent about whether the player was ACCURATE, and a rate
#: about accuracy must not be moved by claims that carry no accuracy signal.
ADJUDICATED_OUTCOMES = frozenset({"confirmed", "refuted"})

DEFAULT_POLICY = "v1_doc"


def _stream_sort_key(claim: dict):
    """Redis stream ids sort as (ms, seq) numerically, NOT as strings.

    '1785850000002-0' vs '1785850000010-0' compares correctly either way, but
    '...-2' vs '...-10' does not: lexically '2' > '10'. First-finder is decided here, so a
    string sort would hand the win to whoever submitted tenth within the same millisecond.
    """
    raw = str(claim.get("stream_id") or "")
    try:
        ms, _, seq = raw.partition("-")
        return (0, int(ms), int(seq or 0))
    except (TypeError, ValueError):
        return (1, 0, 0), raw          # unparseable ids sort last, deterministically


def _has_evidence(claim: dict) -> bool:
    return any(str(e).strip() for e in (claim.get("evidence") or []))


def score_round(claims, verifications=None, policy: str = DEFAULT_POLICY,
                uptime=None, fixed_keys=None) -> dict:
    """Score one round. Pure: no IO, no clock, no randomness, no authority lookups.

    `claims`        [{player, dedupe_key, claim_class, outcome, confidence, stream_id, evidence}]
    `verifications` [{player, verdict, upheld}]
    `uptime`        {player: 0.0..1.0} -- only read by a policy with uptime_weighted
    `fixed_keys`    set of dedupe_keys whose finding was actually FIXED (value weighting)

    Returns {policy, claims: [...per-claim detail...], totals: {player: points}, unscored: n}.
    Per-claim detail is returned so a scoreboard can SHOW ITS WORKING; a bare total that nobody
    can audit is how a scoring dispute becomes unresolvable.
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown policy '{policy}' (known: {sorted(POLICIES)})")
    P = POLICIES[policy]
    claims = list(claims or [])
    uptime = uptime or {}
    fixed_keys = set(fixed_keys or ())

    # Deterministic order, by stream id. Everything downstream depends on this being the ONLY
    # ordering input -- see the module docstring on why player clocks are not eligible.
    ordered = sorted(claims, key=_stream_sort_key)

    # refuted RATE per player, computed over the whole round before any scoring, so the graduated
    # penalty does not depend on where in the round a claim happens to sit.
    # T254: the denominator is the ADJUDICATED set, not everything submitted.
    #
    # It used to count every claim, and the graduated penalty is rate = refuted/seen -- so
    # unadjudicated volume bought immunity. Measured on both graduated policies: two players
    # refuted exactly 3 times scored -15 (only those 3 claims) versus 0 (padded with 60
    # unadjudicated ones), because 3/63 x -5 rounds away. The padding did not even have to be
    # valid; an undefined outcome string worked, while score_round reported `unscored: 60` in
    # the same breath -- it knew it had not scored them and counted them anyway.
    #
    # This composes with the low-confidence hedge rather than being covered by it: one attacks
    # the numerator, this one the denominator of the same rate. And it is silently adversarial,
    # because outrunning the reviewers lowers your own penalty and the cheapest way to outrun a
    # reviewer is to submit noise.
    #
    # `unverifiable` is deliberately NOT adjudicated: "we could not determine this" is not
    # evidence about a player's accuracy in either direction, so it belongs in neither half.
    seen, refuted = {}, {}
    for c in ordered:
        p = c.get("player")
        if c.get("outcome") not in ADJUDICATED_OUTCOMES:
            continue
        seen[p] = seen.get(p, 0) + 1
        if c.get("outcome") == "refuted":
            refuted[p] = refuted.get(p, 0) + 1

    first_seen = {}
    # T221: per-player consumption of the free-miss budget, counted in the round's own
    # deterministic order (`ordered`) so which specific misses are free is reproducible and
    # cannot depend on submission timing within a millisecond.
    low_conf_misses: dict = {}
    out, totals = [], {}

    for c in ordered:
        player = c.get("player")
        key = c.get("dedupe_key")
        outcome = str(c.get("outcome") or "").lower()
        detail = {"player": player, "dedupe_key": key, "outcome": outcome,
                  "claim_class": c.get("claim_class"), "first_finder": False,
                  "scored": True, "points": 0, "reason": ""}

        # NO RECEIPTS, NO SCORE -- checked before anything else, including before first-finder,
        # so an evidence-free claim cannot even reserve a dedupe key it did not earn.
        if not _has_evidence(c):
            detail.update(scored=False, points=0,
                          reason="unscored: no resolvable evidence lines")
            out.append(detail)
            continue

        is_first = key not in first_seen
        if is_first:
            first_seen[key] = c
        detail["first_finder"] = is_first

        is_low_conf = str(c.get("confidence") or "").lower() == "low"

        if outcome == "confirmed":
            pts = P["base"].get(str(c.get("claim_class")), 0)
            # T221: price the hedge. A confirmed low-confidence claim used to earn FULL
            # points while its wrong twin cost nothing -- downside protection with no upside
            # cost, i.e. a free option, and a free option is always exercised. Absent from a
            # policy this is 1.0, so v1_doc and v2_aixcc are byte-identical to before.
            credit = float(P.get("low_confidence_credit", 1.0))
            if is_low_conf and credit != 1.0:
                pts = int(round(pts * credit))
                detail["reason"] = (detail["reason"] + "; " if detail["reason"] else "") + \
                    f"low-confidence credit x{credit:g}"
            if not is_first:
                if P["duplicate_decay"]:
                    # An independent corroborating find keeps a SHARE. A hard zero makes
                    # near-simultaneous independent discovery worthless, which suppresses exactly
                    # the corroboration that makes a finding trustworthy.
                    lag = _lag_hours(first_seen[key], c)
                    window = float(P["duplicate_decay_hours"]) or 1.0
                    frac = max(float(P["duplicate_decay_floor"]), 1.0 - (lag / window))
                    pts = int(round(pts * frac))
                    detail["reason"] = f"duplicate, decayed (lag {lag:.2f}h)"
                else:
                    pts = P["duplicate"]
                    detail["reason"] = "duplicate: first-finder only"
            if P["uptime_weighted"]:
                u = float(uptime.get(player, 1.0))
                floor = float(P.get("uptime_floor", 0.0))
                pts = int(round(pts * max(floor, min(1.0, u))))
                detail["reason"] = (detail["reason"] + "; " if detail["reason"] else "") + \
                    f"uptime x{max(floor, min(1.0, u)):.2f}"
            if key in fixed_keys:
                pts *= 2
                detail["reason"] = (detail["reason"] + "; " if detail["reason"] else "") + \
                    "value-weighted: finding was fixed"
            detail["points"] = pts

        elif outcome == "refuted":
            if is_low_conf:
                # T221: the floor is a KINDNESS FOR HONEST DOUBT, not an exemption from
                # being wrong. Unbounded, it let a hedger spray thirty free wrong claims and
                # win. Bounded, the first N misses stay free -- which is the entire reason
                # this branch exists and must survive -- and the ordinary penalty resumes
                # after. Absent from a policy the budget is infinite, so v1_doc and
                # v2_aixcc keep their exact prior behaviour.
                budget = P.get("low_confidence_free_misses")
                used = low_conf_misses.get(player, 0)
                low_conf_misses[player] = used + 1
                if budget is None or used < int(budget):
                    detail.update(points=P["refuted_low_confidence"],
                                  reason="honest low-confidence report: floored at 0")
                else:
                    detail.update(points=P["refuted"],
                                  reason=f"low-confidence, but past the free-miss budget "
                                         f"({budget}): ordinary penalty applies")
            elif P["graduated_penalty"]:
                rate = refuted.get(player, 0) / max(1, seen.get(player, 1))
                worst = float(P["graduated_penalty_max"])
                detail.update(points=int(round(worst * rate)),
                              reason=f"graduated penalty (refuted rate {rate:.2f})")
            else:
                detail.update(points=P["refuted"], reason="refuted (flat)")

        elif outcome == "unverifiable":
            detail.update(points=P["unverifiable"], reason="evidence did not resolve")
        elif outcome == "already-known":
            detail.update(points=P["already_known"],
                          reason="already known: rediscovery is honest work, never negative")
        else:
            detail.update(scored=False, points=0, reason=f"unscored: unknown outcome {outcome!r}")

        out.append(detail)

    for d in out:
        if d["scored"]:
            totals[d["player"]] = totals.get(d["player"], 0) + d["points"]

    for v in (verifications or []):
        p = v.get("player")
        pts = P["verify_delivered"]
        if str(v.get("verdict") or "").lower() == "refuted" and v.get("upheld"):
            pts = P["verify_refuted_upheld"]
        totals[p] = totals.get(p, 0) + pts

    return {"policy": policy, "claims": out, "totals": totals,
            "unscored": sum(1 for d in out if not d["scored"])}


def _lag_hours(first: dict, later: dict) -> float:
    """Hours between two claims, from their STREAM IDS (ms-prefixed), never player clocks."""
    def ms(c):
        try:
            return int(str(c.get("stream_id") or "0").partition("-")[0])
        except (TypeError, ValueError):
            return 0
    return max(0.0, (ms(later) - ms(first)) / 3_600_000.0)


def compare(claims, verifications=None, **kw) -> dict:
    """Both policies over the same inputs -- the artifact an operator rules on.

    The point of W2 is a DECISION, and a decision needs a diff on real data rather than two
    paragraphs that both sound reasonable.
    """
    a = score_round(claims, verifications, policy="v1_doc", **kw)
    b = score_round(claims, verifications, policy="v2_aixcc", **kw)
    players = sorted(set(a["totals"]) | set(b["totals"]))
    return {
        "v1_doc": a["totals"], "v2_aixcc": b["totals"],
        "delta": {p: b["totals"].get(p, 0) - a["totals"].get(p, 0) for p in players},
        "rank_v1": [p for p, _ in sorted(a["totals"].items(), key=lambda kv: -kv[1])],
        "rank_v2": [p for p, _ in sorted(b["totals"].items(), key=lambda kv: -kv[1])],
    }
