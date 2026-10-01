"""Unit tests for tooling-upgrade/oracle.py and certify.py (plan G0.P3).

Every oracle component gets an EQUAL fixture and a DIFF fixture, built in tmp_path, so a
component that cannot tell "same" from "different" is caught before it judges a real change.
"""
import json
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tooling-upgrade"))
import oracle as O  # noqa: E402


def _o1(outcomes_by_id, reruns=None, skipped=0, collect_errors=()):
    runs = len(next(iter(outcomes_by_id.values())))
    tests = {}
    for nid, outs in outcomes_by_id.items():
        tests[nid] = {"outcomes": outs, "class": O.o1_class(outs)}
        if reruns and nid in reruns:
            tests[nid]["reruns"] = reruns[nid]
    counts = []
    for i in range(runs):
        c = {}
        for outs in outcomes_by_id.values():
            c[outs[i]] = c.get(outs[i], 0) + 1
        c["skipped"] = c.get("skipped", 0) + skipped
        counts.append(c)
    return {"runs": [{"counts": c, "collect_errors": list(collect_errors), "exitstatus": 0,
                      "duration_s": 1} for c in counts], "tests": tests}


# ----------------------------------------------------------------------------- O1

def test_o1_equal_when_outcomes_match():
    a = _o1({"t::a": ["passed"] * 3, "t::b": ["failed"] * 3})
    assert O.compare_o1(a, a) == []


def test_o1_flaky_failure_without_reproduction_is_equal():
    a = _o1({"t::a": ["passed"] * 3})
    b = _o1({"t::a": ["passed", "failed", "passed"]}, reruns={"t::a": ["passed", "passed"]})
    assert O.compare_o1(a, b) == []


def test_o1_diff_on_reproducible_regression():
    a = _o1({"t::a": ["passed"] * 3})
    b = _o1({"t::a": ["failed"] * 3}, reruns={"t::a": ["failed", "failed"]})
    keys = [k for k, _ in O.compare_o1(a, b)]
    assert "regressed:t::a" in keys
    assert "run-count" not in keys


def test_o1_diff_on_missing_id_and_more_skips():
    a = _o1({"t::a": ["passed"], "t::b": ["passed"]})
    b = _o1({"t::a": ["passed"]}, skipped=2)
    keys = [k for k, _ in O.compare_o1(a, b)]
    assert "id:t::b" in keys
    assert "skips" in keys
    assert "run-count" in keys


def test_o1_diff_on_more_collection_errors():
    a = _o1({"t::a": ["passed"]})
    b = _o1({"t::a": ["passed"]}, collect_errors=["tests/x.py"])
    assert [k for k, _ in O.compare_o1(a, b)] == ["collect-errors"]


def test_o1_classes():
    assert O.o1_class(["passed", "passed"]) == "stable-pass"
    assert O.o1_class(["failed", "error"]) == "stable-fail"
    assert O.o1_class(["passed", "failed"]) == "flaky"
    assert O.o1_class(["skipped"]) == "skip"


# ----------------------------------------------------------------------------- O2

def test_o2_formatting_only_change_is_ast_equal():
    a = b'def f( a,b ):\n    """Doc.   \n\n       More."""\n    return {"x":a,  "y":b}\n'
    b = b'def f(a, b):\n    """Doc.\n\n    More."""\n    return {"x": a, "y": b}\n'
    assert O.ast_fingerprint(a) == O.ast_fingerprint(b)


def test_o2_semantic_change_is_ast_diff():
    a = b"def f(a, b):\n    return a + b\n"
    b = b"def f(a, b):\n    return a - b\n"
    assert O.ast_fingerprint(a) != O.ast_fingerprint(b)


# ----------------------------------------------------------------------------- O3

def test_o3_equal_and_diff():
    a = {"modules": {"core.x": {"status": "OK"}, "core.y": {"status": "ImportError(optional-dep)"}}}
    assert O.compare_o3(a, a) == []
    b = {"modules": {"core.x": {"status": "error:ImportError"},
                     "core.y": {"status": "ImportError(optional-dep)"}}}
    assert [k for k, _ in O.compare_o3(a, b)] == ["import:core.x"]


def test_o3_partial_ignores_unprobed_modules():
    a = {"modules": {"core.x": {"status": "OK"}, "core.y": {"status": "OK"}}}
    b = {"modules": {"core.x": {"status": "OK"}}}
    assert O.compare_o3(a, b, partial=True) == []
    assert O.compare_o3(a, b) != []


# ----------------------------------------------------------------------------- O4

def _o4(help_text="usage: x", verbs=("boot",), schema=None):
    return {"help": {"x.py": {"rc": 0, "text": help_text}}, "verbs": {"x.py": list(verbs)},
            "mcp": {"via": "in-process", "tools": {"boot": {"name": "boot", "inputSchema":
                                                            schema or {"type": "object"}}}}}


def test_o4_equal_and_diff():
    assert O.compare_o4(_o4(), _o4()) == []
    keys = [k for k, _ in O.compare_o4(_o4(), _o4(help_text="usage: y", verbs=(),
                                                schema={"type": "object", "required": ["a"]}))]
    assert keys == ["help:x.py", "verbs:x.py", "mcp:boot"]


