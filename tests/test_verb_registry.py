"""The verb registry's contracts -- one table, no silent checker blindness (phase 2, attack C).

Rill's attack C (2026-09-17), verbatim:

    "'Thin dispatcher over a registry' has a cost the sketch does not price: the checkers eat the
    same table. Verb bodies are read not only by dispatch but by the door-parity checker, the
    advertised-verb checker, and the MCP twin surface. Extracting bodies must keep ONE
    introspectable registry that those checkers read, or we trade file collisions for checker
    blindness -- a worse trade, because collisions are loud and blind checkers are silent."

So this file does not merely test that the registry exists. It tests that EVERY consumer still
sees EVERY verb after a body moved:

  * the registry agrees with the parser that dispatches (the only source that cannot lie);
  * every `add_parser` spelling in agent_cli.py resolves at the top level, and any that does not is
    proven NESTED (a sub-action) rather than assumed harmless;
  * the AST-based checkers (advertised verbs, door parity) still get the same set;
  * the coordinate consumers (`compare`, `capability_search`) still get the same set;
  * the MCP twin still bootstraps a door that knows every verb -- checked in a SUBPROCESS, because
    `ai_setup_mcp` installs a process-wide stdout membrane at import;
  * every name the HOOKS and the OUT-OF-TREE plugin read off `agent_cli` still exists -- the
    cross-fleet API surface, where a skew renders as silence.

Run: py tests/test_verb_registry.py   (or via pytest)
"""
import ast
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import agent_cli                                                          # noqa: E402
from verbs import registry as vreg                                        # noqa: E402


# ------------------------------------------------------------------ helpers: the true verb set
def _published():
    """Build the parser (which publishes) and REFUSE to test an empty table.

    This exists because the first draft of this file passed `check_advertised_verbs` with
    "all 0 registry verbs inside" -- the table had never been published, `set() - set() == set()`,
    and a coverage pin read GREEN against nothing. That is precisely the silent-blindness shape
    this file exists to forbid, reproduced inside the test written to catch it. So every pin here
    publishes first and asserts the table is real.
    """
    agent_cli.build_parser()
    assert vreg.REGISTRY, "the registry is empty -- publish() never ran, so this pin would be vacuous"
    return vreg.REGISTRY


def _top_level_choices(parser):
    import argparse
    sa = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
    return sa


def _nested_parents(parser):
    """Top-level verbs whose own dispatch is a nested subparser set (they carry no fn themselves)."""
    import argparse
    out = set()
    for name, sub in _top_level_choices(parser).choices.items():
        if any(isinstance(a, argparse._SubParsersAction) for a in sub._actions):
            out.add(name)
    return out


def _nested_choice_names(parser):
    """Choices that live under ANOTHER verb (e.g. `college start`), i.e. not verbs themselves."""
    import argparse
    out = set()
    for _name, sub in _top_level_choices(parser).choices.items():
        for a in sub._actions:
            if isinstance(a, argparse._SubParsersAction):
                out |= set(a.choices)
    return out


def _ast_add_parser_names():
    """Every `add_parser("...")` spelling in agent_cli.py -- the AST view the checkers use."""
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    out = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_parser" and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            out.add(node.args[0].value)
    return out


# ------------------------------------------------------------------------ the table is the door
def test_the_registry_agrees_with_the_parser_that_dispatches():
    _published()
    parser = agent_cli.build_parser()                 # publishes as its last act
    sa = _top_level_choices(parser)
    assert set(vreg.REGISTRY) == set(sa.choices), (
        "the registry and the parser disagree -- a consumer reading one would miss what the other "
        f"dispatches. only in registry: {sorted(set(vreg.REGISTRY) - set(sa.choices))}; "
        f"only in parser: {sorted(set(sa.choices) - set(vreg.REGISTRY))}")
    print(f"\n--- table == parser ---\n  {len(vreg.REGISTRY)} verbs, identical sets OK")


def test_list_verbs_delegates_and_keeps_its_shape():
    """The compat contract: [(verb, purpose)] in parser order, from agent_cli.list_verbs."""
    _published()
    rows = agent_cli.list_verbs()
    assert rows and all(isinstance(n, str) and isinstance(h, str) for n, h in rows)
    assert rows == vreg.list_verbs(), "agent_cli.list_verbs must delegate to verbs.registry"
    assert [n for n, _ in rows] == list(vreg.REGISTRY), "parser order must be preserved"
    assert agent_cli.list_verbs("recall") == [r for r in rows if "recall" in (r[0] + r[1]).lower()]
    print(f"--- compat contract ---\n  list_verbs delegates, {len(rows)} rows, order preserved OK")


