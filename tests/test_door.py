"""Door tests: the agent_cli surface is self-describing -- every verb has a purpose, and `discover`
introspects the live parser (one source of truth). This is the One-Door guarantee: the door can't
grow a silent verb (one that lies by omission) or describe a verb that doesn't exist.

Run: py tests/test_door.py   (or via pytest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_cli import list_verbs


def test_every_verb_has_a_purpose():
    verbs = list_verbs()
    assert len(verbs) >= 15, f"expected the full door, got {len(verbs)} verbs"
    silent = [n for n, h in verbs if not h]
    assert not silent, f"verbs missing a help/purpose -- the door must not lie: {silent}"
    bad = [n for n, _ in verbs if n != n.lower() or " " in n]   # ubiquitous-language hygiene
    assert not bad, f"non-kebab/lowercase verb names: {bad}"
    print(f"\n--- door is self-describing ---\n  {len(verbs)} verbs, all with a purpose OK")


def test_discover_includes_itself_and_filters():
    names = [n for n, _ in list_verbs()]
    assert "discover" in names and "recall-at" in names, "discover must list itself and siblings"
    filtered = list_verbs("recall")
    assert filtered and all("recall" in (n + h).lower() for n, h in filtered), "filter should match on name/purpose"
    assert not list_verbs("zzzznomatchzzzz"), "no spurious matches"
    print("--- discover filter ---\n  substring filter works; discover lists itself OK")


def test_build_parser_is_deterministic():
    a = [n for n, _ in list_verbs()]
    b = [n for n, _ in list_verbs()]
    assert a == b and a, "build_parser() must be pure/deterministic (cmd_discover calls it at runtime)"
    print("--- build_parser pure ---\n  deterministic OK")


if __name__ == "__main__":
    print("=" * 60); print("DOOR TESTS"); print("=" * 60)
    test_every_verb_has_a_purpose()
    test_discover_includes_itself_and_filters()
    test_build_parser_is_deterministic()
    print("\n" + "=" * 60); print("ALL DOOR TESTS PASSED"); print("=" * 60)
