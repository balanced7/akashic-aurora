# pyright: strict
"""Unit tests for tooling-upgrade/oracle.py and certify.py (plan G0.P3).

Every oracle component gets an EQUAL fixture and a DIFF fixture, built in tmp_path, so a
component that cannot tell "same" from "different" is caught before it judges a real change.
"""

import json
import os
import sys
import textwrap
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tooling-upgrade"))
import certify
import oracle as O


def _o1(
    outcomes_by_id: dict[str, Sequence[str | None]],
    reruns: dict[str, list[str]] | None = None,
    skipped: int = 0,
    collect_errors: Sequence[str] = (),
) -> dict[str, Any]:
    runs = len(next(iter(outcomes_by_id.values())))
    tests: dict[str, dict[str, Any]] = {}
    for nid, outs in outcomes_by_id.items():
        tests[nid] = {"outcomes": outs, "class": O.o1_class(outs)}
        if reruns and nid in reruns:
            tests[nid]["reruns"] = reruns[nid]
    counts: list[dict[str | None, int]] = []
    for i in range(runs):
        c: dict[str | None, int] = {}
        for outs in outcomes_by_id.values():
            c[outs[i]] = c.get(outs[i], 0) + 1
        c["skipped"] = c.get("skipped", 0) + skipped
        counts.append(c)
    return {
        "runs": [
            {"counts": c, "collect_errors": list(collect_errors), "exitstatus": 0, "duration_s": 1} for c in counts
        ],
        "tests": tests,
    }


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
    b = {"modules": {"core.x": {"status": "error:ImportError"}, "core.y": {"status": "ImportError(optional-dep)"}}}
    assert [k for k, _ in O.compare_o3(a, b)] == ["import:core.x"]


def test_o3_partial_ignores_unprobed_modules():
    a = {"modules": {"core.x": {"status": "OK"}, "core.y": {"status": "OK"}}}
    b = {"modules": {"core.x": {"status": "OK"}}}
    assert O.compare_o3(a, b, partial=True) == []
    assert O.compare_o3(a, b) != []


# ----------------------------------------------------------------------------- O4


def _o4(
    help_text: str = "usage: x", verbs: Sequence[str] = ("boot",), schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "help": {"x.py": {"rc": 0, "text": help_text}},
        "verbs": {"x.py": list(verbs)},
        "mcp": {"via": "in-process", "tools": {"boot": {"name": "boot", "inputSchema": schema or {"type": "object"}}}},
    }


def test_o4_equal_and_diff():
    assert O.compare_o4(_o4(), _o4()) == []
    keys = [
        k
        for k, _ in O.compare_o4(
            _o4(), _o4(help_text="usage: y", verbs=(), schema={"type": "object", "required": ["a"]})
        )
    ]
    assert keys == ["help:x.py", "verbs:x.py", "mcp:boot"]


def test_normalize_text_is_path_and_whitespace_neutral(tmp_path: Path):
    t = f"usage:   {tmp_path}/run.py   [-h]  \r\n\n\n"
    assert O.normalize_text(t, tmp_path) == "usage: <ROOT>/run.py [-h]"


# ----------------------------------------------------------------------------- O5


def _o5(
    names: list[str], sig: str = "(a, b=1)", full: str | None = None, sensitive: Sequence[str] = ()
) -> dict[str, Any]:
    return {
        "modules": {"core.x": {"mode": "runtime", "names": names, "sigs": {"f": {"bare": sig, "full": full or sig}}}},
        "sensitive": list(sensitive),
    }


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


def test_o5_static_names_exclude_imports_but_keep_package_reexports(tmp_path: Path):
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
    far: dict[str, Any] = {"commands": {"status": {"rc": 1, "lines": 150, "headings": []}}}
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


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")


def test_o9_counts_every_assertion_form(tmp_path: Path):
    _write(
        tmp_path,
        "tests/test_a.py",
        """
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
    """,
    )
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


def _snap(d: Path, comps: dict[str, Any]) -> None:
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"commit": "x"}), encoding="utf-8")
    for c, data in comps.items():
        (d / (c + ".json")).write_text(json.dumps(data), encoding="utf-8")


