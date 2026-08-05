"""Matched DeepSeek calibration: redundant replication versus positional sharding (T195).

Both arms spend four stateless calls inside ONE concurrent fan.  Replication asks the same anchor
packet four times; positional sharding asks that byte-identical anchor once and sends calls 2-4
across disjoint sibling packets.  The field is 32 sealed canaries, eight per packet, so every
candidate has adjudicator-owned ground truth while the model sees only opaque item handles and
neutral code windows.

This is an equal call-count/token-ceiling calibration, not a claim of equal information: breadth
sharding deliberately buys more unique territory with the same generation budget.  Repetition
can still win by recovering anchor misses or improving precision.  The primary receipt therefore
keeps total findings, assigned recall, conservative precision, judgment coverage, and the
marginal contribution of calls 2-4 separate.

The verbatim prompts, answers, hidden manifest, parse anomalies, and usage live outside git beside
the sealed key.  The repository receives only aggregate receipts; publishing the mapping would
burn the round.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SYSTEM = (
    "You are one stateless code-judgment leaf in a controlled audit. For every assigned item, "
    "decide DEAD (the function is never invoked) or LIVE (it is invoked). Use only the shown "
    "window. A bare registration, list, or dictionary entry is not an invocation; an expression "
    "with call parentheses is. When the window is insufficient, omit the item rather than guess. "
    "Return one JSON object per line and no prose."
)

_PROMPT_HEAD = """Judge all {n} independent Python items below.

Return exactly one JSON object per item you can establish:
{{"item":"<opaque item handle>","verdict":"DEAD" or "LIVE","why":"<12 words max>"}}

