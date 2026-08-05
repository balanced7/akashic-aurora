"""PRE-REGISTERED ACCEPTANCE (T195) -- matched fan dispersal calibration.

The question is not whether four calls beat one.  Both arms get four calls.  The question is what
calls 2-4 buy when they repeat the same anchor packet versus traverse three disjoint sibling
packets.  One combined fan interleaves the arms so provider time is shared.

  K1  replication repeats one prompt byte-for-byte; sharding gets that anchor once
  K2  the other sharding packets are disjoint and together cover the full planted set
  K3  call count, system, model, token ceiling, packet size and prompt volume are matched
  K4  manifest ids and class labels never enter any model prompt
  K5  missing, unknown and conflicting model lines stay explicit; none becomes LIVE
  K6  host-owned assigned/judged/claimed sets feed score_v2, never player denominators
  K7  marginal calls 2-4 are scored separately from the shared anchor
  K8  any incomplete branch or >5% prompt imbalance makes the ruling INCONCLUSIVE
  K9  the verbatim experiment record lives outside git and refuses a repository path

RED command:
  py -m pytest tests/test_t195_replication_vs_positional_sharding.py -q
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import season_fan_calibration as F  # noqa: E402


def _fixture():
    classes = (["catchable"] * 11 + ["undetectable"] * 11 + ["bait"] * 10)
    manifest, candidates = {"canaries": []}, []
    for i, cls in enumerate(classes):
        name = f"neutral_fn_{i:02d}"
        manifest["canaries"].append({
            "id": f"secret_{i:02d}", "name": name, "cls": cls, "shape": "fixture",
        })
        candidates.append({
            "name": name,
            "file": f"core/neutral_{i:02d}.py",
            "line": i + 1,
            "window": f"def {name}():\n    return {i}\n" + (" " * (i * 7)),
        })
    return manifest, candidates


def _packets():
    manifest, candidates = _fixture()
    return manifest, F.make_packets(
        candidates, manifest, packet_count=4, packet_size=8,
        snippet_chars=600, seed=20260805)


def _correct_answer(packet, manifest):
    cls = {c["id"]: c["cls"] for c in manifest["canaries"]}
    lines = []
    for item in packet:
        verdict = "LIVE" if cls[item["_canary_id"]] == "bait" else "DEAD"
        lines.append(json.dumps({"item": item["item_id"], "verdict": verdict,
                                 "why": "fixture judgment"}))
    return "\n".join(lines)


def _branches(plan, manifest, *, fail_index=None):
    out = []
    for i, call in enumerate(plan):
        ok = i != fail_index
        out.append({
            "i": i,
            "ok": ok,
            "partial": not ok,
            "why": "" if ok else "finish_reason=length",
            "answer": _correct_answer(call["packet"], manifest),
            "usd": 0.01,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "elapsed_s": 2.0,
            "model": "deepseek-v4-pro",
        })
    return out


def test_k1_k2_anchor_is_identical_and_only_shards_traverse_siblings():
    _manifest, packets = _packets()
    plan = F.build_call_plan(packets)

    assert [(c["arm"], c["position"]) for c in plan] == [
        ("replication", 0), ("sharding", 0),
        ("replication", 1), ("sharding", 1),
        ("replication", 2), ("sharding", 2),
        ("replication", 3), ("sharding", 3),
    ]
    replication = [c for c in plan if c["arm"] == "replication"]
    sharding = [c for c in plan if c["arm"] == "sharding"]
    assert len({c["prompt"] for c in replication}) == 1
    assert replication[0]["prompt"] == sharding[0]["prompt"]
    assert len({c["prompt"] for c in sharding}) == 4

    shard_sets = [{i["_canary_id"] for i in c["packet"]} for c in sharding]
    assert all(a.isdisjoint(b) for i, a in enumerate(shard_sets)
               for b in shard_sets[i + 1:])
    assert len(set().union(*shard_sets)) == 32


def test_k3_packet_shape_and_prompt_volume_are_matched():
    _manifest, packets = _packets()
    plan = F.build_call_plan(packets)
    by_arm = {arm: [c for c in plan if c["arm"] == arm]
              for arm in ("replication", "sharding")}

    assert {len(c["packet"]) for c in plan} == {8}
    assert {len(by_arm[arm]) for arm in by_arm} == {4}
    chars = {arm: sum(len(c["prompt"]) for c in calls)
             for arm, calls in by_arm.items()}
    assert F.relative_gap(chars["replication"], chars["sharding"]) <= 0.05


def test_k4_the_answer_key_does_not_enter_prompts():
    manifest, packets = _packets()
    prompt = "\n".join(c["prompt"] for c in F.build_call_plan(packets))

    assert all(c["id"] not in prompt for c in manifest["canaries"])
    assert not any(label in prompt.lower()
                   for label in ("catchable", "undetectable", "bait"))


def test_k5_missing_unknown_and_conflicting_lines_are_not_judgments():
    _manifest, packets = _packets()
    packet = packets[0]
    a, b = packet[0]["item_id"], packet[1]["item_id"]
    answer = "\n".join([
        json.dumps({"item": a, "verdict": "DEAD", "why": "first"}),
        json.dumps({"item": a, "verdict": "LIVE", "why": "conflict"}),
        json.dumps({"item": b, "verdict": "LIVE", "why": "settled"}),
        json.dumps({"item": "not_assigned", "verdict": "DEAD", "why": "unknown"}),
    ])
    got = F.parse_answer(answer, packet)

    assert got["conflicts"] == [a]
    assert got["unknown_items"] == ["not_assigned"]
    assert got["judged"] == [packet[1]["_canary_id"]]
    assert packet[0]["_canary_id"] not in got["judged"]
    assert len(got["missing_items"]) == 7


def test_k6_k7_scoring_uses_host_sets_and_separates_marginal_calls():
    manifest, packets = _packets()
    plan = F.build_call_plan(packets)
    got = F.summarize(manifest, plan, _branches(plan, manifest))

    replication = got["arms"]["replication"]
    sharding = got["arms"]["sharding"]
    assert replication["calls"] == sharding["calls"] == 4
    assert replication["score"]["precision"] == 1.0
    assert sharding["score"]["precision"] == 1.0
    assert replication["marginal_true_findings_calls_2_4"] == 0
    assert sharding["marginal_true_findings_calls_2_4"] > 0
    assert replication["assigned_unique"] == 8
    assert sharding["assigned_unique"] == 32
    assert F.adjudicate(got)["ruling"] == "SHARDING"


def test_k8_incomplete_fan_is_inconclusive_and_keeps_unjudged():
    manifest, packets = _packets()
    plan = F.build_call_plan(packets)
    got = F.summarize(manifest, plan, _branches(plan, manifest, fail_index=3))

    assert got["arms"]["sharding"]["branches_ok"] == 3
    assert F.adjudicate(got)["ruling"] == "INCONCLUSIVE"
    assert F.adjudicate(got)["reasons"]


def test_k8_prompt_imbalance_is_inconclusive():
    manifest, packets = _packets()
    plan = F.build_call_plan(packets)
    # Preserve every assignment but create a deliberately unmatched input budget.
    for call in plan:
        if call["arm"] == "sharding":
            call["prompt"] += "x" * 5000
    got = F.summarize(manifest, plan, _branches(plan, manifest))

    decision = F.adjudicate(got)
    assert decision["ruling"] == "INCONCLUSIVE"
    assert any("prompt" in reason for reason in decision["reasons"])


def test_k9_archive_is_verbatim_and_refuses_git(tmp_path):
    record = {
        "manifest": {"canaries": [{"id": "secret"}]},
        "call_plan": [{"prompt": "verbatim prompt"}],
        "branches": [{"answer": "verbatim answer"}],
        "summary": {"arms": {}},
    }
    path = F.archive_calibration(record, archive_dir=str(tmp_path))
    stored = json.loads(open(path, encoding="utf-8").read())
    assert stored["call_plan"][0]["prompt"] == "verbatim prompt"
    assert stored["branches"][0]["answer"] == "verbatim answer"

    with pytest.raises(ValueError, match="git|repositor"):
        F.archive_calibration(record, archive_dir=os.path.join(ROOT, "research"))


def test_run_uses_one_combined_fan_with_matched_controls(tmp_path, monkeypatch):
    manifest, candidates = _fixture()
    calls = []

    def fake_ask(prompts, **kwargs):
        calls.append((list(prompts), dict(kwargs)))
        packets = F.make_packets(candidates, manifest, packet_count=4, packet_size=8,
                                 snippet_chars=600, seed=20260805)
        plan = F.build_call_plan(packets)
        return SimpleNamespace(detail={"branches": _branches(plan, manifest)})

    monkeypatch.setattr(F, "prepare_field", lambda **_kw: {
        "manifest": manifest,
        "candidates": candidates,
        "key_path": str(tmp_path / "key.json"),
        "key_sha256": "a" * 64,
        "seal_verified": True,
        "shadow": str(tmp_path / "shadow"),
    })
    got = F.run(
        seed=20260805, snippet_chars=600, max_tokens=9000, workers=8,
        ask_fn=fake_ask, archive_dir=str(tmp_path / "archive"))

    assert len(calls) == 1 and len(calls[0][0]) == 8
    assert calls[0][1]["system"] == F.SYSTEM
    assert calls[0][1]["max_tokens"] == 9000
    assert calls[0][1]["max_workers"] == 8
    assert got["decision"]["ruling"] == "SHARDING"
    assert got["protocol"]["validity"] == "VALID"
    assert os.path.isfile(got["archive_path"])
