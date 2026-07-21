"""T099 kit -- the KIT tier v1 (kimi PASS 2 build). 6 pins, pre-registered.

P1  install into empty belt -> all entries minted, report ok
P2  $SELF$ substitution -> every step carries the installing seat, no literal $SELF$ survives
P3  exact re-install -> no-op per entry, versions unchanged (RB-26 idempotency)
P4  changed kit entry -> supersedes (version+1), prior rides history
P5  refused entry (quota) -> report confesses REFUSED, other entries still install (partial visibility)
P6  evidence labels ride through -- VERIFIED stays VERIFIED, GUESS stays GUESS (no upgrade)
"""
import core.toolbelt.kit as kit
from core.toolbelt.registry import Toolbelt

KNOWN = {"bifrost-pause", "bifrost-skip-to-now", "bifrost-resume", "bifrost-sync",
         "doctor", "bifrost-dashboard", "delta", "bifrost-inbox"}


def _belt(tmp_path, agent="kimi", quota=20):
    return Toolbelt(agent, root=str(tmp_path), known_verbs=lambda: KNOWN, quota=quota)


def test_p1_install_empty_belt_all_minted(tmp_path):
    rep = kit.install(kit.RECOVERY_KIT, _belt(tmp_path))
    assert rep["ok"] and rep["seat"] == "kimi"
    assert all(e["result"] == "minted" for e in rep["entries"]), rep
    assert len(rep["entries"]) == 4


def test_p2_self_substitution_carries_installing_seat(tmp_path):
    b = _belt(tmp_path, agent="deepseek")
    kit.install(kit.RECOVERY_KIT, b)
    for name in b.active():
        steps = b.get(name)["steps"]
        for step in steps:
            assert "$SELF$" not in step
        if name == "standby-hard":
            assert any("deepseek" in step for step in steps), \
                "the installing seat's name rides at least one step (bifrost-resume takes none)"


def test_p3_reinstall_is_noop_versions_stable(tmp_path):
    b = _belt(tmp_path)
    kit.install(kit.RECOVERY_KIT, b)
    rep2 = kit.install(kit.RECOVERY_KIT, b)
    assert all("no-op" in e["result"] for e in rep2["entries"]), rep2
    assert all(b.get(n)["version"] == 1 for n in b.active())


def test_p4_changed_entry_supersedes_history_retained(tmp_path):
    b = _belt(tmp_path)
    kit.install(kit.RECOVERY_KIT, b)
    changed = dict(kit.RECOVERY_KIT)
    changed["entries"] = [dict(e) for e in kit.RECOVERY_KIT["entries"]]
    changed["entries"][2]["steps"] = [["doctor"]]          # vitals, narrower
    rep = kit.install(changed, b)
    row = [e for e in rep["entries"] if e["name"] == "vitals"][0]
    assert "superseded" in row["result"] and "v2" in row["result"], row
    assert len(b.history("vitals")) == 1


def test_p5_quota_refusal_confessed_partial_install_visible(tmp_path):
    b = _belt(tmp_path, quota=2)                            # only 2 slots
    rep = kit.install(kit.RECOVERY_KIT, b)
    assert rep["ok"] is False
    refused = [e for e in rep["entries"] if e["result"].startswith("REFUSED")]
    minted = [e for e in rep["entries"] if e["result"] == "minted"]
    assert len(minted) == 2 and len(refused) == 2, rep      # partial, confessed


def test_p6_evidence_labels_ride_no_upgrade(tmp_path):
    b = _belt(tmp_path)
    kit.install(kit.RECOVERY_KIT, b)
    assert b.get("standby-hard")["evidence"] == "VERIFIED"
    assert b.get("standby-hard")["tested_against"] == "test_t099_v0_toolbelt+live-run-2026-07-20"
    assert b.get("vitals")["evidence"] == "GUESS"            # confesses, no inflation
