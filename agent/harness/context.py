"""The auto-boot whisper shared by every harness adapter (Integration Tiers H0).

T074 Phase 1: the whisper IS the primer (reconciled build spec
docs/library/report/20260715_t074-seamless-continuity-reconciliation_89103c.md; deepseek's contract
governs). A fresh seat must orient from the whisper alone -- no manual pasting.

Sections, in priority order (each independently fail-soft; drop order is bottom-up so
the orienting core survives budget pressure):

  1 DIRECTIVE  what am I doing?        next-focus note, age-stamped ([STALE] >= 7d)
  2 WHERE      where did we leave off? where-we-are note, 2 lines, age + curated flag
  3 SIBLINGS   who else is here?       live_incarnations() -- live, never age-stamped
  4 DELTA      what moved?             delta count (live)
  5 THEMES     what's the vibe?        session-themes note when < 30d old (age-stamped)
  6 MAIL       unread bus messages     (live)
  7 DRAFT      un-promoted last-session draft pointer
  8 FUNNEL     recall-value pulse      (live)
  9 BOOT       the one-hop full-boot command (the primer never replaces the ritual)
  + STORY      spill-only: the latest JOURNEY.md entry -- the values-carrier rides
               along when the budget has room, never at a working section's expense.

Budget: AKASHIC_WHISPER_LINES lines total (default 12, ~800-char spirit via per-line
clamps). Tiering is unchanged from v1: repo/home get the whisper; anywhere else stays
SILENT unless something is genuinely NEW (then one line pointing home). Kill switch:
AKASHIC_AUTOBOOT=0. Full boot stays one hop away and remains the ritual.

Age stamps mark PROVENANCE (curated/auto/unflagged -- the flag beats inference; an
unflagged note claims nothing) and AGE, so a seat can tell a live signal from a note
that may have outlived its truth.
"""
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

from agent.harness.scope import repo_root, session_in_scope

_DRAFT_FRESH_SECS = 2 * 86400
_STALE_DAYS = 7                      # W5: note-derived lines gain [STALE] at this age
_THEMES_MAX_DAYS = 30                # R2: themes older than this stay off the whisper
_LINE_CLAMP = 150                    # per-line payload clamp (budget spirit, not a wall)
_DEFAULT_BUDGET_LINES = 12           # W6; AKASHIC_WHISPER_LINES overrides (R6)
_NOTE_WINDOW_DAYS = 60               # one store pull feeds every note-derived section

# W6 drop order under budget pressure: bottom-up, orienting core last (recon contract).
_DROP_ORDER = ("boot", "funnel", "draft", "mail", "themes", "delta")


# ---------------------------------------------------------------- data seams (monkeypatchable)
def _fetch_notes() -> list:
    """ONE decisions pull feeds DIRECTIVE + WHERE + THEMES (frugality: the whisper
    runs at every session start)."""
    from core.learning.agent_memory import get_agent_memory
    return get_agent_memory().get_decisions(days=_NOTE_WINDOW_DAYS)


def _live_siblings(agent_id: str, my_session: str = "") -> List[Dict]:
    from core.comm.incarnation import live_incarnations
    return live_incarnations(agent_id, my_session=my_session or None)


def _funnel_line() -> str:
    from core.recall.funnel import snapshot, summary_line
    return "funnel: " + summary_line(snapshot(hours=7 * 24))