def test_every_verb_spelling_resolves_and_only_nested_ones_lack_a_fn():
    _published()
    parser = agent_cli.build_parser()
    parents = _nested_parents(parser)
    nested_flagged = {name for name, spec in vreg.REGISTRY.items() if spec.nested}
    assert nested_flagged <= parents, (
        "a verb flagged `nested` whose parser has no nested subparsers -- the flag would be a "
        f"guess: {sorted(nested_flagged - parents)}")
    for name in sorted(parents):
        spec = vreg.REGISTRY[name]
        assert spec.fn is None or callable(spec.fn), name
    without_fn = {name for name, spec in vreg.REGISTRY.items() if spec.fn is None}
    assert without_fn <= parents, (
        "these verbs have no fn and are NOT nested dispatch -- i.e. a verb that would be "
        f"unreachable through set_defaults: {sorted(without_fn - parents)}")
    resolvable = {name for name, spec in vreg.REGISTRY.items() if callable(spec.fn)}
    for name in sorted(resolvable):
        assert vreg.resolve(name) is vreg.REGISTRY[name].fn
    print(f"--- resolution ---\n  {len(resolvable)} resolve to a callable "
          f"({len(nested_flagged)} of them REPRESENTATIVE of a nested dispatch); "
          f"{len(without_fn)} have no fn at all {sorted(without_fn)} OK")


def test_a_nested_dispatch_verb_still_reports_its_moved_body():
    """`glance` dispatches through nested subparsers, so its parent parser binds no fn.

    Left alone, a representative-less table would report `module == ""` for it and the verb would
    silently vanish from `moved()` -- present in the door, absent from the extraction's own progress
    bar. Pinned because it is exactly the class of blindness this file exists for.
    """
    _published()
    spec = vreg.get_spec("glance")
    assert spec is not None and spec.nested, spec
    assert callable(spec.fn) and spec.fn.__name__ == "cmd_glance", spec
    assert spec.moved, "a moved body behind a nested dispatch must still read as moved"
    print("--- nested dispatch ---\n  glance: representative fn, nested flag, still `moved` OK")


def test_no_add_parser_spelling_can_vanish_from_the_table():
    """ATTACK C's core pin: the AST set the checkers derive must be fully explained.

    Anything an `add_parser("x")` advertises is either a TOP-LEVEL verb (so it is in the registry)
    or a NESTED sub-action (so it is not a verb at all, and the parser proves it). There is no
    third explanation, which is what makes this a coverage proof rather than a hope.
    """
    _published()
    ast_names = _ast_add_parser_names()
    parser = agent_cli.build_parser()
    nested = _nested_choice_names(parser)
    registered = set(vreg.REGISTRY)
    unexplained = ast_names - registered - nested
    assert not unexplained, (
        "add_parser spellings that are neither in the registry nor provably nested -- a consumer "
        f"deriving the verb set from the file would see verbs the table does not: {sorted(unexplained)}")
    assert registered <= ast_names, (
        f"the registry invented verb(s) no add_parser advertises: {sorted(registered - ast_names)}")
    print(f"--- AST coverage ---\n  {len(ast_names)} add_parser spellings = "
          f"{len(registered)} verbs + {len(ast_names - registered)} nested sub-actions OK")


# ---------------------------------------------------- the six consumers named in the design
def test_check_advertised_verbs_still_sees_every_verb():
    _published()
    import check_advertised_verbs as cav
    ast_verbs = cav.registered_verbs()
    registered = set(vreg.REGISTRY)
    missing = registered - ast_verbs
    assert not missing, f"the advertised-verb checker would not see: {sorted(missing)}"
    print(f"--- consumer: check_advertised_verbs ---\n  {len(ast_verbs)} AST verbs, "
          f"all {len(registered)} registry verbs inside OK")


def test_check_door_parity_still_sees_every_verb():
    _published()
    import check_door_parity as cdp
    their = {n.replace("-", "_") for n in cdp.cli_verbs()}
    ours = {n.replace("-", "_") for n in vreg.REGISTRY}
    assert not (ours - their), f"door parity would not see: {sorted(ours - their)}"
    print(f"--- consumer: check_door_parity ---\n  {len(their)} normalized verbs, no gap OK")


def test_the_coordinate_domains_still_see_every_verb():
    _published()
    from core.coord import compare as cmp_mod
    cli_side = cmp_mod._verbs_cli()
    assert cli_side == set(vreg.REGISTRY), (
        "core/coord/compare.py's `verbs.cli` domain (read through agent_cli.list_verbs) has drifted "
        f"from the registry: {sorted(cli_side ^ set(vreg.REGISTRY))}")
    # capability_search's _verb_table() writes a snapshot file; prove it round-trips the same set.
    from core.coord import capability_search as cs
    target = os.path.join(ROOT, "research", "in-flight", "_verbs_snapshot.txt")
    existed = os.path.exists(target)
    path = cs._verb_table()
    try:
        assert path, "capability_search could not produce its verb table (it fails soft -> None)"
        text = open(os.path.join(ROOT, path), encoding="utf-8").read().splitlines()
        assert len(text) == len(vreg.REGISTRY), (
            f"capability_search's verb table has {len(text)} rows, registry has {len(vreg.REGISTRY)}")
        for row in text:
            assert row.split("  ")[0].strip() in vreg.REGISTRY, f"unknown verb in table: {row!r}"
    finally:
        if not existed and os.path.exists(target):
            os.remove(target)          # leave the tree as we found it
    print(f"--- consumer: capability_search + compare ---\n  both see all "
          f"{len(vreg.REGISTRY)} verbs OK")