def test_compare_dirs_equal_diff_and_intended(tmp_path: Path):
    base: dict[str, Any] = {"O8": {"violations": []}, "O9": {"tests": {"t::a": 2}, "total": 2}}
    _snap(tmp_path / "a", base)
    _snap(tmp_path / "b", {"O8": {"violations": []}, "O9": {"tests": {"t::a": 1}, "total": 1}})
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "a", ["O2", "O8", "O9"], intended=[])
    assert ok
    assert lines[-1] == "ORACLE: 3/3 EQUAL"
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "b", ["O8", "O9"], intended=[])
    assert not ok
    assert lines[1].startswith("O9 DIFF 2")
    intended = [{"id": "IC-0001", "component": "O9", "key": "*", "reason": "test"}]
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "b", ["O8", "O9"], intended=intended)
    assert ok
    assert lines[1] == "O9 EQUAL (intended: IC-0001)"


def test_compare_dirs_detail_lists_every_open_item(tmp_path: Path):
    """The summary names three items; `detail` gets all of them, so a CI log is enough to act on."""
    tests = {f"t::{i:d}": 1 for i in range(5)}
    _snap(tmp_path / "a", {"O9": {"tests": tests, "total": 5}})
    _snap(tmp_path / "b", {"O9": {"tests": {}, "total": 0}})
    detail: list[str] = []
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "b", ["O9"], intended=[], detail=detail)
    assert not ok
    assert lines[0].startswith("O9 DIFF")
    assert len(detail) == int(lines[0].split()[2])
    assert all(d.startswith("O9 ") for d in detail)


def test_missing_component_is_never_equal(tmp_path: Path):
    _snap(tmp_path / "a", {"O8": {"violations": []}})
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "a", ["O8", "O9"], intended=[])
    assert not ok
    assert lines[1].startswith("O9 MISSING")


# ----------------------------------------------------------------------------- inventory pieces


def test_dotted_name_and_history():
    assert O.dotted_name("core/foo/bar.py") == "core.foo.bar"
    assert O.dotted_name("core/foo/__init__.py") == "core.foo"
    assert O.dotted_name("research/in-flight/x.py") is None
    assert O.is_history("research/x.py")
    assert not O.is_history("core/x.py")


def test_import_safe_refuses_scripts_that_run_on_import():
    assert O.import_safe(O.ast.parse("import sys\nsys.path.insert(0, '.')\nX = 1\n"))[0]
    assert not O.import_safe(O.ast.parse("def main(): pass\nmain()\n"))[0]
    assert not O.import_safe(O.ast.parse("for i in range(3):\n    print(i)\n"))[0]


def test_repo_graph_resolves_absolute_relative_and_sibling_imports(tmp_path: Path):
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


def test_load_intended_parses_toml_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    p = tmp_path / "INTENDED_CHANGES.md"
    p.write_text(
        '# x\n\n```toml\nid = "IC-0001"\ncomponent = "O4"\nkey = "help:*"\nreason = "launcher text"\n```\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(O, "INTENDED", p)
    assert O.load_intended() == [{"id": "IC-0001", "component": "O4", "key": "help:*", "reason": "launcher text"}]


@pytest.mark.parametrize(
    ("presence", "clean", "faulty", "expected"),
    [
        (1, 0, 1, "MISSED (gate absent)"),
        (0, 1, 1, "MISSED (gate red before the fault: rc=1)"),
        (0, 0, 1, "BIT"),
        (0, 0, 0, "MISSED"),
    ],
)
def test_drill_verdicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, presence: int, clean: int, faulty: int, expected: str
) -> None:
    """A drill BITes only when its gate exists, is green on the clean tree, and goes red on the
    fault -- so a later BIT means the gate caught the fault, not that it was absent or broken."""
    import contextlib

    import certify

    state: dict[str, bool] = {"faulted": False}

    @contextlib.contextmanager
    def fake_tree() -> Generator[Path, None, None]:
        yield tmp_path

    monkeypatch.setattr(certify, "drill_tree", fake_tree)
    monkeypatch.setitem(
        certify.DRILLS,
        "DXX",
        (
            "fake",
            lambda t: state.update(faulted=True),
            lambda t: faulty if state["faulted"] else clean,
            lambda t: presence,
        ),
    )
    assert certify.run_drill("DXX", "G7") == expected