def test_normalize_text_is_path_and_whitespace_neutral(tmp_path):
    t = "usage:   %s/run.py   [-h]  \r\n\n\n" % tmp_path
    assert O.normalize_text(t, tmp_path) == "usage: <ROOT>/run.py [-h]"


# ----------------------------------------------------------------------------- O5

def _o5(names, sig="(a, b=1)", full=None, sensitive=()):
    return {"modules": {"core.x": {"mode": "runtime", "names": names,
                                   "sigs": {"f": {"bare": sig, "full": full or sig}}}},
            "sensitive": list(sensitive)}


def test_o5_equal_and_diff():
    assert O.compare_o5(_o5(["f", "g"]), _o5(["f", "g"])) == []
    keys = [k for k, _ in O.compare_o5(_o5(["f", "g"]), _o5(["f"], sig="(a)"))]
    assert keys == ["name:core.x.g", "sig:core.x.f"]


def test_o5_annotation_change_counts_only_in_sensitive_modules():
    a = _o5(["f"], full="(a: int)")
    b = _o5(["f"], full="(a: 'int')")
    assert O.compare_o5(a, b) == []
    a["sensitive"] = ["core.x"]
    assert [k for k, _ in O.compare_o5(a, b)] == ["annot:core.x.f"]


def test_o5_static_names_exclude_imports_but_keep_package_reexports(tmp_path):
    src = "import os\nfrom typing import Any\nX = 1\ndef f(): pass\nclass C: pass\n"
    tree = O.ast.parse(src)
    assert O.top_level_bindings(tree) == {"X", "f", "C"}
    assert O.top_level_bindings(tree, include_imports=True) == {"X", "f", "C", "os", "Any"}


# ----------------------------------------------------------------------------- O6 / O7

def test_o6_equal_and_diff():
    a = {"checkers": {"check_x": {"rc": 1, "crashed": False}}}
    assert O.compare_o6(a, a) == []
    assert O.compare_o6(a, {"checkers": {"check_x": {"rc": 0, "crashed": False}}}) == []
    worse = {"checkers": {"check_x": {"rc": 1, "crashed": True}}}
    assert [k for k, _ in O.compare_o6(a, worse)] == ["checker:check_x"]


def test_o7_equal_and_diff():
    a = {"commands": {"status": {"rc": 0, "lines": 100, "headings": ["Store:"]}}}
    near = {"commands": {"status": {"rc": 0, "lines": 108, "headings": ["Store:"]}}}
    assert O.compare_o7(a, near) == []
    far = {"commands": {"status": {"rc": 1, "lines": 150, "headings": []}}}
    assert len(O.compare_o7(a, far)) == 3


def test_headings_neutralise_numbers():
    assert O.headings("Lessons: \n## 12 agents\nplain line") == ["## 9 agents"]


# ----------------------------------------------------------------------------- O8

def test_o8_allowlist():
    assert O.allowlisted("pyproject.toml")
    assert O.allowlisted(".github/workflows/ci.yml")
    assert O.allowlisted("tooling-upgrade/snapshots/g0/O1.json")
    assert not O.allowlisted("core/data.json")
    assert not O.allowlisted("docs/ARCHITECTURE.md")


def test_o8_equal_and_diff():
    assert O.compare_o8({}, {"violations": []}) == []
    assert [k for k, _ in O.compare_o8({}, {"violations": ["core/x.json"]})] == ["path:core/x.json"]


# ----------------------------------------------------------------------------- O9

def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")


def test_o9_counts_every_assertion_form(tmp_path):
    _write(tmp_path, "tests/test_a.py", """
        import pytest
        def test_one(m):
            assert 1
            with pytest.raises(ValueError):
                pass
            m.assert_called_once()
            pytest.fail("x")
        class TestK:
            def test_two(self):
                self.assertEqual(1, 1)
        def helper():
            assert 0
    """)
    s = O.test_strength(tmp_path, ["tests/test_a.py"])
    assert s["tests"] == {"tests/test_a.py::test_one": 4, "tests/test_a.py::TestK::test_two": 1}
    assert O.compare_o9(s, s) == []


def test_o9_diff_on_weakened_or_missing_test():
    a = {"tests": {"t::a": 3, "t::b": 1}, "total": 4}
    b = {"tests": {"t::a": 2}, "total": 2}
    keys = [k for k, _ in O.compare_o9(a, b)]
    assert keys == ["test:t::a", "test:t::b", "total"]


# ----------------------------------------------------------------------------- O10

def test_o10_equal_and_diff():
    a = {"packages": {"core": 60.0, "agent": 40.0}}
    assert O.compare_o10(a, {"packages": {"core": 59.6, "agent": 41.0}}) == []
    assert [k for k, _ in O.compare_o10(a, {"packages": {"core": 59.4, "agent": 40.0}})] == ["cov:core"]


# ----------------------------------------------------------------------------- compare + register

def _snap(d, comps):
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"commit": "x"}), encoding="utf-8")
    for c, data in comps.items():
        (d / (c + ".json")).write_text(json.dumps(data), encoding="utf-8")


