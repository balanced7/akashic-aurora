"""
FREE PLAY 2026-07-20 -- deepseek's campfire: a narrative gathering verb.

Design: campfire = show the story chronicle + themes + mark a gathering moment.
Minted as a toolbelt alias, then kata'd to VERIFIED.

The ritual:
  1. story --chronicle      # the living narrative arc
  2. story --themes          # active themes
  3. story --chapter         # current chapter
"""
from core.toolbelt.registry import Toolbelt
import agent_cli
import tempfile, os

def test_campfire_mint_and_kata():
    tmp = tempfile.mkdtemp(prefix="campfire-")
    tb = Toolbelt("deepseek-campfire", root=tmp)

    # ---- MINT the campfire verb
    entry = tb.mint(
        "campfire",
        steps=[
            ["story", "--chronicle"],
            ["story", "--themes"],
            ["story", "--chapter"],
        ],
        evidence="GUESS",
        why="deepseek FREE PLAY 2026-07-20: narrative gathering ritual -- "
            "gather round the chronicle, see the themes, know the chapter. "
            "From the tools-hunt leaderboard (campfire = 3 renderings).",
    )
    assert entry["name"] == "campfire"
    assert entry["evidence"] == "GUESS"
    assert entry["version"] == 1
    print(f"\n  [MINTED] campfire v1 (GUESS) -- {len(entry['steps'])} steps")

    # ---- KATA: grammar-prove it against the door
    steps = tb.resolve("campfire")
    ok, results = agent_cli._kata_check(steps)
    assert ok, f"campfire failed kata: {results}"
    print(f"  [KATA]   campfire grammar CLEAN -- {len(results)} steps verified")

    # ---- LEVEL UP to VERIFIED
    entry2 = agent_cli._kata_apply(tb, "campfire", results)
    assert entry2["evidence"] == "VERIFIED"
    assert entry2["version"] == 2
    assert str(entry2["tested_against"]).startswith("kata-")
    print(f"  [LEVEL]  campfire v2 VERIFIED (tested_against={entry2['tested_against']})")

    # ---- Show the final state
    print(f"\n  {tb.render_list()}")

    # ---- Clean and confirm
    assert tb.get("campfire")["evidence"] == "VERIFIED"
    print(f"\n  >>> CAMPFIRE IS VERIFIED. The fleet can gather. <<<")

    # cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_campfire_resolve():
    """Verify the resolved argv matches design intent."""
    tmp = tempfile.mkdtemp(prefix="campfire-")
    tb = Toolbelt("deepseek-campfire", root=tmp)
    tb.mint("campfire", steps=[
        ["story", "--chronicle"],
        ["story", "--themes"],
        ["story", "--chapter"],
    ])
    resolved = tb.resolve("campfire")
    assert resolved == [
        ["story", "--chronicle"],
        ["story", "--themes"],
        ["story", "--chapter"],
    ], f"unexpected resolution: {resolved}"
    print("\n  [RESOLVE] campfire resolves to 3 story invocations: chronicle, themes, chapter")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
