"""The shared recall-block orchestration — the rule-of-three extraction (t383).

Three harnesses each needed the same sequence and two carried deliberate copies
(claude_pretooluse._recall_context, cursor_posttooluse._recall_block + outcome flow,
claude_userpromptsubmit.build_plan_recall). The DeepSeek Harness arriving as the third
triggered this module, exactly as the tiers doc pre-declared. Adapters translate their
runtime's JSON and call these; the SHARED policy lives here (the architecture rule:
nothing in this file knows a harness name). One deliberate exclusion, per the t383
adversarial review (F2): claude_posttooluse's outcome flow stays in that hook — it is
not the same shape (it BACKFILLS transcript-synthesized FAIL halves before the success,
and its flip event carries an enriched detail with alt/query reconstruction). That
enrichment policy lives there until a second harness needs transcript synthesis.

The three doors (sealed signatures, fences/t383-dsh-adapter/reconciliation.md):

  recall_block(session_key, seen_key, path, command, agent_id=None) -> str
      Surface recall for the action just taken (or about to be): unseen lessons +
      lock warnings; marks seen (anti-repeat, keyed on seen_key), opens the
      FAIL->SUCCESS impression join (keyed on session_key), ledgers the push.

  outcome_block(session_key, seen_key, target, success, agent_id=None) -> str
      Direct outcome credit: resolves the join; on a FAIL->SUCCESS flip credits the
      surfaced lessons, captures the flip event, and returns the JIT learn-nudge
      under the per-seen-key rate limit. "" when there is nothing to say.

  plan_block(prompt, session_key, seen_key, agent_id=None) -> str
      Plan-altitude recall for a fresh user prompt (limit 2, plan header), ledgered.

TWO KEYS, ON PURPOSE: session_key is the JOIN/attribution key (impressions, outcome,
injection ledger — a DSH seat passes its stable agent id; the in-tree hooks pass their
session uuid, byte-for-byte their old behavior). seen_key is the ANTI-REPEAT key (the
per-session "already shown" set and the nudge rate limit). The in-tree hooks pass the
same value for both; DSH splits them (constant identity, per-session repeats).

IDENTITY THREAD (the t383 leak fix): agent_id explicit beats env at every exit —
recall ranking, the flip event, the nudge, and the engine's outcome-stage record
(resolve_action_outcome forwards it). Default None falls back to AKASHIC_AGENT_ID,
which is exactly what the hooks did, so claude/cursor behavior is unchanged. Deriving
agent_id FROM session_key was rejected because the in-tree hooks pass their session
UUID as session_key — deriving would have fed a UUID into recall's self-echo author
match and silently broken self-echo suppression for claude/cursor (review F3).

Fail-open by contract: any exception returns "" — recall must never brick an action.
Kill switches: AKASHIC_RECALL_AT_ACTION=0 (action altitude), AKASHIC_PLAN_RECALL=0
(plan altitude) — "off" is a chosen normal state, silence not error.
"""
import os
import tempfile
from typing import Optional


def _nudge_dir() -> str:
    """Same path as the incumbent hooks (state survives the extraction), read at call
    time so AKASHIC_RECALL_STATE_DIR redirection (tests, relocated state) is honored."""
    root = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
    return os.path.join(root, "nudge")


def _agent(agent_id: Optional[str]) -> Optional[str]:
    return agent_id or os.getenv("AKASHIC_AGENT_ID")


def recall_block(session_key: str, seen_key: str, path: Optional[str],
                 command: Optional[str], agent_id: Optional[str] = None) -> str:
    """Unseen lessons + lock warnings for this target; marks seen/impressions and
    ledgers the push. Lifted in behavior from the two in-hook copies."""
    if os.getenv("AKASHIC_RECALL_AT_ACTION", "1") == "0":
        return ""
    if not path and not command:
        return ""
    try:
        from core.recall.at_action import (recall_at, render, mark_impression,
                                           normalize_target, log_injection)
        from agent.harness.seen import load_seen, mark_seen
        res = recall_at(path=path or None, command=command or None,
                        agent_id=_agent(agent_id),
                        exclude_sources=load_seen(seen_key), count_surface=True)
        out = render(res)
        if out:
            srcs = [l.get("source") for l in res.get("lessons", [])]
            mark_seen(seen_key, srcs)
            target = normalize_target(path or None, command or None)
            mark_impression(session_key, target, srcs)
            log_injection(session_key, "action", target, srcs, len(out))
        return out
    except Exception:
        return ""   # recall must never brick the action


def outcome_block(session_key: str, seen_key: str, target: str, success: bool,
                  agent_id: Optional[str] = None) -> str:
    """Resolve the outcome; on a flip, credit + capture + return the JIT nudge under
    the rate limit. Lifted in behavior from cursor_posttooluse's outcome flow."""
    if not target:
        return ""
    try:
        from core.recall.at_action import resolve_action_outcome, build_learn_nudge
        rep = resolve_action_outcome(session_key, target, bool(success),
                                     agent_id=_agent(agent_id))
        if not success or not rep.get("flipped"):
            return ""
        try:   # durable funnel signal (flips observed vs lessons recorded) -- best-effort
            from core.events.event_log import capture_event
            capture_event("flip", f"FAIL->SUCCESS: {target}",
                          agent_id=_agent(agent_id) or "unknown",
                          detail={"target": target, "credited": rep.get("credited", 0),
                                  "sources": rep.get("sources", [])})
        except Exception:
            pass
        from agent.harness.nudge import nudge_allowed, mark_nudged
        if nudge_allowed(_nudge_dir(), seen_key, target):
            text = build_learn_nudge(target, rep.get("credited", 0), rep.get("sources"),
                                     _agent(agent_id))
            mark_nudged(_nudge_dir(), seen_key, target)
            return text or ""
        return ""
    except Exception:
        return ""   # outcome credit must never brick the action


def plan_block(prompt: str, session_key: str, seen_key: str,
               agent_id: Optional[str] = None) -> str:
    """Plan-altitude context for a fresh prompt, or "" for silence. Lifted in behavior
    from claude_userpromptsubmit.build_plan_recall."""
    if os.getenv("AKASHIC_PLAN_RECALL", "1") == "0":
        return ""
    if not (prompt or "").strip():
        return ""
    try:
        from core.recall.at_action import recall_at, render, log_injection
        from agent.harness.seen import load_seen, mark_seen
        res = recall_at(command=prompt, agent_id=_agent(agent_id), limit=2,
                        exclude_sources=load_seen(seen_key), count_surface=True)
        out = render(res, header="Plan-time recall (Akashic) - corpus knowledge relevant to this request:")
        if not out:
            return ""
        srcs = [l.get("source") for l in res.get("lessons", [])]
        mark_seen(seen_key, srcs)
        log_injection(session_key, "plan", "", srcs, len(out))
        return out
    except Exception:
        return ""   # plan recall must never brick the prompt