def _unread_count(agent_id: str) -> int:
    """How much mail `bifrost-sync` would actually SURFACE (T201).

    The raw pending count counted the conductor's ledger_update/resolved echoes of this
    agent's OWN task transitions. Measured 2026-08-06: the whisper said "7 unread ->
    py agent_cli.py bifrost-sync claude" three times in one session, and running that on
    both lanes returned "(no messages consumed)" every time. The wake watcher already
    skips those kinds and the consume door already declines to surface them -- only this
    counter took them literally, so it nagged every turn about a condition its own
    printed remediation could not clear. That is the W131 pathology in a second organ:
    an alert that is routinely wrong teaches the reader to skip the line, and the habit
    carries into the turn when the number means real mail.

    Reuses the SHARED skip set rather than inventing a third meaning of "unread" (the
    T198 lesson, applied where it is safe to apply). FAILS TOWARD NAGGING, deliberately
    and opposite to T198: unknown kinds count, and a truncated peek adds its unseen
    remainder back, because under-reporting real mail is the worse error here while the
    wake path -- where the worse error is deafness -- is untouched by this function.
    """
    from agent.bifrost_pull import collect_boot_bifrost
    try:
        data = collect_boot_bifrost(agent_id, limit=8) or {}
    except Exception:
        return 0                                  # fail-soft: the whisper never breaks a turn
    pending = int(data.get("pending", 0) or 0)
    msgs = data.get("messages")
    if not isinstance(msgs, list):
        return pending                            # no rendered list -> cannot filter; say the raw truth
    try:
        from core.comm.bifrost_api import PENDING_SKIP_KINDS as _SKIP
    except Exception:
        return pending
    actionable = sum(1 for m in msgs
                     if str((m or {}).get("kind") or "") not in _SKIP)
    # The peek is capped, so anything beyond it was never classified. Count it.
    return actionable + max(0, pending - len(msgs))


def _draft_fresh() -> bool:
    p = os.path.join(repo_root(), "chronicles", "last-session-draft.md")
    try:
        return os.path.isfile(p) and (time.time() - os.path.getmtime(p)) < _DRAFT_FRESH_SECS
    except Exception:
        return False


def _delta_count(agent_id: str) -> int:
    """T052 delta door count. The whisper NEVER commits the mark -- only delivered
    full boots do, per the mark-lag contract."""
    from agent.harness.delta import DeltaMark, current_positions, _moved, FIELDS
    mk = DeltaMark(agent_id).read()
    if not mk:
        return 0
    cur = current_positions(agent_id)
    return sum(1 for f in FIELDS if _moved(mk[f], cur[f]))


def _journey_latest() -> str:
    """Latest dated JOURNEY.md entry title, or ''. The story is the values-carrier
    (creative-robustness reconciliation) -- one pointer, never the text."""
    path = os.path.join(repo_root(), "docs", "JOURNEY.md")
    latest = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("## 20"):            # dated entries only
                    latest = line[3:].strip()
    except Exception:
        return ""
    return latest


# ---------------------------------------------------------------- small pure helpers
def _budget_lines() -> int:
    try:
        return max(3, int(os.getenv("AKASHIC_WHISPER_LINES", "") or _DEFAULT_BUDGET_LINES))
    except Exception:
        return _DEFAULT_BUDGET_LINES


def _one_line(text: str) -> str:
    return " ".join(str(text or "").split())


def _clip(text: str, n: int = _LINE_CLAMP) -> str:
    t = _one_line(text)
    return t if len(t) <= n else t[: n - 3] + "..."


def _age_parts(created_at: str, now: Optional[float] = None):
    """(age_str, age_days) from an ISO timestamp; (None, None) when unparseable."""
    try:
        ts = datetime.fromisoformat(str(created_at)).timestamp()
    except Exception:
        return None, None
    secs = max(0.0, (now if now is not None else time.time()) - ts)
    mins = secs / 60.0
    if mins < 60:
        return f"{mins:.0f}m ago", secs / 86400.0
    hours = mins / 60.0
    if hours < 48:
        return f"{hours:.0f}h ago", secs / 86400.0
    return f"{secs / 86400.0:.0f}d ago", secs / 86400.0


def _find_note(notes: list, title: str):
    for d in notes:
        if getattr(d, "title", "") == title and not getattr(d, "superseded", False):
            return d
    return None