@pytest.mark.parametrize(
    ("form", "is_blanket"),
    [
        ("noqa", True),
        ("noqa: F401", False),
        ("ruff: noqa", True),
        ("type: ignore", True),
        ("type: ignore[attr-defined]", False),
        ("ty: ignore", True),
        ("ty: ignore[invalid-argument-type]", False),
        ("pyright: basic", True),
        ("pyright: ignore[reportX]", False),
        ("pyright: strict", False),
    ],
)
def test_certify_blanket_suppression_forms(form: str, is_blanket: bool) -> None:  # noqa: FBT001, RUF100  # pytest parametrize value, passed by pytest; FBT is ratchet-only
    import certify

    assert certify.blanket(form) is is_blanket


def test_later_goal_waits_for_its_predecessor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`certify.py G<n>` runs G<n>'s checks only once G<n-1> is CERTIFIED in the ledger."""
    import certify

    monkeypatch.setattr(certify, "HERE", tmp_path)
    (tmp_path / "LEDGER.md").write_text("| G0.P1 | DONE | | | | |\n", encoding="utf-8")
    assert not certify.prior_goal_certified(1)
    (tmp_path / "LEDGER.md").write_text("| G0 | CERTIFIED | a..b | | | |\n", encoding="utf-8")
    assert certify.prior_goal_certified(1)
    assert not certify.prior_goal_certified(2)


def test_every_comparator_runs_through_compare_dirs(tmp_path: Path):
    """compare_dirs calls each comparator as (a, b, partial); a signature drift in any one of
    them must fail here, not in the middle of a certificate."""
    fixtures: dict[str, Any] = {
        "O1": _o1({"t::a": ["passed"]}),
        "O3": {"modules": {"m": {"status": "OK"}}},
        "O4": _o4(),
        "O5": _o5(["f"]),
        "O6": {"checkers": {"c": {"rc": 0, "crashed": False}}},
        "O7": {"commands": {"k": {"rc": 0, "lines": 1, "headings": []}}},
        "O8": {"violations": []},
        "O9": {"tests": {"t::a": 1}, "total": 1},
        "O10": {"packages": {"core": 50.0}},
    }
    assert set(fixtures) == set(O.COMPARATORS)
    _snap(tmp_path / "a", fixtures)
    lines, ok = O.compare_dirs(tmp_path / "a", tmp_path / "a", intended=[])
    assert ok
    assert lines[-1] == "ORACLE: 10/10 EQUAL"


def test_oracle_records_are_not_archival_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """inventory.json and the snapshots name every path; if they counted as references, the
    second inventory run would find no ARCHIVAL file at all."""
    import subprocess

    _write(tmp_path, "research/old.py", "x = 1\n")
    _write(tmp_path, "core/live.py", "y = 2\n")
    _write(tmp_path, "tooling-upgrade/inventory.json", '{"files": {"research/old.py": {}}}\n')
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"],
    ):
        subprocess.run(cmd, cwd=tmp_path, check=True)
    inv = O.build_inventory(tmp_path)
    assert inv["archival"] == ["research/old.py"]


def test_public_id_hashes_parameter_text():
    nid = "tests/test_x.py::test_k[fixture-value]"
    pid = O.public_id(nid)
    assert pid.startswith("tests/test_x.py::test_k[#")
    assert "fixture-value" not in pid
    assert O.public_id(pid) == pid
    assert O.public_id("t.py::test_plain") == "t.py::test_plain"


