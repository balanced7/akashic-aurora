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
                 roster.heartbeat(...) for live phases; phase=offline calls
                 roster.go_offline (presence-offline API, 2026-08-24) -- a declared
                 departure removes the worklive key NOW and renders OFFLINE in the
                 roster instead of beating the key alive (the old placeholder defect).
  boot-whisper   --cwd --agent-id --session-id   -> agent.harness.context.build_autoboot_context
  action-recall  --session-key --seen-key [--path P] [--command C]
                 -> agent.harness.actions.recall_block (T3, one beat late)
  outcome-credit --session-key --seen-key [--path P] [--command C] [--target T] --success 0|1
                 -> agent.harness.actions.outcome_block (T4, direct). The target
                 derives via normalize_target(path, command) -- --target is only an
                 already-normalized override (V27).
  plan-recall    --session-key --seen-key --prompt P
                 -> agent.harness.actions.plan_block (T5, derived)
  session-end    --session-id SID [--transcript-path P]
                 -> T6 auto-handoff (DSH shim, 2026-08-24): auto-drafts
                 chronicles/last-session-draft.md (commits+lessons+notes, harness-
                 agnostic), folds session_signals from the DSH log (zstd JSONL,
                 parse_dsh_calls), closes the open episode, runs the clean-death
                 trio. The transcript path is located under
                 $DSH_HOME/sessions/<slug>/session-<sid>/ when not passed.
                 NOT the claude hook: the claude distiller reads Claude-shaped
                 transcripts; this path is DSH-native (callId pairing via
                 message.source.callId, failure via data.error).