def _mailbox_line(agent_id: str) -> str:
    """T095-M1 orientation, one line: what a fresh seat cannot otherwise learn.

    `read_but_undeclared` is the point -- mail some PRIOR incarnation opened and declared nothing
    about. Before M1 that was indistinguishable from never-seen, so every new seat re-adjudicated
    the same questions its predecessor had already read.

    Fail-SILENT toward boot (an orientation line must never be able to break the boot it decorates)
    but HONEST about its own bounds: entries whose body did not survive are counted separately
    rather than folded in, because a count that mixes 'you can read this' with 'this is gone' is
    the kind of quiet completeness claim this arc exists to end.
    """
    try:
        from core.comm import mailbox
        from core.comm.bus import Bus
        if not mailbox.enabled():
            return ""
        bus = Bus("boot-mailbox", promote=False)
        # Three Redis calls, size-independent. The first two cuts of this line cost 3.8s and 3.2s
        # per boot -- the second because it still went through query(), which resolves every
        # entry's tier, cursors and acks to answer a question that needs none of them. An
        # orientation surface that taxes every boot stops being orientation.
        c = mailbox.orientation_counts(bus.ns, agent_id, client=bus._client)
        unopened, undeclared = c["unopened"], c["read_but_undeclared"]
        if not (undeclared or unopened):
            return ""
        # Body availability is deliberately NOT counted here: it needs a read per entry, which is
        # the cost this rewrite removed. It is reported per-message by --open/--state instead.
        # Omitting a field is honest; asserting one cheaply and wrongly would not be.
        return (f"mailbox: {unopened} unopened | {undeclared} read-but-undeclared -> "
                f"py agent_cli.py mailbox {agent_id} --state <sha> | --open <sha>")
    except Exception:
        return ""


def _note_line(prefix: str, note, body_clip: int = _LINE_CLAMP, flag: str = "") -> str:
    """'PREFIX: <body> (<flag, >Nh ago)' with a [STALE] marker past _STALE_DAYS (W4/W5)."""
    age_str, age_days = _age_parts(getattr(note, "created_at", ""))
    suffix = f" ({flag}{age_str})" if age_str else (f" ({flag.rstrip(', ')})" if flag else "")
    stale = "[STALE] " if (age_days is not None and age_days >= _STALE_DAYS) else ""
    return f"{stale}{prefix}: {_clip(getattr(note, 'decision', ''), body_clip)}{suffix}"