def test_the_mcp_twin_boots_and_knows_every_verb():
    """In a SUBPROCESS: `ai_setup_mcp` installs a process-wide stdout membrane at import."""
    _published()
    # NOT stdout: ai_setup_mcp installs a stdout membrane at import and routes python-level prints
    # from unarmed threads to stderr (the real stdout belongs to the JSON-RPC transport). Writing
    # the probe to a FILE is the only channel that does not depend on that membrane's rules --
    # discovered here the hard way, when the first draft's JSON landed in stderr and the pin died
    # on a JSONDecodeError rather than on anything to do with verbs.
    out_file = os.path.join(ROOT, ".mc_scratch", "_mcp_probe.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    code = (
        "import json, agent_cli, ai_setup_mcp\n"
        "open(%r, 'w').write(json.dumps({'n': len(agent_cli.list_verbs()),"
        " 'mcp_has_agent_cli': hasattr(ai_setup_mcp, 'agent_cli')}))\n" % out_file
    )
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, (
            "the MCP door no longer imports against agent_cli -- the second door onto the same verb "
            f"table would be dead: {r.stderr[-800:]}")
        payload = json.load(open(out_file, encoding="utf-8"))
    finally:
        if os.path.exists(out_file):
            os.remove(out_file)
    assert payload["n"] == len(vreg.REGISTRY), (
        f"the MCP door sees {payload['n']} verbs, the registry has {len(vreg.REGISTRY)}")
    assert payload["mcp_has_agent_cli"], "ai_setup_mcp must still import agent_cli (one table)"
    print(f"--- consumer: ai_setup_mcp ---\n  boots in a subprocess, sees all "
          f"{payload['n']} verbs OK")


# ------------------------------------------------- names read off agent_cli by other people's code
def _names_read_off_agent_cli(path):
    """Every `agent_cli.X` / `from agent_cli import X` a file performs."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "agent_cli":
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom) and node.module == "agent_cli":
            names.update(a.name for a in node.names if a.name != "*")
    return names


def test_hooks_and_the_out_of_tree_plugin_still_resolve_every_name_they_read():
    """The cross-fleet surface. `bridge.py` is DEPLOYED to a home directory, so a missing name here
    is not a traceback in this repo -- it is silence where the two halves of the fleet meet."""
    targets = []
    for rel in ("agent/harness/dsh_plugin/bridge.py",
                "agent/harness/hooks/claude_sessionend.py",
                "agent/harness/hooks/claude_stop.py",
                "agent/harness/hooks/cursor_sessionend.py",
                "scripts/hooks/claude_sessionend.py",
                "scripts/hooks/claude_stop.py",
                "scripts/hooks/cursor_sessionend.py",
                "ai_setup_mcp.py"):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            targets.append((rel, p))
    assert len(targets) >= 4, f"expected the hooks + bridge to exist, found {len(targets)}"
    missing = []
    for rel, p in targets:
        for name in sorted(_names_read_off_agent_cli(p)):
            if not hasattr(agent_cli, name):
                missing.append(f"{rel}: agent_cli.{name}")
    assert not missing, (
        "names read off agent_cli that no longer resolve -- for the out-of-tree bridge this is a "
        "silent version skew, not an error:\n  " + "\n  ".join(missing))
    print(f"--- cross-fleet names ---\n  {len(targets)} importer(s), every name resolves OK")


# ---------------------------------------------------------------------- the strangler's own rail
def test_the_moved_verb_keeps_its_identity_and_its_names():
    """`parsed.fn is agent_cli.cmd_orient` -- the premise every t084-style identity pin rests on."""
    _published()
    import verbs.groups.coord.scene as scene
    parsed = agent_cli.build_parser().parse_args(["orient", "--agent", "dsh_agent"])
    assert parsed.fn is agent_cli.cmd_orient, "set_defaults must bind the exported name"
    assert parsed.fn is scene.cmd_orient, "and it must be the ONE object, not a copy"
    spec = vreg.get_spec("orient")
    assert spec.moved and spec.module == "verbs.groups.coord.scene", spec
    assert spec.local is False, "orient's Local flag is declared, not guessed"
    print("--- strangler rail ---\n  orient: one object, declared local=False, module verbs.* OK")


def test_moved_verbs_are_minority_but_visible():
    """The extraction's progress bar, made a pin so it cannot quietly go to zero or to all."""
    _published()
    moved = vreg.moved()
    assert moved, "no verb has moved -- the registry's `moved` view is how the ratchet is read"
    assert len(moved) < len(vreg.REGISTRY), "unexpected: the whole door moved at once"
    for spec in moved:
        assert spec.fn is not None, f"a moved verb with no fn: {spec.name}"
    print(f"--- extraction progress ---\n  {len(moved)}/{len(vreg.REGISTRY)} verb bodies under "
          f"verbs/ ({', '.join(sorted(s.name for s in moved))}) OK")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except Exception as exc:                                          # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print("\nALL VERB-REGISTRY PINS PASSED" if not failures else f"\n{failures} FAILURE(S)")
    sys.exit(1 if failures else 0)