"""
import argparse
import json
import os
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
        from core.comm.roster import go_offline, heartbeat
        ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
        agent = os.environ.get("AKASHIC_AGENT_ID", "dsh_agent")
        if str(a.phase).lower() == "offline":
            rep = go_offline(ns, agent, a.session_id or "")
            return _emit({"ok": bool(rep and rep.get("ok")), "phase": a.phase,
                          "offline_ts": (rep or {}).get("offline_ts")})
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
        # identity thread on ALL doors (t383 review F1): explicit beats inherited env
        text = recall_block(a.session_key, a.seen_key, a.path, a.command,
                            agent_id=a.session_key)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def derive_target(path=None, command=None, target=None) -> str:
    """V27 target-join law: the resolve target MUST be the same derivation as the
    surface target. recall_block normalizes internally (normalize_target), so the
    resolve door derives from the SAME path/command inputs here. --target is only an
    already-normalized override. Pinned by tests/test_dsh_contract.py."""
    if path or command:
        from core.recall.at_action import normalize_target
        return normalize_target(path or None, command or None)
    return target or ""


def cmd_outcome_credit(a) -> int:
    try:
        _, outcome_block, _ = _import_actions()
        # V27 target-join law (broken LIVE, fixed 2026-08-24): the plugin once pre-joined
        # 'path | command' in JS and passed it as --target, while normalize_target emits
        # p:<abspath>/c:<lowercased command> -- the join evaporated and flips could never
        # credit. The JS now sends --path/--command; the bridge does the single derivation.
        target = derive_target(a.path, a.command, a.target)
        text = outcome_block(a.session_key, a.seen_key, target, bool(a.success),
                             agent_id=a.session_key)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def cmd_plan_recall(a) -> int:
    try:
        _, _, plan_block = _import_actions()
        text = plan_block(a.prompt, a.session_key, a.seen_key, agent_id=a.session_key)
        return _emit({"text": text or ""})
    except Exception as e:
        return _emit({"text": "", "error": type(e).__name__, "error_detail": str(e)[:200]})


def _read_dsh_lines(transcript_path: str, max_bytes: int = 16 * 1024 * 1024):
    """DSH session log -> (text lines, truncated). The log is zstd-FRAME-per-line
    JSONL (session.jsonl.zstd); plain .jsonl is also accepted (tests/fixtures)."""
    try:
        if str(transcript_path).endswith(".zstd"):
            import zstandard
            dctx = zstandard.ZstdDecompressor()
            with open(transcript_path, "rb") as f:
                reader = dctx.stream_reader(f)
                chunks = []
                while True:
                    chunk = reader.read(1 << 20)
                    if not chunk:
                        break
                    chunks.append(chunk)
            text = b"".join(chunks).decode("utf-8", errors="ignore")
        else:
            with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception:
        return [], False
    truncated = len(text) > max_bytes
    if truncated:
        text = text[-max_bytes:]
        nl = text.find("\n")
        text = text[nl + 1:] if nl >= 0 else ""
    return text.splitlines(), truncated


_FILE_TOOLS = ("read", "edit", "write", "notebookedit")
_SHELL_TOOLS = ("pwsh", "bash", "powershell")


def parse_dsh_calls(transcript_path: str, max_bytes: int = 16 * 1024 * 1024):
    """DSH session log -> the SAME calls shape core.renew.session_signals.fold_signals
    consumes ([{tool, target, at, ok}]). The DSH adapter's translation of
    claude_sessionend.parse_transcript_calls: tool/call records carry {callId, name,
    arguments (JSON string)}; tool/result pairs via message.source.callId; failure is
    data.error. Targets normalize like the surface (p: files / c: commands) so the
    correlation join stays exact. Pinned by tests/test_dsh_contract.py."""
    from core.recall.at_action import normalize_target
    lines, truncated = _read_dsh_lines(transcript_path, max_bytes)
    order, uses, results = [], {}, {}
    for line in lines:
        line = line.lstrip("\ufeff")   # tolerate a BOM on the first record
        try:
            rec = json.loads(line)
        except Exception:
            continue
        data = rec.get("data") or {}
        if rec.get("type") == "tool/call" and data.get("callId"):
            name = str(data.get("name") or "")
            args = data.get("arguments") or "{}"
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            if name in _FILE_TOOLS:
                target = normalize_target(args.get("file_path") or args.get("path") or None, None)
            elif name in _SHELL_TOOLS:
                target = normalize_target(None, args.get("command") or None)
            else:
                target = ""
            order.append(data["callId"])
            uses[data["callId"]] = {"tool": name, "target": target, "at": rec.get("time", 0)}
        elif rec.get("type") == "tool/result":
            src = (data.get("message") or {}).get("source") or {}
            cid = src.get("callId")
            if cid in uses:
                results[cid] = not bool(data.get("error"))
    return [{**uses[cid], "ok": results[cid]} for cid in order if cid in results], truncated


def locate_dsh_session_log(dsh_home: str, session_id: str) -> str:
    """The DSH session log under the real layout
    $DSH_HOME/sessions/<workspace-slug>/session-<id>/session.jsonl[.zstd]."""
    sid = session_id if str(session_id).startswith("session-") else "session-" + str(session_id)
    base = os.path.join(dsh_home, "sessions")
    if not os.path.isdir(base):
        return ""
    try:
        for slug in os.listdir(base):
            for name in ("session.jsonl.zstd", "session.jsonl"):
                p = os.path.join(base, slug, sid, name)
                if os.path.isfile(p):
                    return p
    except Exception:
        return ""
    return ""


def _gather_draft(trigger: str) -> None:
    """The ONE draft builder, delegated (this module owns no second way to build a
    draft -- pinned by tests/test_draft_keepalive.py): commits + lessons + notes +
    flips -> chronicles/last-session-draft.md. Raises on failure; callers wrap it."""
    import agent_cli
    from core.learning.agent_memory import get_agent_memory
    commits = agent_cli._recent_commits(24)
    lessons = agent_cli._recent_lessons(8)
    notes = get_agent_memory().get_decisions(days=1)
    try:
        from core.recall.at_action import recent_flips, recent_injections
        flips, injections = recent_flips(24), recent_injections(24)
    except Exception:
        flips, injections = [], []
    agent_cli.write_last_session_draft(
        agent_cli.last_session_draft_path(), commits, lessons, notes,
        trigger=trigger, flips=flips, injections=injections)


def _keepalive_run() -> dict:
    """The throttled turn-boundary draft refresh (Vandor's organ, wired 2026-08-26).
    Never raises; returns {"wrote": bool, "reason": str} -- a skip is a stated
    decision, and the 600s throttle keeps the common case one getmtime."""
    try:
        repo = _repo()
        sys.path.insert(0, repo)
        from agent.harness import draft_keepalive
        import agent_cli

        def _write():
            old = os.getcwd()
            os.chdir(repo)
            try:
                _gather_draft("DSH draft keepalive")
            finally:
                os.chdir(old)

        return draft_keepalive.refresh(agent_cli.last_session_draft_path(), write=_write)
    except Exception as e:                                              # noqa: BLE001
        return {"wrote": False,
                "reason": f"keepalive failed ({type(e).__name__}: {str(e)[:80]})"}


def cmd_draft_keepalive(a) -> int:
    """draft-keepalive -- the DSH analog of the Stop-hook keepalive: fired
    fire-and-forget at every turn boundary (tools/post-execute), it refreshes
    chronicles/last-session-draft.md when stale so a taskkill /F on the host still
    leaves a draft NEWER than the kill. Kill switch: AKASHIC_DRAFT_KEEPALIVE=0."""
    return _emit(_keepalive_run())


def _build_draft_keepalive_parser(sub=None):
    """Standalone builder so pins can parse the subcommand without main().
    With sub=None it builds a top-level parser and returns it; with a subparsers
    action it registers the subcommand there and returns the sub-parser."""
    if sub is None:
        ap = argparse.ArgumentParser(prog="bridge.py")
        _build_draft_keepalive_parser(ap.add_subparsers(dest="cmd", required=True))
        return ap
    k = sub.add_parser("draft-keepalive")
    k.set_defaults(fn=cmd_draft_keepalive)
    return k


def cmd_session_end(a) -> int:
    # T6 auto-handoff, DSH-native. Same shared organs the claude hook drives, but the
    # transcript side is the DSH log (zstd JSONL) instead of Claude JSONL. Best-effort
    # throughout: an auto-handoff must never block a session from ending.
    try:
        repo = _repo()
        sys.path.insert(0, repo)   # imports (agent_cli, core.*) resolve against the repo
        os.chdir(repo)   # git-based calls resolve against the repo, not the server cwd
        sid = a.session_id or ""
        home = os.environ.get("DSH_HOME") or os.path.join(os.path.expanduser("~"), ".dsh")
        transcript = a.transcript_path or locate_dsh_session_log(home, sid)

        # DRAFT (harness-agnostic): commits + lessons + notes -> last-session-draft.md
        _gather_draft("DSH session end")

        # SIGNALS: DSH calls -> the same fold the claude hook uses (watermark shared).
        # Same kill switch as claude_sessionend: AKASHIC_SESSION_SIGNALS=0.
        signals_done = False
        if os.getenv("AKASHIC_SESSION_SIGNALS", "1") != "0" and transcript and os.path.exists(transcript):
            calls, truncated = parse_dsh_calls(transcript)
            if calls:
                from agent.harness.hooks.claude_sessionend import (
                    _already_emitted_calls, _mark_emitted)
                if len(calls) > _already_emitted_calls(sid):
                    from core.renew.session_signals import fold_signals
                    signals = fold_signals(calls)
                    signals["window_truncated"] = truncated
                    from core.events.event_log import capture_event
                    capture_event(
                        "session_signals",
                        f"SESSION SIGNALS: {signals['total_calls']} calls, "
                        f"{signals['fail_count']} fails, {signals['progress_count']} progress",
                        agent_id=os.environ.get("AKASHIC_AGENT_ID") or "dsh_agent",
                        session_id=sid, detail=signals)
                    _mark_emitted(sid, len(calls))
                    signals_done = True

        # episode close + clean-death trio (event guard requires the literal SessionEnd)
        try:
            from core.narrative.episode import close_open_episode_for_session_end
            close_open_episode_for_session_end()
        except Exception:
            pass
        try:
            from core.comm.session_exit import clean_death
            clean_death(os.environ.get("AKASHIC_AGENT_ID") or "dsh_agent", sid,
                        event="SessionEnd")
        except Exception:
            pass
        return _emit({"ran": True, "draft": "chronicles/last-session-draft.md",
                      "signals": signals_done,
                      "transcript": bool(transcript and os.path.exists(transcript))})
    except Exception as e:
        return _emit({"ran": False, "error": type(e).__name__, "error_detail": str(e)[:200]})


def _build_outcome_parser(sub=None):
    """The outcome-credit door accepts --path/--command so the resolve target is
    derived from the same inputs as the surface target (V27). --target stays as an
    already-normalized override. Built as a named helper so tests can pin the shape;
    with sub=None it builds a standalone parser for tests."""
    if sub is None:
        sub = argparse.ArgumentParser(prog="bridge.py").add_subparsers(dest="cmd")
    o = sub.add_parser("outcome-credit")
    o.add_argument("--session-key", required=True)
    o.add_argument("--seen-key", default="")
    o.add_argument("--path", default=None)
    o.add_argument("--command", default=None)
    o.add_argument("--target", default=None)
    o.add_argument("--success", type=int, choices=(0, 1), default=1)
    o.set_defaults(fn=cmd_outcome_credit)
    return o


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

    o = _build_outcome_parser(sub)

    pl = sub.add_parser("plan-recall")
    pl.add_argument("--session-key", required=True)
    pl.add_argument("--seen-key", default="")
    pl.add_argument("--prompt", default="")
    pl.set_defaults(fn=cmd_plan_recall)

    se = sub.add_parser("session-end")
    se.add_argument("--session-id", default="")
    se.add_argument("--transcript-path", default=None)
    se.set_defaults(fn=cmd_session_end)

    _build_draft_keepalive_parser(sub)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