# ---------------------------------------------------------------- the whisper
def build_autoboot_context(cwd: str, agent_id: str, session_id: str = "") -> str:
    """The whisper text for this session's start point, or "" for silence. Each data
    pull is independently fail-soft: a broken piece drops out, it never blanks the rest.
    `session_id` (new, T074 W3) lets SIBLINGS exclude the caller's own incarnation."""
    if os.getenv("AKASHIC_AUTOBOOT", "1") == "0":
        return ""
    home_or_repo = session_in_scope(cwd)

    unread = 0
    try:
        unread = _unread_count(agent_id)
    except Exception:
        pass
    fresh_draft = _draft_fresh()

    if not home_or_repo:
        if not unread and not fresh_draft:
            return ""   # unrelated project, nothing new -> full silence
        bits = []
        if unread:
            bits.append(f"{unread} unread bus msg(s)")
        if fresh_draft:
            bits.append("a fresh last-session draft")
        return (f"[akashic] {' and '.join(bits)} waiting -- "
                f"py agent_cli.py boot {agent_id} --task \"...\"  (repo: {repo_root()})")

    notes: list = []
    try:
        notes = _fetch_notes()
    except Exception:
        pass
    siblings: List[Dict] = []
    try:
        siblings = _live_siblings(agent_id, session_id)
    except Exception:
        pass
    delta_n = 0
    try:
        delta_n = _delta_count(agent_id)
    except Exception:
        pass
    funnel = ""
    try:
        funnel = _funnel_line() or ""
    except Exception:
        pass

    directive = _find_note(notes, "next-focus")
    where = _find_note(notes, "where-we-are")
    themes = _find_note(notes, "session-themes")
    if themes is not None:
        _, t_days = _age_parts(getattr(themes, "created_at", ""))
        if t_days is None or t_days >= _THEMES_MAX_DAYS:
            themes = None                                  # R2: an old vibe is noise

    # Silence rule (v1-compatible): no real signal anywhere -> say nothing at all.
    if not any((directive, where, themes, siblings, unread, fresh_draft, delta_n, funnel)):
        return ""

    # ---- assemble sections in priority order: (key, [payload lines]) --------------
    sections: List = []

    if directive is not None:
        d_line = _note_line("DIRECTIVE", directive, body_clip=110)
    else:
        d_line = "DIRECTIVE: none active -- check the ledger: py agent_cli.py task list"
    sections.append(("directive", [d_line]))

    if where is not None:
        cur = getattr(where, "curated", None)
        flag = "curated, " if cur is True else ("auto, " if cur is False else "")
        w_lines = [_note_line("WHERE", where, body_clip=_LINE_CLAMP, flag=flag)]
        rest = _one_line(getattr(where, "decision", ""))[_LINE_CLAMP - 3:]
        if len(rest) > 40:                                  # a second line only when it earns itself
            w_lines.append("  " + _clip(rest, _LINE_CLAMP))
    else:
        w_lines = ["WHERE: (no where-we-are note yet -- record one: "
                   f"py agent_cli.py note {agent_id} --title where-we-are)"]
    sections.append(("where", w_lines))

    try:
        from core.comm.incarnation import siblings_line
        sections.append(("siblings", [f"SIBLINGS: {siblings_line(agent_id, siblings)}"]))
    except Exception:
        pass

    if delta_n:
        sections.append(("delta", [f"delta: {delta_n} source(s) moved since your last boot -> "
                                   f"py agent_cli.py delta {agent_id}"]))
    if themes is not None:
        sections.append(("themes", [_note_line("THEMES", themes, body_clip=120)]))
    if unread:
        # W8 (T081): Prometheus-style denominator label -- the whisper peek reads the LEGACY
        # cursor (all lanes during dual-write, first 8). Name what's counted so the operator
        # stops asking "why 8 here vs 10 in sync?" -- they measure different things.
        try:
            from core.comm.bifrost_api import BifrostAPI
            scope = "work-lane" if BifrostAPI.consume_lane_enabled() else "all lanes"
        except Exception:
            scope = "legacy peek"
        sections.append(("mail", [f"mail: {unread} unread ({scope}) -> "
                                  f"py agent_cli.py bifrost-sync {agent_id}"]))
    # T095-M1: the mailbox becomes INHABITED here. The verbs shipped wired to a door, but a door
    # nobody walks through is not a mailbox -- a seat only benefits if the state reaches the place
    # it already looks. `read_but_undeclared` is the load-bearing count: mail a PRIOR incarnation
    # opened and said nothing about. Without this line a fresh seat cannot tell that from unread,
    # which is the gap this whole arc exists to close.
    mbx_line = _mailbox_line(agent_id)
    if mbx_line:
        sections.append(("mailbox", [mbx_line]))
    if fresh_draft:
        sections.append(("draft", ["draft: chronicles/last-session-draft.md -> review; promote with "
                                   "`py agent_cli.py wrap --commit`"]))
    if funnel:
        sections.append(("funnel", [funnel]))
    sections.append(("boot", [f"boot: py agent_cli.py boot {agent_id} --task \"<this slice>\"  "
                              "(full context, one hop)"]))

    # ---- budget: drop bottom-up, orienting core last (W6) -------------------------
    budget = _budget_lines()
    total = lambda: sum(len(body) for _, body in sections)
    for key in _DROP_ORDER:
        if total() <= budget:
            break
        sections = [(k, b) for k, b in sections if k != key]
    if total() > budget and len(w_lines) > 1:               # last resort: WHERE folds to 1 line
        sections = [(k, (b[:1] if k == "where" else b)) for k, b in sections]

    # ---- STORY spill (R3): rides along only when the budget has room --------------
    if total() < budget:
        try:
            latest = _journey_latest()
            if latest:
                sections.append(("story", [f"STORY: docs/JOURNEY.md -- {_clip(latest, 110)}"]))
        except Exception:
            pass

    # ---- render: first line owns the [akashic] tag, the rest indent ---------------
    lines: List[str] = []
    for _, body in sections:
        lines.extend(body)
    lines = lines[:budget]
    out = [f"[akashic] {lines[0]}"]
    out.extend("  " + l for l in lines[1:])
    return "\n".join(out)
