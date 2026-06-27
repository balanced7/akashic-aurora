"""
Hand-labeled gold fixture for the auto-logger query layer (the local benchmark).

~40 raw events across four domain clusters with DISTINCT vocabularies (ai-setup /
research / stemroller / vision), each cluster on its own day. The distinct vocab is
deliberate: it makes keyword search's job possible and the gold sets unambiguous, so
window-recall and search-precision are honest, reproducible numbers -- not vibes.

`build_events_fixture(event_log)` captures the rows into the given (isolated) EventLog and
returns the gold answers:
  - window  : a span + the exact set of in-window event summaries (recall must be 100%)
  - queries : QA queries + their gold-relevant summaries (precision@5 must be >= 0.8)
  - filters : per kind / track / agent counts (exact-filter checks)

Identify events by their (unique) `summary`. When a real event exposes a missing case,
add it HERE first -- it becomes a permanent regression anchor.
"""

# (at, kind, agent, track, summary)
_ROWS = [
    # ---- Day 1: ai-setup (vocab: ledger store redis chronicler bootstrap narrative) ----
    ("2026-06-20T09:00:00", "command",     "claude",   "ai-setup", "bootstrap booted the narrative chronicler"),
    ("2026-06-20T10:00:00", "file_edit",   "claude",   "ai-setup", "edit core ledger store dual-write path"),
    ("2026-06-20T11:00:00", "tool_call",   "claude",   "ai-setup", "ran chronicler over the redis ledger"),
    ("2026-06-20T12:00:00", "observation", "claude",   "ai-setup", "redis store reconciler healed file drift"),
    ("2026-06-20T13:00:00", "learning",    "claude",   "ai-setup", "bootstrap narrative chronicler idempotent rerun"),
    ("2026-06-20T14:00:00", "note",        "claude",   "ai-setup", "ledger chronicler atlas regenerated cleanly"),

    # ---- Day 2: research (vocab: raptor graphrag zettelkasten arxiv disentanglement) ----
    ("2026-06-21T09:00:00", "observation", "claude",   "research", "read the raptor recursive tree arxiv paper"),
    ("2026-06-21T10:00:00", "note",        "claude",   "research", "graphrag versus raptor skeleton comparison"),
    ("2026-06-21T11:00:00", "learning",    "claude",   "research", "track inference equals conversation disentanglement"),
    ("2026-06-21T12:00:00", "note",        "claude",   "research", "zettelkasten para analogues for tracks themes"),
    ("2026-06-21T13:00:00", "observation", "claude",   "research", "zep temporal graphrag bi-temporal arxiv notes"),
    ("2026-06-21T14:00:00", "learning",    "claude",   "research", "raptor disentanglement zettelkasten synthesis"),

    # ---- Day 3: stemroller (vocab: stemroller demucs vocals stem separation zluda) ----
    ("2026-06-22T09:00:00", "command",     "opencode", "stemroller", "stemroller amd zluda fork build setup"),
    ("2026-06-22T10:00:00", "file_edit",   "opencode", "stemroller", "wire demucs stem separation pipeline"),
    ("2026-06-22T11:00:00", "tool_call",   "opencode", "stemroller", "run demucs vocals stem separation job"),
    ("2026-06-22T12:00:00", "observation", "opencode", "stemroller", "vocals isolated in the stemroller demo"),
    ("2026-06-22T13:00:00", "learning",    "opencode", "stemroller", "zluda hip sdk path needed for demucs"),
    ("2026-06-22T14:00:00", "note",        "opencode", "stemroller", "stemroller packaging with demucs models"),

    # ---- Day 4: vision (vocab: florence comfyui directml ocr vision) ----
    ("2026-06-23T09:00:00", "command",     "opencode", "vision", "launch comfyui florence directml workflow"),
    ("2026-06-23T10:00:00", "file_edit",   "opencode", "vision", "edit florence comfyui ocr node config"),
    ("2026-06-23T11:00:00", "tool_call",   "opencode", "vision", "run florence ocr over the vision scan"),
    ("2026-06-23T12:00:00", "observation", "opencode", "vision", "comfyui directml vision throughput measured"),
    ("2026-06-23T13:00:00", "learning",    "opencode", "vision", "florence directml beats cpu for ocr vision"),
    ("2026-06-23T14:00:00", "note",        "opencode", "vision", "comfyui florence pipeline packaged"),

    # ---- scattered lifecycle / noise (distinct, low-keyword) ----
    ("2026-06-20T08:00:00", "session",     "system",   "ai-setup", "Session started"),
    ("2026-06-23T18:00:00", "session",     "system",   "ai-setup", "Session ended"),
    ("2026-06-21T16:00:00", "boot",        "gpt",      None,        "gpt agent booted for a quick triage"),
]

# distinct cluster vocabularies (the four QA queries)
_QUERIES = [
    ("demucs vocals stem separation", "stemroller"),
    ("florence comfyui directml vision", "vision"),
    ("raptor zettelkasten disentanglement arxiv", "research"),
    ("chronicler ledger bootstrap redis", "ai-setup"),
]

# the window covers all of Day 3 -> exactly the six stemroller events
_WINDOW = ("2026-06-22T00:00:00", "2026-06-22T23:59:59")


def build_events_fixture(event_log):
    """Capture the gold rows into `event_log`; return the gold-answer metadata."""
    for at, kind, agent, track, summary in _ROWS:
        event_log.capture(kind, summary, agent_id=agent, track=track, at=at)

    in_window = [r[4] for r in _ROWS if _WINDOW[0] <= r[0] <= _WINDOW[1]]

    # a query's relevant set = the domain cluster's working events (its track, minus
    # lifecycle noise). Each cluster has 6 keyword-bearing events -> a clean precision@5.
    queries = []
    for q, cluster in _QUERIES:
        relevant = {r[4] for r in _ROWS if r[3] == cluster and r[1] not in ("session", "boot")}
        queries.append({"q": q, "relevant": relevant, "k": 5})

    by_kind, by_track, by_agent = {}, {}, {}
    for _at, kind, agent, track, _s in _ROWS:
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_track[track] = by_track.get(track, 0) + 1
        by_agent[agent] = by_agent.get(agent, 0) + 1

    return {
        "n": len(_ROWS),
        "window": {"start": _WINDOW[0], "end": _WINDOW[1], "expected": set(in_window)},
        "queries": queries,
        "by_kind": by_kind, "by_track": by_track, "by_agent": by_agent,
    }