def test_o1_volatile_parametrize_ids_compare_by_count():
    """Ids built from a timestamp differ every run; same count and passes is EQUAL, fewer is DIFF."""
    a: dict[str, Any] = {
        "runs": [{"counts": {"passed": 1}, "collect_errors": []}] * 2,
        "tests": {
            "t::v[#1]": {"outcomes": ["passed", None], "class": "stable-pass"},
            "t::v[#2]": {"outcomes": [None, "passed"], "class": "stable-pass"},
        },
    }
    assert "t::v" in O.volatile_bases(a)
    b: dict[str, Any] = {
        "runs": [{"counts": {"passed": 1}, "collect_errors": []}],
        "tests": {"t::v[#3]": {"outcomes": ["passed"], "class": "stable-pass"}},
    }
    assert O.compare_o1(a, b) == []
    b["tests"]["t::v[#3]"]["outcomes"] = ["failed"]
    assert [k for k, _ in O.compare_o1(a, b)] == ["volatile:t::v"]


# ----------------------------------------------------------------------------- G1 asserts


def test_dev_group_must_be_exactly_the_plan_list():
    import certify

    dev = [
        "ruff>=0.1",
        "basedpyright",
        "ty",
        "pytest>=8",
        "pytest-cov",
        "pytest-xdist",
        "pytest_randomly",
        "poethepoet",
        "prek",
        "deptry",
    ]
    good = {"project": {"dependencies": ["redis>=5"]}, "dependency-groups": {"dev": dev, "ml": ["x"], "browser": ["y"]}}
    assert certify.dev_group_problems(good) == []
    bad = {
        "project": {"dependencies": ["pytest>=8", "pre-commit>=3"]},
        "dependency-groups": {"dev": [*dev[1:], "black"], "ml": []},
    }
    msgs = " | ".join(certify.dev_group_problems(bad))
    for frag in ("dev lacks ruff", "dev has black", "still has tool pytest", "pre-commit", "browser missing"):
        assert frag in msgs


def test_uv_settings():
    import certify

    good = {
        "tool": {
            "uv": {"package": False, "required-version": ">=0.12", "exclude-newer": "7 days", "default-groups": ["dev"]}
        }
    }
    assert certify.uv_settings_problems(good) == []
    assert len(certify.uv_settings_problems({"tool": {"uv": {"package": False, "required-version": ">=0.11"}}})) == 3


def test_gate_members_order_and_ignore_fail():
    import certify

    ok = {"gate": {"sequence": ["lock-check", "deps", "guardrails", "test-fast"]}}
    assert certify.gate_problems(ok, ["lock-check", "test-fast"]) == []
    assert certify.gate_problems(ok, ["fmt-check"]) == ["gate lacks fmt-check"]
    wrong = {"gate": {"sequence": ["deps", "lock-check", "echo"], "ignore_fail": True}}
    msgs = " | ".join(certify.gate_problems(wrong, []))
    assert "'echo' is not a plan gate task" in msgs
    assert "order" in msgs
    assert "ignore_fail" in msgs
    assert certify.gate_problems({"gate": {"shell": "true || true"}}, []) == ["gate is not a sequence task"]


def test_sha_pins(tmp_path: Path):
    import certify

    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "jobs:\n  a:\n    steps:\n"
        "      - uses: actions/checkout@" + "a" * 40 + "  # v4.2.2\n"
        "      - uses: ./local-action\n"
        "      - uses: docker://alpine:3\n"
        "      - uses: actions/setup-python@v5\n",
        encoding="utf-8",
    )
    problems = certify.sha_pin_problems(tmp_path)
    assert len(problems) == 1
    assert "actions/setup-python@v5" in problems[0]


def test_verify_checkout_catches_a_flipped_byte(tmp_path: Path):
    """A file that differs from its commit after checkout (one bit flipped: '}' -> 'u') must stop
    the run; git's stat cache alone would call the tree clean."""
    import subprocess

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
    )

    def g(*a: str) -> None:
        subprocess.run(["git", *a], cwd=tmp_path, env=env, check=True, capture_output=True)

    g("init", "-q")
    f = tmp_path / "m.py"
    f.write_text('x = f"{a}{b}"\n', encoding="utf-8")
    g("add", "m.py")
    g("commit", "-q", "-m", "c")
    O.verify_checkout(tmp_path)  # pristine: passes
    st = f.stat()
    f.write_bytes(f.read_bytes().replace(b"}{", b"u{"))
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))  # same size and mtime: stat cache is fooled
    with pytest.raises(RuntimeError, match="does not match its commit"):
        O.verify_checkout(tmp_path)


