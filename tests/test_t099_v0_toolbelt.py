"""
T099 · V0 self-tooling — verb registry + alias engine + capture verb.
Cites docs/self-tooling-design-2026-07.md (reconciled three-half design; Daniel gate 2026-07-20).

Laws under test (pre-registered, RED before core/toolbelt/registry.py exists):
  - SUGAR-ONLY: an alias is a sequence of EXISTING agent_cli verbs; minting a step naming an
    unknown verb refuses loudly. Aliases run only via `run <agent> <name>` — a real verb can
    never be shadowed by construction.
  - HONESTY LABELS (kimi a): every entry carries evidence VERIFIED|INFER|GUESS (default GUESS)
    + tested_against; labels render in the listing.
  - OBSERVATION/PROJECTION (kimi c + lesson-identity contract): re-mint same name supersedes
    with version+1 (prior retained); exact re-mint (same steps) is a no-op; registry file is
    the durable source of truth.
  - QUOTA (junk-drawer guard): per-agent cap, default 20 active; the 21st mint refuses.
  - EXECUTION: resolve_and_run executes steps in order through an injected runner (hermetic).
Run: py -m pytest tests/test_t099_v0_toolbelt.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KNOWN = {"bifrost-pause", "bifrost-skip-to-now", "bifrost-resume", "doctor", "discover"}


def _reg(tmp_path):
    from core.toolbelt.registry import Toolbelt
    return Toolbelt("t-tester", root=str(tmp_path), known_verbs=lambda: KNOWN)


def test_mint_resolve_round_trip(tmp_path):
    tb = _reg(tmp_path)
    tb.mint("standby-hard", [["bifrost-pause", "--reason", "x", "--by", "t-tester"],
                             ["bifrost-skip-to-now", "t-tester", "--by", "t-tester", "--reason", "x"],
                             ["bifrost-resume"]])
    steps = tb.resolve("standby-hard")
    assert [s[0] for s in steps] == ["bifrost-pause", "bifrost-skip-to-now", "bifrost-resume"]


def test_sugar_only_unknown_verb_refuses(tmp_path):
    tb = _reg(tmp_path)
    try:
        tb.mint("evil", [["rm", "-rf", "/"]])
        assert False, "minting a non-agent_cli step must refuse"
    except ValueError as e:
        assert "unknown verb" in str(e).lower()


def test_honesty_label_defaults_guess_and_renders(tmp_path):
    tb = _reg(tmp_path)
    tb.mint("peek", [["discover"]])
    entry = tb.get("peek")
    assert entry["evidence"] == "GUESS", "untested sugar must confess it's untested"
    assert entry["tested_against"] is None
    listing = tb.render_list()
    assert "GUESS" in listing and "peek" in listing


def test_remint_supersedes_with_version_exact_remint_noop(tmp_path):
    tb = _reg(tmp_path)
    tb.mint("peek", [["discover"]])
    v1 = tb.get("peek")["version"]
    tb.mint("peek", [["discover"]])                      # exact re-mint -> no-op
    assert tb.get("peek")["version"] == v1
    tb.mint("peek", [["doctor"]])                        # changed definition -> supersede
    e = tb.get("peek")
    assert e["version"] == v1 + 1 and e["steps"] == [["doctor"]]
    assert tb.history("peek")[0]["steps"] == [["discover"]], "prior observation retained"


def test_quota_refuses_21st_active(tmp_path):
    tb = _reg(tmp_path)
    for i in range(20):
        tb.mint(f"a{i}", [["discover"]])
    try:
        tb.mint("a20", [["discover"]])
        assert False, "21st active mint must refuse (junk-drawer guard)"
    except ValueError as e:
        assert "quota" in str(e).lower()


def test_run_executes_steps_in_order_via_injected_runner(tmp_path):
    tb = _reg(tmp_path)
    tb.mint("combo", [["bifrost-pause", "--by", "t"], ["bifrost-resume"]])
    ran = []
    rc = tb.resolve_and_run("combo", runner=lambda argv: (ran.append(list(argv)) or 0))
    assert rc == 0 and [r[0] for r in ran] == ["bifrost-pause", "bifrost-resume"]


def test_registry_survives_reload_file_is_truth(tmp_path):
    from core.toolbelt.registry import Toolbelt
    tb = _reg(tmp_path)
    tb.mint("keep", [["discover"]])
    tb2 = Toolbelt("t-tester", root=str(tmp_path), known_verbs=lambda: KNOWN)   # fresh projection
    assert tb2.resolve("keep") == [["discover"]], "re-projection from the durable file"


def test_evidence_upgrade_is_not_swallowed_by_noop(tmp_path):
    """Dogfood catch 2026-07-20: re-minting identical steps with a CHANGED honesty label was
    swallowed by the exact-re-mint no-op. Evidence IS content (observation/projection contract):
    a label change must supersede (version+1), never silently no-op."""
    tb = _reg(tmp_path)
    tb.mint("peek", [["discover"]])
    assert tb.get("peek")["evidence"] == "GUESS"
    tb.mint("peek", [["discover"]], evidence="VERIFIED", tested_against="pin-x")
    e = tb.get("peek")
    assert e["evidence"] == "VERIFIED" and e["tested_against"] == "pin-x" and e["version"] == 2


def test_family_tag_persists_renders_and_is_content(tmp_path):
    """Round-2 (Daniel theming): entries carry a FAMILY tag (Halo-caste taxonomy). Family
    persists, renders grouped, defaults UNSORTED, and IS content — a family change must
    supersede (version+1), never silently no-op (same law as evidence)."""
    tb = _reg(tmp_path)
    tb.mint("peek", [["discover"]])
    assert tb.get("peek").get("family", "UNSORTED") == "UNSORTED"
    tb.mint("peek", [["discover"]], family="MONITORS")
    e = tb.get("peek")
    assert e["family"] == "MONITORS" and e["version"] == 2, "family change supersedes"
    tb.mint("peek", [["discover"]], family="MONITORS")     # exact re-mint incl family -> no-op
    assert tb.get("peek")["version"] == 2
    assert "MONITORS" in tb.render_list()
