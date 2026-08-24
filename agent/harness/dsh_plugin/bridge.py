"""Bridge: DSH plugin <-> Akashic repo, one subprocess per event, JSON in/out.

REFERENCE COPY — synced via git; deploy to $DSH_HOME with scripts/install_dsh_plugin.py.
The sealed design (fence t383-dsh-adapter reconciliation, 2026-08-24) assigns the
DSH side five listeners and this bridge. Every subcommand calls a shared repo
function and prints exactly one JSON line. Fail-open by construction: never
raises, and a missing repo module prints an error shape instead of a traceback —
the plugin treats any error shape as silence.

PORTABILITY (the one per-instance seam): the repo path is NEVER hardcoded here.
Resolution order: env AKASHIC_REPO (stamped into $DSH_HOME/.env by the installer)
-> marker-walk upward from cwd looking for agent_cli.py. A miss emits the
fail-open error shape {"error": "AkashicRepoNotFound"} — it never tracebacks.

Subcommands:
  presence       --phase idle|thinking|tool-running|offline --session-id SID
                 roster.heartbeat(BIFROST_NAMESPACE, "dsh_agent", SID, phase=...).
                 OFFLINE NOTE: roster has no clear API (TTL owns liveness); the
                 reconciliation assigns the presence-writer snippet to claude —
                 this --phase offline beat is the placeholder until that snippet
                 supersedes it.
  boot-whisper   --cwd --agent-id --session-id   -> agent.harness.context.build_autoboot_context
  action-recall  --session-key --seen-key [--path P] [--command C]
                 -> agent.harness.actions.recall_block (T3, one beat late)
  outcome-credit --session-key --seen-key --target T --success 0|1
                 -> agent.harness.actions.outcome_block (T4, direct)
  plan-recall    --session-key --seen-key --prompt P
                 -> agent.harness.actions.plan_block (T5, derived)
  session-end    --session-id SID
                 -> best-effort where-we-are distiller (T6, capture-only).
                 KNOWN GAP: claude_sessionend.py consumes Claude-shaped
                 transcripts; DSH transcripts need a shim before the distiller
                 can see them. Flags silently (fail-open) until then.
"""
import argparse
import json
import os
import subprocess
import sys


def _repo() -> str:
    """The one per-instance seam. Env first (installer-stamped), marker-walk second."""
    env = os.environ.get("AKASHIC_REPO")
    if env and os.path.isfile(os.path.join(env, "agent_cli.py")):
        return env
    d = os.getcwd()
    for _ in range(12):
        if os.path.isfile(os.path.join(d, "agent_cli.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise RuntimeError("AkashicRepoNotFound: set AKASHIC_REPO in $DSH_HOME/.env "
                       "(scripts/install_dsh_plugin.py stamps it)")


def _emit(obj) -> int:
    print(json.dumps(obj))
    return 0


def _import_actions():
    """The shared orchestration module. Raises until claude lands it."""
    sys.path.insert(0, _repo())
    from agent.harness.actions import recall_block, outcome_block, plan_block  # noqa: F401
    return recall_block, outcome_block, plan_block


def cmd_presence(a) -> int:
    try:
        sys.path.insert(0, _repo())
        from core.comm.roster import heartbeat
        ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
        agent = os.environ.get("AKASHIC_AGENT_ID", "dsh_agent")
        rep = heartbeat(ns, agent, a.session_id or "", phase=a.phase)
        return _emit({"ok": bool(rep and rep.get("ok")), "phase": a.phase,
                      "resumed_after_s": (rep or {}).get("resumed_after_s")})
    except Exception as e:
        return _emit({"ok": False, "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_boot_whisper(a) -> int:
    try:
        sys.path.insert(0, _repo())
        from agent.harness.context import build_autoboot_context
        text = build_autoboot_context(a.cwd, a.agent_id, a.session_id)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_action_recall(a) -> int:
    try:
        recall_block, _, _ = _import_actions()
        text = recall_block(a.session_key, a.seen_key, a.path, a.command)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_outcome_credit(a) -> int:
    try:
        _, outcome_block, _ = _import_actions()
        text = outcome_block(a.session_key, a.seen_key, a.target, bool(a.success),
                             agent_id=a.session_key)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_plan_recall(a) -> int:
    try:
        _, _, plan_block = _import_actions()
        text = plan_block(a.prompt, a.session_key, a.seen_key)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_session_end(a) -> int:
    # T6 capture, best-effort. The distiller reads Claude-shaped transcripts;
    # DSH transcripts need a shim (flagged to claude in the build report).
    try:
        repo = _repo()
        hook = os.path.join(repo, "agent", "harness", "hooks", "claude_sessionend.py")
        if not os.path.exists(hook):
            return _emit({"ran": False, "error": "NoDistiller"})
        proc = subprocess.run([sys.executable, hook], input=json.dumps({
            "session_id": a.session_id, "transcript_path": "", "cwd": repo}),
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        return _emit({"ran": proc.returncode == 0, "rc": proc.returncode,
                      "stderr_tail": (proc.stderr or "")[-200:]})
    except Exception as e:
        return _emit({"ran": False, "error": type(e).__name__, "error_detail": str(e)[:200]})


def main() -> int:
    ap = argparse.ArgumentParser(prog="bridge.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("presence")
    p.add_argument("--phase", default="idle")
    p.add_argument("--session-id", default="")
    p.set_defaults(fn=cmd_presence)

    w = sub.add_parser("boot-whisper")
    w.add_argument("--cwd", default="")
    w.add_argument("--agent-id", default="dsh_agent")
    w.add_argument("--session-id", default="")
    w.set_defaults(fn=cmd_boot_whisper)

    r = sub.add_parser("action-recall")
    r.add_argument("--session-key", required=True)
    r.add_argument("--seen-key", default="")
    r.add_argument("--path", default=None)
    r.add_argument("--command", default=None)
    r.set_defaults(fn=cmd_action_recall)

    o = sub.add_parser("outcome-credit")
    o.add_argument("--session-key", required=True)
    o.add_argument("--seen-key", default="")
    o.add_argument("--target", required=True)
    o.add_argument("--success", type=int, choices=(0, 1), default=1)
    o.set_defaults(fn=cmd_outcome_credit)

    pl = sub.add_parser("plan-recall")
    pl.add_argument("--session-key", required=True)
    pl.add_argument("--seen-key", default="")
    pl.add_argument("--prompt", default="")
    pl.set_defaults(fn=cmd_plan_recall)

    se = sub.add_parser("session-end")
    se.add_argument("--session-id", default="")
    se.set_defaults(fn=cmd_session_end)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