def test_oracle_env_drops_an_inherited_ai_setup(monkeypatch: pytest.MonkeyPatch):
    """oracle_env strips inherited AI_SETUP/isolation/Redis-port vars and pins REDIS_DB to 15."""
    # CI sets AI_SETUP to the checkout; the suite runs in a copy, where an AI_SETUP naming
    # another directory would read as "already isolated" to tests/isolate_canonical.py
    monkeypatch.setenv("AI_SETUP", "/somewhere/else")
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    monkeypatch.setenv("REDIS_PORT", "16379")
    env = O.oracle_env()
    assert "AI_SETUP" not in env
    assert "_AISETUP_TEST_ISOLATED" not in env
    assert "REDIS_PORT" not in env
    assert env["REDIS_DB"] == "15"


def test_written_paths_sees_a_rewrite_with_identical_bytes(tmp_path: Path):
    """written_paths reports a same-bytes rewrite (by mtime) and a new untracked file."""
    # O4's side-effect probe: a generator that ignores --help and rewrites its doc is still a
    # side effect when the doc is already current (git status alone shows nothing)
    O.git("init", "-q", cwd=tmp_path)
    doc = tmp_path / "DOC.md"
    doc.write_text("same\n", encoding="utf-8")
    (tmp_path / "keep.md").write_text("k\n", encoding="utf-8")
    O.git("add", ".", cwd=tmp_path)
    written, stamps = O.written_paths(tmp_path, {})
    assert written == set()
    st = doc.stat()
    doc.write_text("same\n", encoding="utf-8")
    os.utime(doc, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    (tmp_path / "new.txt").write_text("n\n", encoding="utf-8")
    written, _ = O.written_paths(tmp_path, stamps)
    assert written == {"DOC.md", "new.txt"}


_UVPY = ["uv", "run", "--frozen", "python", "-m", "pytest"]
_OLD_CHECK: dict[str, Any] = {
    "id": "G9.t",
    "phase": "G9.P1",
    "cmd": [*_UVPY, "-q", "-p", "no:randomly", "tests/x.py"],
    "expect": 0,
    "expect_stdout": "passed",
}
_NEW_CMD = [*_UVPY, "-p", "no:randomly", "tests/x.py"]
_LEDGER = "- **D-G9-1.** G9.t2 supersedes G9.t: the registered cmd doubled -q.\n"


def _new_check(**over: Any) -> dict[str, Any]:
    new = {**_OLD_CHECK, "id": "G9.t2", "cmd": list(_NEW_CMD)}
    new.update(over)
    return new


@pytest.fixture
def pinned(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Certify with PINNED_SUPERSESSIONS replaced by the single G9.t -> G9.t2 test pair."""
    monkeypatch.setattr(
        certify,
        "PINNED_SUPERSESSIONS",
        {("G9", "G9.t"): ("G9.t2", tuple(_OLD_CHECK["cmd"]), tuple(_NEW_CMD))},
    )
    return certify


def test_supersede_accepts_the_pinned_pair(pinned: Any):
    """The pinned pair, ledgered and registered in order, yields no problems."""
    assert pinned.supersede_verdict("G9", _OLD_CHECK, _new_check(), _LEDGER, 0, 1) == []


@pytest.mark.parametrize(
    ("goal", "over", "ledger", "old_at", "new_at", "needle"),
    [
        ("G8", {}, _LEDGER, 0, 1, "not a pinned supersession"),  # same ids, another goal
        ("G9", {"id": "G9.t3"}, _LEDGER, 0, 1, "not a pinned supersession"),  # another successor
        ("G9", {"cmd": [*_UVPY, "-p", "no:randomly"]}, _LEDGER, 0, 1, "not the pinned argv"),
        ("G9", {"cmd": [*_UVPY, "-q", "-p", "no:randomly", "tests/x.py"]}, _LEDGER, 0, 1, "not the pinned argv"),
        ("G9", {"expect_stdout": "."}, _LEDGER, 0, 1, "expect_stdout differs"),
        ("G9", {"expect": 1}, _LEDGER, 0, 1, "expect differs"),
        ("G9", {"phase": "G9.P2"}, _LEDGER, 0, 1, "phase differs"),
        ("G9", {"timeout_s": 60}, _LEDGER, 0, 1, "timeout_s differs"),
        ("G9", {}, "no decision here\n", 0, 1, "LEDGER"),
        ("G9", {}, "- G9.t2-x and G9.tt only\n", 0, 1, "LEDGER"),
        ("G9", {}, _LEDGER, 1, 1, "later commit"),
        ("G9", {}, _LEDGER, 0, -1, "later commit"),
    ],
)
def test_supersede_rejects_anything_but_the_pinned_pair(
    pinned: Any, *, goal: str, over: dict[str, Any], ledger: str, old_at: int, new_at: int, needle: str
):
    """Any deviation from the pinned pair (goal, ids, argv, fields, ledger, order) is named."""
    problems = pinned.supersede_verdict(goal, _OLD_CHECK, _new_check(**over), ledger, old_at, new_at)
    assert any(needle in p for p in problems), problems


@pytest.mark.parametrize(
    ("old_cmd", "new_cmd"),
    [
        (["git", "diff", "--quiet", "HEAD"], ["git", "diff", "HEAD"]),
        (
            ["uv", "run", "--with", "pytest", "git", "diff", "--quiet", "HEAD"],
            ["uv", "run", "--with", "pytest", "git", "diff", "HEAD"],
        ),
        ([*_UVPY, "-p", "no:randomly", "--", "tests", "-q"], [*_UVPY, "-p", "no:randomly", "--", "tests"]),
        ([*_UVPY, "-q", "-p", "no:randomly", "tests/x.py"], _NEW_CMD),  # the shape of a legit drop
    ],
)
def test_supersede_rejects_every_unpinned_pair(old_cmd: list[str], new_cmd: list[str]):
    """The real table (only G5.hook-stage-test is pinned) rejects every other dropped flag."""
    old = {**_OLD_CHECK, "cmd": old_cmd}
    new = {**_OLD_CHECK, "id": "G9.t2", "cmd": new_cmd}
    assert any("not a pinned supersession" in p for p in certify.supersede_verdict("G9", old, new, _LEDGER, 0, 1))


def test_supersessions_reject_an_unknown_target_and_a_second_successor(
    pinned: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A second successor and an unknown supersedes target are problems; the first pair stays valid."""
    (tmp_path / "LEDGER.md").write_text(_LEDGER + "- G9.t3 supersedes G9.t too\n", encoding="utf-8")
    monkeypatch.setattr(pinned, "HERE", tmp_path)
    order = {"G9.t": 0, "G9.t2": 1, "G9.t3": 2}

    def first_registered(_goal: str, check_id: str) -> int:
        return order.get(check_id, -1)

    monkeypatch.setattr(pinned, "_first_registered", first_registered)
    two = {"check": [_OLD_CHECK, _new_check(supersedes="G9.t"), _new_check(id="G9.t3", supersedes="G9.t")]}
    valid, problems = pinned.supersessions("G9", two)
    assert valid == {"G9.t": "G9.t2"}
    assert any("superseded twice" in p for p in problems)
    valid, problems = pinned.supersessions("G9", {"check": [_new_check(supersedes="G9.nope")]})
    assert valid == {}
    assert any("unknown check G9.nope" in p for p in problems)


def test_the_pinned_g5_pair_matches_its_checks_file():
    """The real G5 checks file supersedes exactly the pinned G5 pair, with no problems."""
    valid, problems = certify.supersessions("G5", certify.load_checks("G5"))
    assert (valid, problems) == ({"G5.hook-stage-test": "G5.hook-stage-test-summary"}, [])


_PYPROJECT = """[tool.ruff]
extend-exclude = [
    "research/a/b.py",
]
[tool.deptry]
extend_exclude = ["^docs/"]
known_first_party = ["research/c/d.py"]
[tool.basedpyright]
exclude = ["research/a/b.py", "research/e/f.py"]
"""


@pytest.mark.parametrize(
    ("extra", "hidden", "visible"),
    [
        ("", {"research/a/b.py", "research/e/f.py"}, {"research/c/d.py"}),
        ('[tool.poe.tasks]\nx = "python research/a/b.py"\n', {"research/e/f.py"}, {"research/a/b.py"}),
        ("# see research/e/f.py\n", {"research/a/b.py"}, {"research/e/f.py"}),
        ('[tool.pytest.ini_options]\ntestpaths = ["research/e/f.py"]\n', {"research/a/b.py"}, {"research/e/f.py"}),
    ],
)
def test_only_exclusion_list_entries_are_discounted(extra: str, hidden: set[str], visible: set[str]):
    """A path counts as referenced unless every mention of it is an exclusion-list entry."""
    only_paths, _ = O.only_in_exclusions("pyproject.toml", _PYPROJECT + extra)
    assert only_paths == hidden
    assert not (only_paths & visible)


def test_exclusion_entries_apply_to_pyproject_only():
    """The same text in any other file is never discounted."""
    assert O.only_in_exclusions("docs/notes.toml", _PYPROJECT) == (set(), set())


_PHYS = b"# Physics\n\n> Derived at c0e78d38. A bound\n\nbody\n"
_REPLAYED = _PHYS.replace(b"c0e78d38", b"00c842bf")


def _pinned_repo(tmp_path: Path, replayed: bytes) -> tuple[Path, str]:
    """Commit docs/PHYSICS.md as `_PHYS`, then stage `replayed` over it; return (repo, commit)."""
    (tmp_path / "docs").mkdir()
    phys = tmp_path / "docs" / "PHYSICS.md"
    phys.write_bytes(_PHYS)
    ident = ("-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false")
    O.git("init", "-q", cwd=tmp_path)
    O.git("add", "-A", cwd=tmp_path)
    O.git(*ident, "commit", "-q", "-m", "c", cwd=tmp_path)
    sha = O.git("rev-parse", "HEAD", cwd=tmp_path).strip()
    phys.write_bytes(replayed)
    O.git("add", "-A", cwd=tmp_path)
    return tmp_path, sha


@pytest.mark.parametrize(
    ("replayed", "ok"),
    [
        (_REPLAYED, True),  # the pinned stamp swap, nothing else
        (_REPLAYED.replace(b"body", b"bodY"), False),  # another change rides along
        (_REPLAYED.replace(b"\n\nbody", b"\n\rbody"), False),  # a lone CR
        (_REPLAYED.replace(b"body", b"b\xffdy"), False),  # an invalid UTF-8 byte
        (_REPLAYED + _REPLAYED, False),  # the replayed stamp twice
        (_PHYS.replace(b"c0e78d38", b"0dc8e086"), False),  # some other stamp
    ],
)
def test_a_pinned_replay_differs_only_by_its_literal_stamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, replayed: bytes, ok: bool
):
    """The one pinned replay exception swaps one literal stamp; the tree must then match exactly."""
    repo, sha = _pinned_repo(tmp_path, replayed)
    monkeypatch.setattr(
        certify,
        "PINNED_REPLAY_STAMPS",
        {sha: ("docs/PHYSICS.md", b"> Derived at 00c842bf.", b"> Derived at c0e78d38.")},
    )
    assert not certify.same_tree(repo, sha)
    assert (certify.apply_pinned_stamp(repo, sha) and certify.same_tree(repo, sha)) is ok


def test_an_unpinned_replay_gets_no_stamp_tolerance(tmp_path: Path):
    """Without a pin, a replay that differs only by the stamp still differs."""
    repo, sha = _pinned_repo(tmp_path, _REPLAYED)
    assert not certify.apply_pinned_stamp(repo, sha)
    assert not certify.same_tree(repo, sha)


def test_an_escaped_exclusion_entry_discounts_nothing():
    """With any backslash in pyproject.toml, parsed entries may differ from their raw text: fail closed."""
    text = '[tool.ruff]\nextend-exclude = ["research\\\\a\\\\b.py"]\n[tool.poe.tasks]\nx = "python research/a/b.py"\n'
    assert O.only_in_exclusions("pyproject.toml", text) == (set(), set())