def test_compare_dirs_equal_diff_and_intended(tmp_path):
    base = {"O8": {"violations": []}, "O9": {"tests": {"t::a": 2}, "total": 2}}
    _snap(tmp_path / "a", base)
    _snap(tmp_path / "b", {"O8": {"violations": []}, "O9": {"tests": {"t::a": 1}, "total": 1}})
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "a", ["O2", "O8", "O9"], intended=[])
    assert ok and lines[-1] == "ORACLE: 3/3 EQUAL"
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "b", ["O8", "O9"], intended=[])
    assert not ok and lines[1].startswith("O9 DIFF 2")
    intended = [{"id": "IC-0001", "component": "O9", "key": "*", "reason": "test"}]
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "b", ["O8", "O9"], intended=intended)
    assert ok and lines[1] == "O9 EQUAL (intended: IC-0001)"


def test_missing_component_is_never_equal(tmp_path):
    _snap(tmp_path / "a", {"O8": {"violations": []}})
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "a", ["O8", "O9"], intended=[])
    assert not ok and lines[1].startswith("O9 MISSING")


# ----------------------------------------------------------------------------- inventory pieces

def test_dotted_name_and_history():
    assert O.dotted_name("core/foo/bar.py") == "core.foo.bar"
    assert O.dotted_name("core/foo/__init__.py") == "core.foo"
    assert O.dotted_name("research/in-flight/x.py") is None
    assert O.is_history("research/x.py") and not O.is_history("core/x.py")


def test_import_safe_refuses_scripts_that_run_on_import():
    assert O.import_safe(O.ast.parse("import sys\nsys.path.insert(0, '.')\nX = 1\n"))[0]
    assert not O.import_safe(O.ast.parse("def main(): pass\nmain()\n"))[0]
    assert not O.import_safe(O.ast.parse("for i in range(3):\n    print(i)\n"))[0]


def test_repo_graph_resolves_absolute_relative_and_sibling_imports(tmp_path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/a.py", "from . import b\nfrom .b import thing\n")
    _write(tmp_path, "pkg/b.py", "thing = 1\n")
    _write(tmp_path, "scripts/run.py", "import helper\nimport pkg.a\npkg.a.used\n")
    _write(tmp_path, "scripts/helper.py", "")
    files = ["pkg/__init__.py", "pkg/a.py", "pkg/b.py", "scripts/run.py", "scripts/helper.py"]
    g = O.RepoGraph(tmp_path, files)
    assert "pkg/b.py" in g.edges["pkg/a.py"]
    assert {"scripts/helper.py", "pkg/a.py"} <= g.edges["scripts/run.py"]
    assert g.ext_names["pkg/b.py"] == {"thing"}
    assert "used" in g.ext_names["pkg/a.py"]
    assert "pkg/a.py" in g.reverse()["pkg/b.py"]


def test_annotation_triggers_find_introspection():
    src = "from dataclasses import dataclass\n@dataclass\nclass C: x: int\n@mcp.tool()\ndef t(): pass\n"
    assert O.annotation_triggers(O.ast.parse(src)) == ["@*.tool decorator", "dataclass"]


def test_load_intended_parses_toml_blocks(tmp_path, monkeypatch):
    p = tmp_path / "INTENDED_CHANGES.md"
    p.write_text('# x\n\n```toml\nid = "IC-0001"\ncomponent = "O4"\nkey = "help:*"\n'
                 'reason = "launcher text"\n```\n', encoding="utf-8")
    monkeypatch.setattr(O, "INTENDED", p)
    assert O.load_intended() == [{"id": "IC-0001", "component": "O4", "key": "help:*",
                                  "reason": "launcher text"}]


@pytest.mark.parametrize("presence,clean,faulty,expected", [
    (1, 0, 1, "MISSED (gate absent)"),
    (0, 1, 1, "MISSED (gate red before the fault: rc=1)"),
    (0, 0, 1, "BIT"),
    (0, 0, 0, "MISSED"),
])
def test_drill_verdicts(tmp_path, monkeypatch, presence, clean, faulty, expected):
    """A drill BITes only when its gate exists, is green on the clean tree, and goes red on the
    fault -- so a later BIT means the gate caught the fault, not that it was absent or broken."""
    import contextlib
    import certify
    state = {"faulted": False}

    @contextlib.contextmanager
    def fake_tree():
        yield tmp_path

    monkeypatch.setattr(certify, "drill_tree", fake_tree)
    monkeypatch.setitem(certify.DRILLS, "DXX", (
        "fake", lambda t: state.update(faulted=True),
        lambda t: faulty if state["faulted"] else clean, lambda t: presence))
    assert certify.run_drill("DXX", "G7") == expected


@pytest.mark.parametrize("form,is_blanket", [
    ("noqa", True), ("noqa: F401", False), ("ruff: noqa", True), ("type: ignore", True),
    ("type: ignore[attr-defined]", False), ("pyright: basic", True),
    ("pyright: ignore[reportX]", False), ("pyright: strict", False),
])
def test_certify_blanket_suppression_forms(form, is_blanket):
    import certify
    assert certify.blanket(form) is is_blanket
