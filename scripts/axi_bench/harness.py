#!/usr/bin/env python3
"""Measure one CLI verb before and after its AXI change, instead of assuming it improved.

    uv run python -m scripts.axi_bench.harness <verb> [--before <git ref>] [--repeats 3]

WHAT IT MEASURES, for the code at --before (default BASELINE, the fork's master before any AXI
change) and the working tree:

  accuracy     A reader model sees ONLY the verb's stdout -- no repo, no tools -- and answers
               fixed questions whose answers are known because the bench seeded the data. Graded
               mechanically against those answers (exact, number, contains, set), never by a
               model, so a judge cannot be the thing that improved. Each question runs --repeats
               times per side.
  tokens       What the output costs the reader, from the reader's own usage report: total input
               tokens of each call (the prompt template is identical on both sides, so the
               difference is the output itself), plus characters and lines of stdout.
  conformance  The AXI rules a script can check: an unknown flag exits 2 and names the valid
               flags on stdout; --help exits 0; an empty store gets an explicit zero instead of
               silence; agent-mode stdout carries no ANSI colour.

THE SANDBOX. Every run gets a fresh AI_SETUP directory and a flushed Redis logical db (15 by
default, the same isolation the test suite uses, tests/isolate_canonical.py), so the bench never
reads or writes the live store. Benches that run at the same time need different dbs: --db
takes 1-12 (13 belongs to the link end-to-end tests, 0 is the live store and is refused). The
spec's SEED commands run with the working tree's CLI, so both sides read identical data.

THE READER. `claude -p` with a small model (default claude-haiku-5-5), run from an empty
directory with AKASHIC_STOP_WAKE=0 so no project instructions or hooks reach it.

SPECS live in scripts/axi_bench/specs/<verb>.py (module name: the verb with '-' as '_'):

    VERB = "locks"
    SEED = [["lock", "alice", "core/a.py"], ...]          # argv lists, run before measuring
    RUNS = {"list": ["locks"]}                            # name -> argv of the verb under test
    EMPTY = ["locks"]                                     # argv run on an empty store, or None
    QUESTIONS = [{"run": "list", "q": "...", "a": "alice", "grade": "exact"}, ...]

Reports go to research/axi-bench/<verb>.json and .md.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
#: The fork's master before any AXI change, so every verb is compared with its original output.
BASELINE = "50c2ee6f"
REPORTS = ROOT / "research" / "axi-bench"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
READER_PROMPT = (
    "Below is the complete stdout of the shell command `{cmd}`, run in a project's CLI.\n"
    "Answer the question using only this output. If the output does not contain the answer, "
    "reply UNKNOWN. Reply with only the answer: no explanation, no quotes, no punctuation "
    "around it.\n\n<output>\n{output}\n</output>\n\nQuestion: {question}"
)
EMPTY_WORDS = re.compile(r"\b(0|no|none|nothing|empty|zero)\b", re.IGNORECASE)


# ------------------------------------------------------------------ trees and sandbox


def export_tree(ref: str, dest: Path) -> Path:
    """Write the files of git `ref` to dest (no .git, no worktree registration)."""
    dest.mkdir(parents=True, exist_ok=True)
    tar = dest.parent / f"{dest.name}.tar"
    with tar.open("wb") as fh:
        subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", ref], stdout=fh, check=True)
    with tarfile.open(tar) as tf:
        tf.extractall(dest, filter="data")
    tar.unlink()
    # The world is named by the checkout folder or a .aurora-world file. An export named "before"
    # matches no world and prints a warning into stdout, which would count against the old code.
    try:
        sys.path.insert(0, str(ROOT))
        from core.world import current

        (dest / ".aurora-world").write_text(current().name + "\n", encoding="utf-8")
    except Exception:
        pass
    return dest


def flush_db(db: int) -> None:
    import redis

    if db == 0:
        raise SystemExit("refusing to flush Redis db 0: it holds the live store")
    port = int(os.getenv("REDIS_PORT") or 16379)
    redis.Redis(port=port, db=db).flushdb()


class Sandbox:
    def __init__(self, base: Path, db: int = 15):
        self.base = base
        self.data = base / "data"
        self.db = db

    def reset(self) -> None:
        shutil.rmtree(self.data, ignore_errors=True)
        self.data.mkdir(parents=True)
        flush_db(self.db)

    def env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "CODEX_", "CURSOR_"))}
        env.update(
            AI_SETUP=str(self.data),
            REDIS_DB=str(self.db),
            AKASHIC_AGENT_ID="bench",
            AURORA_OUTPUT="agent",
            AKASHIC_STOP_WAKE="0",
            NO_COLOR="1",
            PYTHONIOENCODING="utf-8",
        )
        env.pop("AI_AGENT", None)
        env.pop("AURORA_LAUNCHER", None)
        return env


def run_cli(tree: Path, argv: list[str], sandbox: Sandbox, timeout: int = 120) -> dict:
    t0 = time.monotonic()
    p = subprocess.run(
        [sys.executable, str(tree / "agent_cli.py"), *argv],
        cwd=tree,
        env=sandbox.env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "argv": argv,
        "exit": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
        "seconds": round(time.monotonic() - t0, 2),
    }


# ------------------------------------------------------------------ reader and grading


def ask_reader(cmd: str, output: str, question: str, model: str, workdir: Path) -> dict:
    prompt = READER_PROMPT.format(cmd=cmd, output=output.rstrip() or "(no output)", question=question)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AKASHIC_", "AI_SETUP", "REDIS_DB"))}
    env["AKASHIC_STOP_WAKE"] = "0"
    for attempt in range(3):
        p = subprocess.run(
            [
                "claude", "-p", "--model", model, "--max-turns", "1", "--output-format", "json",
                "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Task",
            ],
            input=prompt,
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )  # fmt: skip
        try:
            d = json.loads(p.stdout)
            u = d.get("usage") or {}
            return {
                "answer": str(d.get("result") or "").strip(),
                "input_tokens": int(u.get("input_tokens", 0))
                + int(u.get("cache_creation_input_tokens", 0))
                + int(u.get("cache_read_input_tokens", 0)),
                "cost_usd": float(d.get("total_cost_usd") or 0),
            }
        except (ValueError, TypeError):
            time.sleep(2 * (attempt + 1))
    return {"answer": "", "input_tokens": 0, "cost_usd": 0.0, "error": (p.stderr or p.stdout)[-300:]}


def _norm(s: str) -> str:
    s = ANSI.sub("", str(s)).strip().strip("`'\".").strip()
    return re.sub(r"\s+", " ", s).lower()


def grade(kind: str, answer: str, expected) -> bool:
    a = _norm(answer)
    if kind == "exact":
        return a == _norm(expected)
    if kind == "number":
        nums = re.findall(r"-?\d+(?:\.\d+)?", a.replace(",", ""))
        return bool(nums) and float(nums[0]) == float(expected)
    if kind == "contains":
        items = expected if isinstance(expected, (list, tuple)) else [expected]
        return all(_norm(x) in a for x in items)
    if kind == "set":
        got = {_norm(x) for x in re.split(r"[,;\n]| and ", a) if _norm(x)}
        return got == {_norm(x) for x in expected}
    if kind == "unknown":  # the honest answer is that the output does not say
        return a in ("unknown", "")
    raise ValueError(f"unknown grade kind {kind!r}")


# ------------------------------------------------------------------ conformance


def conformance(tree: Path, spec, sandbox: Sandbox, verb_argv: list[str]) -> dict:
    checks = {}
    r = run_cli(tree, [*verb_argv, "--definitely-not-a-flag"], sandbox)
    checks["unknown_flag_exit_2"] = r["exit"] == 2
    checks["unknown_flag_on_stdout"] = "definitely-not-a-flag" in r["stdout"]
    checks["unknown_flag_lists_valid_flags"] = "--help" in r["stdout"]
    r = run_cli(tree, [*verb_argv, "--help"], sandbox)
    checks["help_exit_0"] = r["exit"] == 0
    if getattr(spec, "EMPTY", None):
        sandbox.reset()
        r = run_cli(tree, spec.EMPTY, sandbox)
        checks["empty_state_explicit"] = r["exit"] == 0 and bool(EMPTY_WORDS.search(r["stdout"]))
    checks["no_ansi_in_agent_stdout"] = True
    return checks


# ------------------------------------------------------------------ the run


def load_spec(verb: str):
    return importlib.import_module(f"scripts.axi_bench.specs.{verb.replace('-', '_')}")


def calibrate(spec, model: str, workdir: Path, workers: int) -> list[int]:
    """Per question, the reader's input tokens with the output left empty: the fixed cost of the
    call (system prompt, template, command, question). Subtracting it leaves exactly what the
    command's output costs. The same baseline serves both sides."""

    def one(q):
        cmd = "aurora " + " ".join(spec.RUNS[q["run"]])
        return ask_reader(cmd, "", q["q"], model, workdir)["input_tokens"]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, spec.QUESTIONS))


