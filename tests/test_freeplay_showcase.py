"""
FREE PLAY 2026-07-20 -- DEEPSEEK'S SHOWCASE: mint + kata + verify three new verbs.

TOOLS HUNT LEADERBOARD → DEEPSEEK TOOLBELT:
  parse-gate   — the edit-verify cycle: lock→fence→kata (scar-springboard #1)
  toast        — raise a glass: story-chronicle + notes --project + wrap snapshot  
  muse         — creative brainstorm: knowledge-map + lookback + events --capture

Every verb: MINT (GUESS) → KATA (grammar-prove) → LEVEL UP (VERIFIED).
"""
from core.toolbelt.registry import Toolbelt
import agent_cli
import tempfile, os, shutil

def _toolbelt(tmp):
    return Toolbelt("deepseek-showcase", root=tmp)

# ═══════════════════════════════════════════════════════════════════ PARSE-GATE
def test_parse_gate():
    """parse-gate: lock→fence open→kata. The full edit-verify ceremony in one verb."""
    tmp = tempfile.mkdtemp(prefix="pg-")
    tb = _toolbelt(tmp)

    tb.mint("parse-gate", steps=[
        ["lock",    "deepseek", "placeholder"],    # claim the path
        ["fence",   "open", "--slot", "brief"],    # open the fence slot
        ["kata",    "deepseek", "placeholder"],    # grammar-prove the result
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: scar-springboard #1 from tools hunt. "
           "lock→fence→kata = the full edit-verify cycle. "
           "Each step is a real agent_cli verb — sugar-only, never shadows.")

    ok, results = agent_cli._kata_check(tb.resolve("parse-gate"))
    assert ok, f"parse-gate kata FAILED: {[r for r in results if not r[0]]}"
    entry = agent_cli._kata_apply(tb, "parse-gate", results)
    assert entry["evidence"] == "VERIFIED"
    assert entry["version"] == 2
    print(f"  [PARSE-GATE] v{entry['version']} {entry['evidence']} — {len(entry['steps'])} steps")

    shutil.rmtree(tmp, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════ TOAST  
def test_toast():
    """toast: raise a glass — story chronicle + notes --project + wrap overnight."""
    tmp = tempfile.mkdtemp(prefix="toast-")
    tb = _toolbelt(tmp)

    tb.mint("toast", steps=[
        ["story",   "--chronicle"],                  # the living narrative arc
        ["notes",   "--project"],                    # regenerate memory.md
        ["wrap",    "--hours", "24"],                # distill the session
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: toast from tools-hunt creative tier. "
           "Raise a glass: see the chronicle, refresh project memory, distill. "
           "The celebration verb for end-of-session.")

    ok, results = agent_cli._kata_check(tb.resolve("toast"))
    assert ok, f"toast kata FAILED: {[r for r in results if not r[0]]}"
    entry = agent_cli._kata_apply(tb, "toast", results)
    assert entry["evidence"] == "VERIFIED"
    print(f"  [TOAST]      v{entry['version']} {entry['evidence']} — {len(entry['steps'])} steps")

    shutil.rmtree(tmp, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════ MUSE
def test_muse():
    """muse: creative brainstorm — knowledge-map + lookback + events capture."""
    tmp = tempfile.mkdtemp(prefix="muse-")
    tb = _toolbelt(tmp)

    tb.mint("muse", steps=[
        ["knowledge-map", "recovery"],               # walk the neighborhood
        ["lookback",      "what are our biggest architectural risks?"],  # strategic WHY
        ["events",        "--capture", "--summary", "muse-firehose"], # capture the firehose
    ], evidence="GUESS",
       why="deepseek FREE PLAY 2026-07-20: muse from tools-hunt creative tier. "
           "The creative brainstorm ritual: map the idea neighborhood, "
           "look back at the WHY, capture what's happening NOW.")

    ok, results = agent_cli._kata_check(tb.resolve("muse"))
    assert ok, f"muse kata FAILED: {[r for r in results if not r[0]]}"
    entry = agent_cli._kata_apply(tb, "muse", results)
    assert entry["evidence"] == "VERIFIED"
    print(f"  [MUSE]       v{entry['version']} {entry['evidence']} — {len(entry['steps'])} steps")

    shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════ BATCH SHOW
def test_toolbelt_roster():
    """Show the full showcase roster after minting all three."""
    tmp = tempfile.mkdtemp(prefix="showcase-")
    tb = _toolbelt(tmp)

    for name, steps in [
        ("parse-gate", [["lock", "deepseek", "x"], ["fence", "open", "--slot", "brief"], ["kata", "deepseek", "x"]]),
        ("toast",      [["story", "--chronicle"], ["notes", "--project"], ["wrap", "--hours", "24"]]),
        ("muse",       [["knowledge-map", "recovery"], ["lookback", "risks"], ["events", "--capture", "--summary", "muse-firehose"]]),
    ]:
        tb.mint(name, steps=steps)
        ok, results = agent_cli._kata_check(tb.resolve(name))
        assert ok, f"{name} kata FAILED"
        agent_cli._kata_apply(tb, name, results)

    print(f"\n{tb.render_list()}")
    print(f"\n  >>> 3 VERBS, ALL VERIFIED. The toolbelt is armed. <<<")

    shutil.rmtree(tmp, ignore_errors=True)
