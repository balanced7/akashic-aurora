"""The mutation runner (W128, amended by W236).

WHY THIS EXISTS. docs/method-baseline-2026-07.md asks EVERY slice to mutation-test its pins.
Until now scripts/ held no runner, so every seat hand-rolled the same patch-run-restore loop
-- and the hand-roll produced SIX false results across two sessions, every one a harness
failure rather than a subject failure, at least two of them a wrong CONCLUSION rather than a
retry. W128 was filed 2026-08-04.

A MUTATION HARNESS HAS TWO HALVES AND BOTH CAN LIE.

  THE APPLIER. Did the patch reach the file? sed eats backslash escapes, so \\u, \\t and \\n
  cannot survive into a file at all; an anchor carrying a comment or a newline matches
  nothing; a mutant that is a SyntaxError makes pytest emit a COLLECTION error rather than
  FAILED lines. Each of those is a mutation that never ran, and a naive runner calls it
  SURVIVED -- which reads as "your pin is blind" when the truth is "your harness is". That is
  W236, and it is why NULL-APPLY is a verdict rather than a footnote.

  THE DETECTOR. Did the runner read the test result correctly? This half is in neither wish
  and cost a full round on 2026-10-02: a harness that scored the suite with
  `" failed" not in output` reported all six of its mutations as SURVIVED. Under
  `-q --no-header` pytest prints no lowercase counts line at all -- a clean run is about
  eighty characters of dots, a failing run ends in UPPERCASE FAILED lines -- so the detector
  returned the same answer in both directions. The mutations were perfect.
  SO: THE VERDICT COMES FROM THE EXIT CODE. Never from matching output text. Output is for
  humans; the exit code is the contract.

THE THIRD SPECIES, W128's own: NULL-SEMANTIC. The patch lands, parses, and changes nothing
observable -- T159's M1 survived because EXCEPTIONS is a subset of unreachable, so the clause
removed zero modules. Semantic nullity is undecidable in general and this runner does not
pretend otherwise: a mutation may DECLARE a `probe`, an expression whose value must move if
the mutation is live. When no probe is declared the runner cannot rule semantic nullity out,
so every SURVIVED says so explicitly. W128's closing line is the requirement -- "a report
that cannot say 'this mutation changed nothing' will eventually be used to delete a good pin".

TWO-SIDED SELF-CALIBRATION, BEFORE ANY VERDICT IS BELIEVED. A harness that cannot fail loudly
is the same defect class as a pin that cannot fail.
    BASELINE      the target must be green unmutated, or no verdict is readable
    CANARY        an injected guaranteed-failure must read RED, or the detector is blind and
                  every SURVIVED this run is a lie
    NULL CONTROL  an injected provable no-op must read GREEN, or the suite is
                  non-deterministic and every CAUGHT this run is a coin flip
Any of the three failing REFUSES the run rather than emitting verdicts nobody should trust.

THE TELL THIS RUNNER EXISTS TO CATCH: a uniform verdict. Six of six surviving, or zero of
six, is a statement about the harness far more often than about the pins.

Spec lives in a FILE, never inline (W236): sed and shell quoting are two of the three ways
the applier has already lied here.

    {"tests": "tests/test_foo.py",
     "mutations": [
       {"label": "drop the lock",
        "file":  "agent_cli.py",
        "anchor": "with _exclusive(path):",     # must appear EXACTLY once
        "replacement": "with _nullcontext():",
        "expect": "test_name_substring",         # optional: WHICH pin should fire
        "probe":  "__import__('m').f(1)"}        # optional: rules out NULL-SEMANTIC
     ]}

Usage::

    py scripts/mutate.py --spec spec.json [--tests tests/test_foo.py] [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TIMEOUT = 600

CAUGHT = "CAUGHT"
CAUGHT_BY_OTHER = "CAUGHT-BY-OTHER"
SURVIVED = "SURVIVED"
NULL_APPLY = "NULL-APPLY"
NULL_SEMANTIC = "NULL-SEMANTIC"

_NO_PROBE_NOTE = ("no probe declared, so semantic nullity could NOT be ruled out -- this may "
                  "be an unguarded line or a mutation that changes nothing; declare a probe "
                  "to tell them apart")


def _run_tests(tests: str, repo: Path, timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, str]:
    """Run the target and return (returncode, output).

    THE RETURN CODE IS THE VERDICT. The text comes back only so a human can read why, and
    callers must never score on it -- see the module docstring. Module-level so tests can
    substitute a detector and prove the calibration refuses a blind one.
    """
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", tests, "-q", "--no-header", "-p", "no:randomly", "-rf"],
            capture_output=True, text=True, cwd=str(repo), timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        # A timeout is NOT a pass. Scoring it green is the blind-detector species again.
        return 124, "TIMEOUT after %ss" % timeout


_probe_seq = 0


def _probe_value(expr: str, repo: Path, timeout: int = 120) -> Tuple[bool, str]:
    """Evaluate a declared probe in a FRESH interpreter rooted at the repo.

    Fresh because the mutated module must actually be re-imported; evaluating in-process
    would read whatever is already in sys.modules and report 'unchanged' for every mutation.

    AND A FRESH BYTECODE CACHE, which is NOT optional and was found by this module's own
    pins. A subprocess is not enough: Python invalidates a .pyc by (mtime, size), and a
    mutation like `n * 2` -> `n * 3` changes NEITHER -- same byte length, same second. The
    probe then re-imports the STALE bytecode and reports the same value before and after, so
    every live mutation with a same-length replacement scores NULL-SEMANTIC. That is a new
    false-verdict species inside the very tool built to eliminate them, and it is silent.

    PYTHONPYCACHEPREFIX gives each probe its own cache directory outside the repo, so the
    before-probe and the after-probe cannot share bytecode and nothing is left behind. -B
    alone would not do it: it stops WRITING a .pyc, not reading one that already exists.
    """
    global _probe_seq
    _probe_seq += 1
    code = ("import sys; sys.path.insert(0, %r)\n"
            "try:\n    print(repr(%s))\n"
            "except Exception as e:\n    print('PROBE-RAISED:' + type(e).__name__ + ':' + str(e))\n"
            % (str(repo), expr))
    import tempfile
    cache = os.path.join(tempfile.gettempdir(), "mutate_pyc_%d_%d" % (os.getpid(), _probe_seq))
    env = {**os.environ, "PYTHONPYCACHEPREFIX": cache, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                           cwd=str(repo), timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "PROBE-TIMEOUT"
    if r.returncode != 0:
        return False, "PROBE-ERROR:" + (r.stderr or "").strip()[-200:]
    return True, (r.stdout or "").strip()


def _calibrate(tests: str, repo: Path, scratch_file: Optional[Path],
               timeout: int) -> Dict[str, Any]:
    """Prove the detector can say RED and can say GREEN before any verdict is believed."""
    out: Dict[str, Any] = {"ok": False, "baseline": None, "canary": None, "null_control": None}

    rc, _ = _run_tests(tests, repo, timeout)
    out["baseline"] = {"returncode": rc, "green": rc == 0}
    if rc != 0:
        out["why"] = ("baseline is RED before any mutation -- a verdict against an already "
                      "failing target is unreadable. Fix or narrow --tests first.")
        return out

    # CANARY: a guaranteed failure must read as red, or the detector is blind.
    canary = repo / "test__mutate_canary_.py"
    try:
        canary.write_text("def test__mutate_canary():\n    assert False\n", encoding="utf-8")
        crc, _ = _run_tests(canary.name, repo, timeout)
    finally:
        try:
            canary.unlink()
        except OSError:
            pass
    out["canary"] = {"returncode": crc, "went_red": crc != 0}
    if crc == 0:
        out["why"] = ("CANARY NOT CAUGHT: an injected guaranteed-failure reported green, so "
                      "the detector cannot see red. Every SURVIVED in this run would be a "
                      "lie. Refusing to report verdicts.")
        return out

    # NULL CONTROL: a provable no-op must stay green, or the suite is non-deterministic.
    if scratch_file and scratch_file.exists():
        original = scratch_file.read_bytes()
        try:
            scratch_file.write_bytes(original + b"\n# mutate.py null control\n")
            nrc, _ = _run_tests(tests, repo, timeout)
        finally:
            scratch_file.write_bytes(original)
    else:
        nrc, _ = _run_tests(tests, repo, timeout)
    out["null_control"] = {"returncode": nrc, "stayed_green": nrc == 0}
    if nrc != 0:
        out["why"] = ("NULL CONTROL WENT RED: a provable no-op reddened the target, so the "
                      "suite is non-deterministic and every CAUGHT in this run would be a "
                      "coin flip. Refusing to report verdicts.")
        return out

    out["ok"] = True
    return out


def _apply_check(src: str, anchor: str, replacement: str) -> Optional[str]:
    """Return a NULL-APPLY reason, or None when the patch can legitimately land."""
    if not anchor:
        return "no anchor given -- nothing to replace"
    n = src.count(anchor)
    if n == 0:
        return ("anchor not found in the file -- the patch would have silently no-opped "
                "(this says NOTHING about the pins)")
    if n > 1:
        return ("anchor is ambiguous: %d matches, so the runner cannot know which site it "
                "mutated" % n)
    if replacement == anchor:
        return "replacement is identical to the anchor -- the file would be unchanged"
    return None


def _mutated_line(text: str, replacement: str) -> str:
    for line in text.splitlines():
        if replacement.strip() and replacement.strip() in line:
            return line.strip()
    return ""


def run_spec(spec: Dict[str, Any], tests: Optional[str] = None,
             repo: Optional[Path] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Run every mutation in `spec` and return {'calibration', 'results'}.

    Results is EMPTY when calibration fails -- refusing is the point, because a verdict from
    an uncalibrated harness is worse than no verdict: it gets believed.
    """
    repo = Path(repo or Path(__file__).resolve().parents[1])
    tests = tests or spec.get("tests")
    if not tests:
        raise ValueError("no test target: pass --tests or put 'tests' in the spec")
    muts: List[Dict[str, Any]] = list(spec.get("mutations") or [])

    first = next((repo / m["file"] for m in muts if m.get("file")), None)
    cal = _calibrate(tests, repo, first, timeout)
    if not cal["ok"]:
        return {"calibration": cal, "results": []}

    results: List[Dict[str, Any]] = []
    for m in muts:
        label = m.get("label") or m.get("anchor", "")[:40]
        rel = m.get("file", "")
        target = repo / rel
        row: Dict[str, Any] = {"label": label, "file": rel, "verdict": NULL_APPLY,
                               "detail": "", "mutated_line": "", "returncode": None,
                               "semantic_null_ruled_out": None}

        if not target.is_file():
            row["detail"] = "no such file: %s" % rel
            results.append(row)
            continue

        before = target.read_bytes()
        src = before.decode("utf-8", "replace")
        anchor, replacement = m.get("anchor", ""), m.get("replacement", "")

        reason = _apply_check(src, anchor, replacement)
        if reason:
            row["detail"] = reason
            results.append(row)
            continue

        probe = m.get("probe")
        probe_before = None
        if probe:
            okb, probe_before = _probe_value(probe, repo)
            if not okb:
                probe = None            # an unusable probe must not masquerade as evidence
                row["detail"] = "probe unusable before mutation (%s); " % probe_before

        try:
            target.write_text(src.replace(anchor, replacement, 1), encoding="utf-8", newline="")
            after_bytes = target.read_bytes()
            after = after_bytes.decode("utf-8", "replace")

            if after_bytes == before:
                row["detail"] += "the file is byte-identical after the write"
                continue
            if replacement and replacement not in after:
                row["detail"] += ("the mutant token is NOT in the file after writing -- an "
                                  "escaping layer ate it")
                continue
            if target.suffix == ".py":
                try:
                    ast.parse(after)
                except SyntaxError as e:
                    row["detail"] += ("the mutant does not parse (%s line %s) -- pytest would "
                                      "report a COLLECTION error, which a FAILED-line parser "
                                      "scores as survived" % (e.msg, e.lineno))
                    continue

            row["mutated_line"] = _mutated_line(after, replacement)

            if probe:
                oka, probe_after = _probe_value(probe, repo)
                if oka and probe_after == probe_before:
                    row["verdict"] = NULL_SEMANTIC
                    row["semantic_null_ruled_out"] = False
                    row["detail"] += ("the mutant LANDED but the declared probe did not move "
                                      "(%s both before and after) -- it changes nothing "
                                      "observable, so this is not evidence about any pin"
                                      % probe_after[:80])
                    continue
                row["semantic_null_ruled_out"] = bool(oka)

            rc, out = _run_tests(tests, repo, timeout)
            row["returncode"] = rc                       # THE VERDICT IS THE EXIT CODE
            if rc == 0:
                row["verdict"] = SURVIVED
                if row["semantic_null_ruled_out"] is None:
                    row["semantic_null_ruled_out"] = False
                    row["detail"] += ("nothing guards this line. " + _NO_PROBE_NOTE)
                else:
                    row["detail"] += ("nothing guards this line, and the declared probe moved, "
                                      "so it is genuinely unguarded rather than a no-op")
            else:
                expect = m.get("expect")
                if not expect or expect in out:
                    row["verdict"] = CAUGHT
                    row["detail"] += ("%s fired" % expect) if expect else "the target went red"
                else:
                    row["verdict"] = CAUGHT_BY_OTHER
                    row["detail"] += ("the target went red but %r did not fire -- the "
                                      "expectation or the mutation is wrong" % expect)
        finally:
            target.write_bytes(before)
            if target.read_bytes() != before:            # a leaking harness is worse than none
                raise RuntimeError("RESTORE FAILED for %s -- the tree is left mutated" % rel)
            # Plain append: an identity-free `if row not in results` would compare dicts and
            # silently DROP the second of two mutations that happened to score identically.
            results.append(row)

    return {"calibration": cal, "results": results}