def measure(
    tree: Path, spec, sandbox: Sandbox, model: str, repeats: int, workdir: Path, workers: int, base: list[int]
) -> dict:
    sandbox.reset()
    for argv in getattr(spec, "SEED", []):
        r = run_cli(ROOT, argv, sandbox)  # seed with the working tree's CLI: same data both sides
        if r["exit"] != 0:
            raise SystemExit(f"seed command failed: {argv}\n{r['stdout']}\n{r['stderr']}")
    runs = {name: run_cli(tree, argv, sandbox) for name, argv in spec.RUNS.items()}
    jobs = []
    for qi, q in enumerate(spec.QUESTIONS):
        stdout = runs[q["run"]]["stdout"]
        cmd = "aurora " + " ".join(spec.RUNS[q["run"]])
        jobs.extend((qi, rep, cmd, stdout, q) for rep in range(repeats))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        answers = list(pool.map(lambda j: (j, ask_reader(j[2], j[3], j[4]["q"], model, workdir)), jobs))
    per_q: list[dict] = []
    for qi, q in enumerate(spec.QUESTIONS):
        got = [a for (j, a) in answers if j[0] == qi]
        ok = [grade(q.get("grade", "exact"), a["answer"], q["a"]) for a in got]
        per_q.append({"q": q["q"], "expected": q["a"], "answers": [a["answer"] for a in got], "correct": sum(ok)})
    tokens = [a["input_tokens"] - base[j[0]] for (j, a) in answers if a["input_tokens"] and base[j[0]]]
    verb_argv = next(iter(spec.RUNS.values()))
    verb_argv = verb_argv[: len(spec.VERB.split())]
    conf = conformance(tree, spec, sandbox, verb_argv)
    conf["no_ansi_in_agent_stdout"] = not any(ANSI.search(r["stdout"]) for r in runs.values())
    total = sum(int(x["correct"]) for x in per_q)
    return {
        "accuracy": round(total / max(1, len(per_q) * repeats), 3),
        "correct": total,
        "asked": len(per_q) * repeats,
        "output_tokens": int(statistics.median(tokens)) if tokens else None,
        "stdout_chars": sum(len(r["stdout"]) for r in runs.values()),
        "stdout_lines": sum(r["stdout"].count("\n") for r in runs.values()),
        "cost_usd": round(sum(a.get("cost_usd", 0) for (_, a) in answers), 4),
        "conformance": conf,
        "conformance_passed": f"{sum(conf.values())}/{len(conf)}",
        "questions": per_q,
        "runs": {k: {"argv": v["argv"], "exit": v["exit"], "stdout": v["stdout"]} for k, v in runs.items()},
    }


