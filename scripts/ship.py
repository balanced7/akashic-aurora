#!/usr/bin/env python3
"""ship.py -- one disciplined command to ship a slice: GATE -> commit+push -> (lesson) -> snapshot.

    py scripts/ship.py "commit message" path [path ...]
    py scripts/ship.py "msg" a.py b.py --learn-exp NAME --tried "..." --result "..." --recommend "..."
    py scripts/ship.py "msg" a.py --no-snapshot
    py scripts/ship.py "msg" a.py --dry-run         # print the plan; do nothing

Encodes the whole slice ritual so the conventions can't be forgotten or half-done:
  1. GATE -- check_boundaries + check_doc_freshness + the full pytest suite. ANY failure ABORTS
     before anything is committed, so you never push something CI would reject.
  2. COMMIT + PUSH via mirror.py with EXPLICIT paths (never `git add -A`; the shared-tree rule).
  3. (optional) record a lesson  (--learn-exp ...).
  4. snapshot the knowledge store (knowledge DATA is not in git).
Fail-fast: if a step exits non-zero, ship stops and reports; nothing past it runs.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "py"


def build_plan(args):
    """The ordered [(label, argv)] steps. PURE -- powers --dry-run and the tests (no side effects)."""
    steps = []
    if not args.no_test:
        steps.append(("guard: boundaries", [PY, "scripts/check_boundaries.py"]))
        steps.append(("guard: doc-freshness", [PY, "scripts/check_doc_freshness.py"]))
        steps.append(("guard: doc-currency (no dead law in docs/)",
                      [PY, "scripts/check_doc_currency.py", *args.paths]))
        steps.append(("guard: comprehensibility (map matches code)", [PY, "scripts/check_comprehensibility.py"]))
        steps.append(("guard: door parity (no new verb-surface drift)", [PY, "scripts/check_door_parity.py"]))
        steps.append(("guard: wiring (no new built-but-unwired module)", [PY, "scripts/check_wiring.py"]))
        steps.append(("guard: reconciliation gate (substrate ships cite their spec, M1)",
                      [PY, "scripts/check_reconciliation_gate.py", args.message, *args.paths]))
        steps.append(("guard: pre-registration (pins never born with impl, M3)",
                      [PY, "scripts/check_preregistration.py", args.message, *args.paths]))
        steps.append(("guard: verbatim citation (GATE decisions cite their record, M6)",
                      [PY, "scripts/check_verbatim_citation.py", args.message]))
        steps.append(("tests (full suite)", [PY, "-m", "pytest", "-q"]))
    steps.append(("commit + push", [PY, "scripts/mirror.py", args.message, *args.paths]))
    if args.learn_exp:
        learn = [PY, "agent_cli.py", "learn", args.agent, "--experiment", args.learn_exp]
        if args.tried:
            learn += ["--tried", args.tried]
        if args.result:
            learn += ["--result", args.result]
        if args.recommend:
            learn += ["--recommend", args.recommend]
        if getattr(args, "anti_pattern", ""):
            learn += ["--anti-pattern", args.anti_pattern]
        steps.append(("record lesson", learn))
    if not args.no_snapshot:
        steps.append(("snapshot", [PY, "scripts/snapshot_knowledge.py", "snapshot"]))
    return steps


def _run(label, cmd):
    print(f"\n=== {label} ===")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


def _durable_child_argv(argv):
    """Remove launcher-only flags and add the recursion guard for the supervised child."""
    drop_value = {"--job-id", "--job-state-dir", "--deadline-seconds", "--grace-seconds"}
    out = []
    skip = False
    for item in argv:
        if skip:
            skip = False
            continue
        if item == "--durable" or item == "--_durable-child":
            continue
        if item in drop_value:
            skip = True
            continue
        if any(item.startswith(flag + "=") for flag in drop_value):
            continue
        out.append(item)
    out.append("--_durable-child")
    return out


def _cancel_requested():
    path = os.getenv("AKASHIC_JOB_CANCEL_FILE", "")
    return bool(path and os.path.exists(path))


def _git_value(*args):
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def main(argv=None):
    p = argparse.ArgumentParser(prog="ship.py", description="Gate -> commit+push -> lesson -> snapshot, in one step.")
    p.add_argument("message", help="commit message")
    p.add_argument("paths", nargs="*", help="the EXPLICIT files you're shipping (never git add -A)")
    p.add_argument("--agent", default=os.getenv("AKASHIC_AGENT_ID", "claude"))
    p.add_argument("--learn-exp", dest="learn_exp", default=None, help="record a lesson with this experiment name")
    p.add_argument("--tried", default="")
    p.add_argument("--result", default="")
    p.add_argument("--recommend", default="")
    p.add_argument("--anti-pattern", dest="anti_pattern", default="",
                   help="tag the recorded lesson as a reusable known-bad (recall's dissent-finder warns on it)")
    p.add_argument("--no-test", action="store_true", help="skip the gate (rare; e.g. a docs-only fixup)")
    p.add_argument("--no-snapshot", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    p.add_argument("--durable", action="store_true",
                   help="launch under the T093 out-of-tree supervisor and return a receipt immediately")
    p.add_argument("--job-id", default="", help="deterministic durable job id (recommended)")
    p.add_argument("--job-state-dir", default=os.path.join(ROOT, "state", "jobs"))
    p.add_argument("--deadline-seconds", type=float, default=7200.0,
                   help="hard runtime cap enforced by the independent watchdog")
    p.add_argument("--grace-seconds", type=float, default=5.0,
                   help="cooperative cancel grace before exact child-tree force kill")
    p.add_argument("--_durable-child", action="store_true", help=argparse.SUPPRESS)
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = p.parse_args(raw_argv)

    if not args.paths:
        print("ERROR: name the EXPLICIT paths you're shipping (ship never `git add -A` in a shared tree).")
        print('Example: py scripts/ship.py "fix X" core/foo.py tests/test_foo.py')
        return 2

    if args.durable and not args._durable_child:
        # The job id is discoverable in state/jobs even if this short launch frame is lost.
        job_id = args.job_id or time.strftime("ship-%Y%m%d-%H%M%S") + f"-{os.getpid()}"
        from run_job import launch_job
        command = [PY, os.path.abspath(__file__), *_durable_child_argv(raw_argv)]
        receipt = launch_job(
            command,
            job_id=job_id,
            state_dir=args.job_state_dir,
            cwd=ROOT,
            max_runtime=args.deadline_seconds,
            grace_seconds=args.grace_seconds,
            broker="auto",
        )
        print(json.dumps(receipt, sort_keys=True, ensure_ascii=True), flush=True)
        return 0

    steps = build_plan(args)
    if args.dry_run:
        print("# ship plan (dry-run -- nothing executed):")
        for label, cmd in steps:
            print(f"  - {label}: {' '.join(cmd)}")
        return 0

    published = False
    outcome_path = os.getenv("AKASHIC_JOB_OUTCOME_FILE", "")
    fence_path = os.getenv("AKASHIC_JOB_PUBLISH_FENCE", "")
    write_outcome = None
    protect_publish = None
    if outcome_path and fence_path:
        from run_job import (
            protect_owned_job_during_publish,
            publish_fence,
            write_child_outcome,
        )
        write_outcome = write_child_outcome
        protect_publish = protect_owned_job_during_publish

    for label, cmd in steps:
        if _cancel_requested():
            if published and write_outcome:
                write_outcome(outcome_path, {
                    "state": "succeeded",
                    "primary_effect": "pushed",
                    "commit_sha": _git_value("rev-parse", "HEAD"),
                    "branch": _git_value("rev-parse", "--abbrev-ref", "HEAD"),
                    "cancel_requested": True,
                    "cancel_disposition": "after_publish_commit_point",
                    "post_publish_incomplete": True,
                })
                print(f"\n[ship] CANCEL DEFERRED after publish before: {label}; primary effect is durable.")
                return 0
            print(f"\n[ship] CANCELLED before: {label}. Nothing from this or later steps ran.")
            return 130

        if label == "commit + push" and write_outcome:
            # Open our verified Job Object handle before taking the fence. If
            # both guards die during push, KILL_ON_JOB_CLOSE must not bypass the
            # durable publish commit point. The handle closes immediately after
            # fence release, restoring ordinary fail-close semantics.
            with protect_publish():
                with publish_fence(fence_path, blocking=True) as acquired:
                    if not acquired:
                        print("\n[ship] ABORTED: could not acquire the publish fence.")
                        return 1
                    if _cancel_requested():
                        print("\n[ship] CANCELLED at the publish fence; commit/push never started.")
                        return 130
                    head_before = _git_value("rev-parse", "HEAD")
                    branch = _git_value("rev-parse", "--abbrev-ref", "HEAD")
                    write_outcome(outcome_path, {
                        "state": "publish_active",
                        "primary_effect": "unknown",
                        "publish_may_have_occurred": True,
                        "head_before": head_before,
                        "branch": branch,
                        "message": args.message,
                        "paths": list(args.paths),
                    })
                    if not _run(label, cmd):
                        write_outcome(outcome_path, {
                            "state": "outcome_unknown",
                            "primary_effect": "unknown",
                            "publish_may_have_occurred": True,
                            "head_before": head_before,
                            "head_after": _git_value("rev-parse", "HEAD"),
                            "branch": branch,
                            "failed_step": label,
                        })
                        print(f"\n[ship] ABORTED at: {label} (exit non-zero). Publish outcome needs inspection.")
                        return 1
                    write_outcome(outcome_path, {
                        "state": "published",
                        "primary_effect": "pushed",
                        "commit_sha": _git_value("rev-parse", "HEAD"),
                        "head_before": head_before,
                        "branch": branch,
                        "post_publish_incomplete": True,
                    })
                    published = True
            if _cancel_requested():
                write_outcome(outcome_path, {
                    "state": "succeeded",
                    "primary_effect": "pushed",
                    "commit_sha": _git_value("rev-parse", "HEAD"),
                    "branch": branch,
                    "cancel_requested": True,
                    "cancel_disposition": "after_publish_commit_point",
                    "post_publish_incomplete": True,
                })
                print("\n[ship] CANCEL DEFERRED until publish completed; optional later steps skipped.")
                return 0
            continue

        if not _run(label, cmd):
            if published and write_outcome:
                write_outcome(outcome_path, {
                    "state": "succeeded",
                    "primary_effect": "pushed",
                    "commit_sha": _git_value("rev-parse", "HEAD"),
                    "branch": _git_value("rev-parse", "--abbrev-ref", "HEAD"),
                    "post_publish_incomplete": True,
                    "post_publish_failure": label,
                })
                print(
                    f"\n[ship] WARNING after publish: {label} failed; "
                    "the pushed primary effect remains succeeded."
                )
                return 0
            print(f"\n[ship] ABORTED at: {label} (exit non-zero). Nothing past this step ran.")
            return 1
        if _cancel_requested():
            if published and write_outcome:
                write_outcome(outcome_path, {
                    "state": "succeeded",
                    "primary_effect": "pushed",
                    "commit_sha": _git_value("rev-parse", "HEAD"),
                    "branch": _git_value("rev-parse", "--abbrev-ref", "HEAD"),
                    "cancel_requested": True,
                    "cancel_disposition": "after_publish_commit_point",
                    "post_publish_incomplete": True,
                })
                print(f"\n[ship] CANCEL DEFERRED after publish and {label}; later steps skipped.")
                return 0
            print(f"\n[ship] CANCELLED after: {label}. Nothing past this step ran.")
            return 130
    if published and write_outcome:
        write_outcome(outcome_path, {
            "state": "succeeded",
            "primary_effect": "pushed",
            "commit_sha": _git_value("rev-parse", "HEAD"),
            "branch": _git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "post_publish_incomplete": False,
        })
    print("\n[ship] done -- gated green, committed, pushed" +
          ("" if args.no_snapshot else ", snapshotted") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