def render(report: Dict[str, Any]) -> str:
    cal = report["calibration"]
    lines: List[str] = []
    if not cal["ok"]:
        lines.append("REFUSED -- the harness is not calibrated, so no verdict is trustworthy.")
        lines.append("  " + str(cal.get("why", "")))
        for k in ("baseline", "canary", "null_control"):
            if cal.get(k) is not None:
                lines.append("    %-13s %s" % (k, cal[k]))
        return "\n".join(lines)

    lines.append("calibrated: baseline green, canary caught, null control clean")
    lines.append("")
    lines.append("%-44s %-15s %s" % ("mutation", "verdict", "detail"))
    lines.append("-" * 112)
    counts: Dict[str, int] = {}
    for r in report["results"]:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        lines.append("%-44s %-15s %s" % (r["label"][:44], r["verdict"], r["detail"][:60]))
        if r.get("mutated_line"):
            lines.append("%-44s %-15s | %s" % ("", "", r["mutated_line"][:80]))
    lines.append("")
    lines.append("  " + ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    uniform = len(counts) == 1 and len(report["results"]) > 2
    if uniform:
        lines.append("  UNIFORM VERDICT across %d mutations. That is a statement about the "
                     "harness far more often than about the pins -- re-run one by hand before "
                     "believing it." % len(report["results"]))
    if counts.get(SURVIVED):
        lines.append("  SURVIVED is not 'the pin is blind' unless a probe ruled out "
                     "NULL-SEMANTIC; check semantic_null_ruled_out per row.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="mutation runner (W128/W236)")
    ap.add_argument("--spec", required=True, help="path to the mutation spec JSON")
    ap.add_argument("--tests", help="pytest target (overrides the spec's 'tests')")
    ap.add_argument("--repo", help="repo root (default: this file's parent)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--json", action="store_true", help="emit the raw report")
    a = ap.parse_args(argv)

    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    if isinstance(spec, list):                       # bare list of mutations is fine
        spec = {"mutations": spec}
    report = run_spec(spec, tests=a.tests, repo=Path(a.repo) if a.repo else None,
                      timeout=a.timeout)
    print(json.dumps(report, indent=2) if a.json else render(report))
    if not report["calibration"]["ok"]:
        return 2
    bad = [r for r in report["results"] if r["verdict"] in (SURVIVED, NULL_APPLY)]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