def report_md(verb: str, before_ref: str, before: dict, after: dict, model: str, repeats: int) -> str:
    def delta(b, a, pct=True):
        if b in (None, 0) or a is None:
            return "n/a"
        d = a - b
        return f"{d:+,}" + (f" ({d / b:+.0%})" if pct else "")

    def num(n):
        return "n/a" if n is None else f"{n:,}"

    rows = [
        ("Reader accuracy", f"{before['correct']}/{before['asked']} ({before['accuracy']:.0%})",
         f"{after['correct']}/{after['asked']} ({after['accuracy']:.0%})",
         f"{(after['accuracy'] - before['accuracy']) * 100:+.0f} pp"),
        ("Output tokens, as the reader counts them (median)", num(before["output_tokens"]),
         num(after["output_tokens"]), delta(before["output_tokens"], after["output_tokens"])),
        ("Stdout characters (all runs)", num(before["stdout_chars"]), num(after["stdout_chars"]),
         delta(before["stdout_chars"], after["stdout_chars"])),
        ("AXI checks passed", before["conformance_passed"], after["conformance_passed"], ""),
    ]  # fmt: skip
    lines = [
        f"# AXI bench: `{verb}`",
        "",
        (
            f"Before: `{before_ref}`. After: this change. Reader: `{model}`, {repeats} runs per question, "
            "graded mechanically against seeded answers."
        ),
        "",
        "| Measure | Before | After | Change |",
        "|---|---|---|---|",
        *[f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows],
        "",
        "## Questions",
        "",
        "| Question | Expected | Before | After |",
        "|---|---|---|---|",
    ]
    for qb, qa in zip(before["questions"], after["questions"], strict=True):
        lines.append(f"| {qb['q']} | `{qb['expected']}` | {qb['correct']}/{repeats} | {qa['correct']}/{repeats} |")
    lines += ["", "## AXI checks", "", "| Check | Before | After |", "|---|---|---|"]
    for k in after["conformance"]:
        b, a = before["conformance"].get(k), after["conformance"][k]
        lines.append(f"| {k.replace('_', ' ')} | {'pass' if b else 'fail'} | {'pass' if a else 'fail'} |")
    for side, res in (("Before", before), ("After", after)):
        lines += ["", f"## {side}: output", ""]
        for run in res["runs"].values():
            lines += [
                f"`aurora {' '.join(run['argv'])}` (exit {run['exit']})",
                "",
                "```",
                run["stdout"].rstrip(),
                "```",
                "",
            ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AXI before/after bench for one CLI verb")
    ap.add_argument("verb")
    ap.add_argument("--before", default=BASELINE, help="git ref of the code before the change")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument(
        "--db",
        type=int,
        default=15,
        choices=[*range(1, 13), 15],
        help="Redis logical db for the sandbox (flushed); give parallel benches different ones",
    )
    ap.add_argument("--no-write", action="store_true", help="print the report, write nothing")
    a = ap.parse_args(argv)
    spec = load_spec(a.verb)
    with tempfile.TemporaryDirectory(prefix="axi-bench-") as tmp:
        base = Path(tmp)
        before_tree = export_tree(a.before, base / "before")
        sandbox = Sandbox(base, a.db)
        reader_dir = base / "reader"
        reader_dir.mkdir()
        base = calibrate(spec, a.model, reader_dir, a.workers)
        before = measure(before_tree, spec, sandbox, a.model, a.repeats, reader_dir, a.workers, base)
        after = measure(ROOT, spec, sandbox, a.model, a.repeats, reader_dir, a.workers, base)
        sandbox.reset()
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", a.before], capture_output=True, text=True)
    ref = f"{a.before} ({sha.stdout.strip()})" if sha.returncode == 0 else a.before
    md = report_md(a.verb, ref, before, after, a.model, a.repeats)
    if a.no_write:
        print(md)
        return 0
    REPORTS.mkdir(parents=True, exist_ok=True)
    stem = a.verb.replace(" ", "-")
    (REPORTS / f"{stem}.md").write_text(md, encoding="utf-8")
    (REPORTS / f"{stem}.json").write_text(
        json.dumps({"verb": a.verb, "before_ref": ref, "model": a.model, "repeats": a.repeats,
                    "before": before, "after": after}, indent=2) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