An omitted item is recorded as UNJUDGED, not LIVE. Do not infer relationships between items.
"""

DEFAULT_ARCHIVE_DIR = os.environ.get(
    "AKASHIC_CALIBRATION_DIR", os.path.join(os.path.expanduser("~"), ".akashic", "calibrations"))


def relative_gap(a: int, b: int) -> float:
    """Symmetric relative gap; two empty inputs are exactly matched."""
    top = max(abs(a), abs(b))
    return (abs(a - b) / top) if top else 0.0


def _normalise_window(value: str, chars: int) -> str:
    if chars <= 0:
        raise ValueError("snippet_chars must be positive")
    return str(value or "")[:chars].ljust(chars)


def make_packets(candidates, manifest: dict, *, packet_count: int = 4,
                 packet_size: int = 8, snippet_chars: int = 1200,
                 seed: int = 20260805):
    """Build balanced, disjoint packets while keeping manifest facts host-side.

    The planted set must fill the field exactly.  Quietly padding with ordinary repository
    candidates would turn their unknown truth into false-positive labels; quietly dropping a
    canary would make the assigned denominator gameable.  Both are refused.
    """
    if packet_count <= 0 or packet_size <= 0:
        raise ValueError("packet_count and packet_size must be positive")
    canaries = list(manifest.get("canaries", []))
    expected = packet_count * packet_size
    if len(canaries) != expected:
        raise ValueError(
            f"matched field needs exactly {expected} canaries; manifest has {len(canaries)}")

    by_name = {}
    for candidate in candidates or []:
        by_name.setdefault(candidate.get("name"), []).append(candidate)

    rng = random.Random(seed)
    ordered = []
    known_classes = ("catchable", "undetectable", "bait")
    extra_classes = sorted({c.get("cls") for c in canaries} - set(known_classes))
    for cls in known_classes + tuple(extra_classes):
        group = [c for c in canaries if c.get("cls") == cls]
        rng.shuffle(group)
        ordered.extend(group)

    packets = [[] for _ in range(packet_count)]
    # Keep the round-robin cursor continuous across classes.  With 11/11/10 class counts this
    # yields 8 items in every packet and rotates which packet receives each class's remainder.
    for index, canary in enumerate(ordered):
        matches = by_name.get(canary.get("name"), [])
        if len(matches) != 1:
            raise ValueError(
                f"canary {canary.get('id')} name {canary.get('name')!r} maps to "
                f"{len(matches)} candidates; the assigned window is ambiguous")
        candidate = matches[0]
        packets[index % packet_count].append({
            "name": str(candidate["name"]),
            "file": str(candidate.get("file", "")),
            "line": int(candidate.get("line", 0)),
            "window": _normalise_window(candidate.get("window", ""), snippet_chars),
            "_canary_id": str(canary["id"]),
            "_cls": str(canary["cls"]),
        })

    if any(len(packet) != packet_size for packet in packets):
        raise ValueError(f"packet construction did not produce {packet_size} items per packet")

    for packet_index, packet in enumerate(packets):
        rng.shuffle(packet)
        for item_index, item in enumerate(packet):
            opaque = hashlib.sha256(
                f"{seed}:{packet_index}:{item_index}:{item['name']}".encode()).hexdigest()[:6]
            item["item_id"] = f"item_{packet_index}{item_index}_{opaque}"
    return packets


def render_packet(packet) -> str:
    """Render only model-visible fields.  Hidden ids/classes never cross this boundary."""
    parts = [_PROMPT_HEAD.format(n=len(packet))]
    for item in packet:
        parts.append(
            f"### {item['item_id']}\n"
            f"function: {item['name']}\n"
            f"source: {item['file']}:{item['line']}\n"
            f"```python\n{item['window']}\n```\n")
    return "\n".join(parts)


def build_call_plan(packets):
    """Interleave arms: R0,S0,R1,S1... so provider time is shared."""
    if not packets:
        raise ValueError("at least one packet is required")
    prompts = [render_packet(packet) for packet in packets]
    plan = []
    for position in range(len(packets)):
        plan.append({
            "arm": "replication", "position": position, "packet_index": 0,
            "packet": packets[0], "prompt": prompts[0],
        })
        plan.append({
            "arm": "sharding", "position": position, "packet_index": position,
            "packet": packets[position], "prompt": prompts[position],
        })
    return plan


def parse_answer(answer, packet) -> dict:
    """Parse JSON lines without coercing silence, conflict, or an unknown handle into LIVE."""
    item_map = {item["item_id"]: item for item in packet}
    verdicts = {}
    why = {}
    conflicts, unknown, invalid_lines = set(), set(), 0

    for raw in str(answer or "").splitlines():
        line = raw.strip().strip("`").strip()
        if not line.startswith("{"):
            if line:
                invalid_lines += 1
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            invalid_lines += 1
            continue
        item_id = str(obj.get("item", ""))
        verdict = str(obj.get("verdict", "")).upper()
        if item_id not in item_map:
            if item_id:
                unknown.add(item_id)
            else:
                invalid_lines += 1
            continue
        if verdict not in {"DEAD", "LIVE"}:
            invalid_lines += 1
            continue
        if item_id in conflicts:
            continue
        if item_id in verdicts and verdicts[item_id] != verdict:
            conflicts.add(item_id)
            verdicts.pop(item_id, None)
            why.pop(item_id, None)
            continue
        verdicts[item_id] = verdict
        why[item_id] = str(obj.get("why", ""))[:160]

    judged = sorted(item_map[item_id]["_canary_id"] for item_id in verdicts)
    claimed = sorted(item_map[item_id]["_canary_id"]
                     for item_id, verdict in verdicts.items() if verdict == "DEAD")
    missing = sorted(set(item_map) - set(verdicts))
    return {
        "verdicts": {item_map[item_id]["_canary_id"]: verdict
                     for item_id, verdict in sorted(verdicts.items())},
        "why": {item_id: why[item_id] for item_id in sorted(why)},
        "judged": judged,
        "claimed": claimed,
        "missing_items": missing,
        "unknown_items": sorted(unknown),
        "conflicts": sorted(conflicts),
        "invalid_lines": invalid_lines,
    }


def _sum_known(values):
    values = list(values)
    if any(value is None for value in values):
        return None
    return sum(values)


def _repeatability(parsed_branches):
    """Pairwise verdict agreement on items judged by more than one repeated branch."""
    compared = agreements = 0
    for i, left in enumerate(parsed_branches):
        for right in parsed_branches[i + 1:]:
            lv, rv = left["parse"]["verdicts"], right["parse"]["verdicts"]
            for canary_id in set(lv) & set(rv):
                compared += 1
                agreements += int(lv[canary_id] == rv[canary_id])
    return {
        "pairwise_compared": compared,
        "agreement": (agreements / compared) if compared else None,
    }


def summarize(manifest: dict, call_plan, branches) -> dict:
    """Aggregate host-owned assignment facts and model judgments without hiding partials."""
    from scripts import canary_oracle as C

    if len(call_plan) != len(branches):
        raise ValueError(
            f"call plan has {len(call_plan)} slots but fan returned {len(branches)} branches")
    defect_ids = {c["id"] for c in manifest.get("canaries", [])
                  if c.get("cls") in {"catchable", "undetectable"}}
    arms = {}

    for arm in ("replication", "sharding"):
        positions = []
        assigned = set()
        judged = set()
        claimed = set()
        arm_calls = [(call, branch) for call, branch in zip(call_plan, branches)
                     if call["arm"] == arm]
        for call, branch in arm_calls:
            parsed = parse_answer(branch.get("answer"), call["packet"])
            branch_assigned = {item["_canary_id"] for item in call["packet"]}
            assigned.update(branch_assigned)
            judged.update(parsed["judged"])
            claimed.update(parsed["claimed"])
            positions.append({
                "position": call["position"],
                "packet_index": call["packet_index"],
                "ok": bool(branch.get("ok")),
                "partial": bool(branch.get("partial")),
                "why": branch.get("why", ""),
                "assigned": sorted(branch_assigned),
                "parse": parsed,
            })

        positions.sort(key=lambda row: row["position"])
        anchor_true = set(positions[0]["parse"]["claimed"]) & defect_ids
        later_true = set().union(
            *(set(row["parse"]["claimed"]) & defect_ids for row in positions[1:]))
        anchor_assigned = set(positions[0]["assigned"])
        later_assigned = set().union(*(set(row["assigned"]) for row in positions[1:]))
        score = C.score_v2(manifest, claimed, assigned=assigned, judged=judged)
        arm_branches = [branch for call, branch in arm_calls]
        arms[arm] = {
            "calls": len(arm_calls),
            "branches_ok": sum(bool(branch.get("ok")) for branch in arm_branches),
            "branches_partial": sum(bool(branch.get("partial")) for branch in arm_branches),
            "prompt_chars": sum(len(call["prompt"]) for call, _ in arm_calls),
            "prompt_tokens": _sum_known(branch.get("prompt_tokens") for branch in arm_branches),
            "completion_tokens": _sum_known(
                branch.get("completion_tokens") for branch in arm_branches),
            "usd": _sum_known(branch.get("usd") for branch in arm_branches),
            "assigned_unique": len(assigned),
            "judged_unique": len(judged),
            "claimed_unique": len(claimed),
            "judgment_coverage": (len(judged) / len(assigned)) if assigned else None,
            "marginal_assigned_calls_2_4": len(later_assigned - anchor_assigned),
            "marginal_true_findings_calls_2_4": len(later_true - anchor_true),
            "score": score,
            "repeatability": _repeatability(positions),
            "positions": positions,
        }

    return {
        "arms": arms,
        "prompt_char_gap": relative_gap(
            arms["replication"]["prompt_chars"], arms["sharding"]["prompt_chars"]),
    }


def adjudicate(summary: dict, *, prompt_tolerance: float = 0.05,
               min_judgment_coverage: float = 0.80,
               precision_tolerance: float = 0.10) -> dict:
    """Apply the pre-registered ruling; any broken match yields INCONCLUSIVE."""
    arms = summary.get("arms", {})
    reasons = []
    for arm in ("replication", "sharding"):
        row = arms.get(arm)
        if not row:
            reasons.append(f"missing {arm} arm")
            continue
        if row["calls"] != 4:
            reasons.append(f"{arm} has {row['calls']} calls, expected 4")
        if row["branches_ok"] != row["calls"]:
            reasons.append(
                f"{arm} completed {row['branches_ok']}/{row['calls']} branches")
        coverage = row.get("judgment_coverage")
        if coverage is None or coverage < min_judgment_coverage:
            reasons.append(
                f"{arm} judgment coverage {coverage} is below {min_judgment_coverage}")
    if summary.get("prompt_char_gap", 1.0) > prompt_tolerance:
        reasons.append(
            f"prompt character gap {summary.get('prompt_char_gap'):.4f} exceeds "
            f"{prompt_tolerance:.4f}")
    if reasons:
        return {"ruling": "INCONCLUSIVE", "reasons": reasons}

    rep, shard = arms["replication"], arms["sharding"]
    rep_gain = rep["marginal_true_findings_calls_2_4"]
    shard_gain = shard["marginal_true_findings_calls_2_4"]
    rep_precision = rep["score"].get("precision")
    shard_precision = shard["score"].get("precision")

    if (shard_gain > rep_gain and shard_precision is not None
            and (rep_precision is None
                 or shard_precision >= rep_precision - precision_tolerance)):
        return {
            "ruling": "SHARDING",
            "reasons": [
                f"calls 2-4 added {shard_gain} unique true findings versus {rep_gain}, "
                "without exceeding the registered precision tolerance"
            ],
        }
    if (rep_gain > shard_gain and rep_precision is not None
            and (shard_precision is None
                 or rep_precision >= shard_precision - precision_tolerance)):
        return {
            "ruling": "REPLICATION",
            "reasons": [
                f"calls 2-4 recovered {rep_gain} anchor findings versus {shard_gain}, "
                "without exceeding the registered precision tolerance"
            ],
        }
    return {
        "ruling": "INCONCLUSIVE",
        "reasons": [
            f"marginal true findings tie or precision trade-off is unresolved "
            f"(replication={rep_gain}, sharding={shard_gain})"
        ],
    }


def archive_calibration(record: dict, *, archive_dir: str = None) -> str:
    """Write a verbatim hidden record outside every git worktree."""
    from scripts.round_archive import _tracked_by_git

    target_dir = os.path.abspath(archive_dir or DEFAULT_ARCHIVE_DIR)
    if _tracked_by_git(target_dir):
        raise ValueError(
            f"refusing to archive calibration evidence inside a git repository "
            f"({target_dir}); the record contains the sealed answer mapping")
    os.makedirs(target_dir, exist_ok=True)
    doc = dict(record)
    doc["schema"] = "akashic.fan-calibration/1"
    doc.setdefault("ended_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    digest = hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()[:10]
    stamp = "".join(ch for ch in doc["ended_at"] if ch.isalnum() or ch in "-_")
    path = os.path.join(target_dir, f"{stamp}_t195_{digest}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, default=str)
    os.replace(tmp, path)
    return path


def _finalize_archive(path: str, protocol: dict) -> None:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["protocol"] = protocol
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, default=str)
    os.replace(tmp, path)


def prepare_field(*, seed: int = 20260805, k: int = 32,
                  shadow: str = None, key_path: str = None) -> dict:
    """Create one committed-HEAD shadow, plant/seal the hidden field, and enumerate windows."""
    from scripts import canary_oracle as C
    from scripts.season_dryrun import _fresh_worktree
    from scripts.season_llm_player import candidates

    temp_root = tempfile.mkdtemp(prefix="season_fan_calibration_")
    shadow = shadow or os.path.join(temp_root, "shadow")
    key_path = key_path or os.path.join(temp_root, "key.json")
    _fresh_worktree(shadow)
    manifest = C.plant(shadow, k=k, seed=seed)
    digest = C.seal(manifest, key_path)
    return {
        "manifest": manifest,
        "candidates": candidates(shadow),
        "key_path": key_path,
        "key_sha256": digest,
        "seal_verified": C.verify_seal(key_path),
        "shadow": shadow,
    }


def _prompt_leaks(call_plan, manifest: dict, key_sha256: str):
    text = "\n".join(call["prompt"] for call in call_plan)
    forbidden = [str(c["id"]) for c in manifest.get("canaries", [])]
    if key_sha256:
        forbidden.append(str(key_sha256))
    return sorted(token for token in forbidden if token and token in text)


def run(*, seed: int = 20260805, packet_count: int = 4, packet_size: int = 8,
        snippet_chars: int = 1200, model: str = "deepseek-v4-pro",
        max_tokens: int = 9000, workers: int = 8, ask_fn=None,
        archive_dir: str = None, shadow: str = None, key_path: str = None) -> dict:
    """Execute one combined matched fan and return a key-safe aggregate receipt."""
    from scripts import canary_oracle as C
    if ask_fn is None:
        from core.comm.ask import ask_many
        ask_fn = ask_many

    field = prepare_field(
        seed=seed, k=packet_count * packet_size, shadow=shadow, key_path=key_path)
    packets = make_packets(
        field["candidates"], field["manifest"], packet_count=packet_count,
        packet_size=packet_size, snippet_chars=snippet_chars, seed=seed)
    call_plan = build_call_plan(packets)
    leaks = _prompt_leaks(call_plan, field["manifest"], field["key_sha256"])
    if leaks:
        raise RuntimeError(
            f"answer-key token(s) reached model input; refusing to spend: {len(leaks)} leak(s)")

    outcome = ask_fn(
        [call["prompt"] for call in call_plan], system=SYSTEM, model=model,
        max_tokens=max_tokens, max_workers=workers)
    branches = list((outcome.detail or {}).get("branches", []))
    summary = summarize(field["manifest"], call_plan, branches)
    decision = adjudicate(summary)

    record = {
        "config": {
            "seed": seed, "packet_count": packet_count, "packet_size": packet_size,
            "snippet_chars": snippet_chars, "model": model,
            "max_tokens": max_tokens, "workers": workers,
        },
        "key_sha256": field["key_sha256"],
        "manifest": field["manifest"],
        "call_plan": call_plan,
        "branches": branches,
        "summary": summary,
        "decision": decision,
    }
    archive_path = archive_calibration(record, archive_dir=archive_dir)
    with open(archive_path, encoding="utf-8") as fh:
        stored = json.load(fh)
    archive_complete = (
        len(stored.get("call_plan", [])) == len(call_plan)
        and len(stored.get("branches", [])) == len(call_plan)
        and all("prompt" in call for call in stored.get("call_plan", []))
        and all("answer" in branch for branch in stored.get("branches", []))
        and bool(stored.get("manifest", {}).get("canaries")))
    protocol = C.protocol_verdict(
        seal_verified=bool(field.get("seal_verified")),
        archive_complete=archive_complete,
        key_leak_detected=bool(leaks),
    )
    _finalize_archive(archive_path, protocol)

    return {
        "config": record["config"],
        "summary": summary,
        "decision": decision,
        "protocol": protocol,
        "archive_path": archive_path,
        "shadow": field.get("shadow"),
        "key_sha256_prefix": str(field["key_sha256"])[:12],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20260805)
    ap.add_argument("--snippet-chars", type=int, default=1200)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--max-tokens", type=int, default=9000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--archive-dir", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = run(
        seed=args.seed, snippet_chars=args.snippet_chars, model=args.model,
        max_tokens=args.max_tokens, workers=args.workers, archive_dir=args.archive_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        rep = result["summary"]["arms"]["replication"]
        shard = result["summary"]["arms"]["sharding"]
        print("== MATCHED DEEPSEEK FAN CALIBRATION ==")
        print(f"ruling: {result['decision']['ruling']}  protocol: {result['protocol']['validity']}")
        print(f"replication: true={rep['score']['true_positives']} "
              f"marginal={rep['marginal_true_findings_calls_2_4']} "
              f"precision={rep['score']['precision']} coverage={rep['judgment_coverage']}")
        print(f"sharding:    true={shard['score']['true_positives']} "
              f"marginal={shard['marginal_true_findings_calls_2_4']} "
              f"precision={shard['score']['precision']} coverage={shard['judgment_coverage']}")
        print(f"verbatim archive: {result['archive_path']}")
    return 2 if result["protocol"]["validity"] == "VOID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
