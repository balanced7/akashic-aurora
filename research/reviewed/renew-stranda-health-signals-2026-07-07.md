# RENEW Strand A — Cheap deterministic context-health signals (empirical)

**Status:** first empirical pass complete, 2026-07-07 · **Author:** claude
**Scope:** open-docket item A (`[EMPIRICAL — core]`) — "Cheap deterministic health signals that
predict degraded output." Prerequisite before building the membrane's Renew job.
**Design context:** `docs/agent-membrane-design-2026-07.md` §Renew · `renew-membrane-temporal-job` note.

---

## TL;DR (what changed)

1. **The signals are cheaply computable from data we already keep** — confirmed on 3,969 real tool
   traces (`research/in-flight/bus-20260707.jsonl`). ✅
2. **But the docket's suggested outcome label is the wrong construct, and no *right* label is durably
   captured.** FAIL→SUCCESS flips measure *recall utility* (did a surfaced lesson help), not
   *working-context health* — and on the data they cluster in the **most productive** sessions.
   Raw FAIL events are never persisted; human interjections total 2. **The blocking gap for Strand A is
   the label, not the signal.** The docket's "instrument + correlate" is inverted — instrument the
   *label* first.
3. **Negative result: raw reread rate does NOT discriminate health.** It saturates at 0.62–0.77 the
   moment any iterative file work happens, identically across a 4.75 h productive session and a 17 min
   one. GPT's "they start rereading files" tell does not survive contact with real traces as a *raw*
   signal. Demote it; the promising form is **progress-normalized** (churn ÷ progress), not raw churn.

**Recommendation:** do **not** build the health estimator yet. Ship a tiny **label-capture** slice
first (persist FAIL / abandoned / steer as durable events), accumulate ~10–20 labeled sessions, *then*
correlate. Everything downstream (policy C, gate D) is un-earnable until a degraded-output label exists.

---

## Method

- **Signal source:** `research/in-flight/bus-20260707.jsonl` (the `renew_bus_recorder.py` "two-birds"
  dataset). 5,033 captured bus events; **3,969 `kind=trace, meta.trace=tool`** tool-call traces spanning
  **2026-07-04 07:22 → 2026-07-07 05:51 UTC** (~3 days).
- **Label source:** `core.events.event_log` durable firehose (`events:raw`). 25 `flip` events
  (2026-07-02 → 07-07), 92 `boot` events, **2** `interjection` events, **0** durable `fail` events.
- **Signals computed per session** (session = >20 min idle gap; a proxy — exact boot boundaries live in
  the 92 `boot` events and are a cheap refinement): tool-call count, **reread rate** (fraction of
  Read/Edit/Write whose target was already touched this session), **repetition rate** (consecutive
  identical `(tool,target)`), **max-file-touch** (times the single most-touched file was hit).
- Analysis scripts (scratchpad, reproducible): `renew_stranda_mine.py`, `renew_stranda_join.py`.
  Deterministic, no LLM — consistent with the discipline ("No LLM judge for health").

## Findings — claude's 13 sessions, flips overlaid

| calls | reread | rep | maxTouch | flips | window (UTC) | note |
|------:|-------:|----:|---------:|------:|--------------|------|
| 712 | 0.735 | 0.129 | **32** | 3 | 07-07 01:06→05:51 (4.75 h) | shipped membrane slices — **healthy, high churn** |
| 192 | 0.625 | 0.073 | 16 | 1 | 07-04 22:02→00:04 | |
| 114 | 0.625 | 0.061 | 6 | 0 | 07-05 12:41→14:20 | |
| 65 | **0.765** | 0.154 | 10 | 1 | 07-06 00:10→00:27 (17 min) | highest reread, tiny session |
| 51 | 0.375 | 0.02 | 3 | 0 | 07-06 00:58→01:25 | |
| ≤22 | ≤0.25 | — | ≤2 | 0 | (8 short sessions) | little/no file work |

**Reads:**
- **Reread rate is non-discriminating.** 0.625–0.765 across every session with real file activity,
  independent of duration, call volume, or flip count. It flags "iterating on files," not "in trouble."
- **max-file-touch and call count scale with duration** — but the longest, highest-churn session was the
  *most productive* (3 flips, shipped work). So raw magnitude ≠ debt.
- **Flips cluster in high-activity sessions** (3 in the big one). They track *progress*, confirming they
  are the wrong sign for *degradation*. A degraded session is one with high churn and **no** progress
  markers — which is exactly what we cannot see today, because we log progress (flips) but not stalls.

## Data-quality caveats (honest bounds)

- Recorder window is only ~3 days (07-04→07-07); n=13 claude sessions, ~5 with meaningful file work.
  **Underpowered** — descriptive, not inferential.
- Target extraction is regex-heuristic. **Trace formats are agent-specific**: claude emits `Tool · desc`;
  **deepseek emits `read_file(path=…)` function-call style** (2,784 traces the claude parser scored as
  `?`). A per-agent parser is needed before deepseek health is measurable.
- Session boundaries are idle-gap proxies; join to the 92 durable `boot` events for exact
  turns-since-boot.

## Signal catalog (cost-tagged), revised by evidence

| Signal | Where / cost | Verdict from this pass |
|---|---|---|
| **reread rate (raw)** | PostToolUse, free | **Demote** — non-discriminating (saturates high) |
| calls-since-last-progress (flip / task-close / commit) | free (join to event_log) | **Promising** — the churn÷progress normalizer; untested (need label) |
| repetition of the *same failing* action | needs durable FAIL label | **Promising** — but blocked on label capture |
| max-file-touch, tool-call count | PostToolUse, free | Duration proxies; only useful *normalized* by progress |
| turns-since-boot | 92 boot events, free | Cheap context-age input to a policy; not a health signal alone |
| task-ledger churn | `state/coord/tasks.json`, cheap scan | Not yet tested; plausible |
| superseded-record density | `core/primitives/supersession.py active_only`, scan | Matches the doc's "48%-full-of-superseded" framing; untested |
| stale-lock count | lock dir (path unconfirmed) | Untested; low priority |

Existing accumulator to extend, **not** rebuild: `core/coord/cognitive_metrics.py` already has
`duplicate_file_reads`, `waste_ratio`, `record_tool_call` classification, `record_context_refresh`,
`record_human_interjection`. The health estimator is a *consumer* of these, once a label exists.

## Recommended next slice — invert to label-first

**A′ (label capture, ~small):** persist the degraded-output label as durable `event_log` events —
(1) FAIL / failed-then-retried action (already computed transiently in `claude_posttooluse.py`; just
`capture_event`), (2) abandoned-work / context-refresh, (3) human steer/HALT/interjection. This is the
missing half of the ground truth and is nearly free — the detections already exist, they simply aren't
written down.

**Then** re-run this correlation with churn-÷-progress signals against a real label, on ~10–20
accumulated sessions, and only *then* (Strand C) propose a refresh policy. Gate D stays unchanged.

**Do not** ship a health threshold on reread rate — this pass shows it would fire on healthy deep work.

---
*Reproduce:* `py <scratchpad>/renew_stranda_mine.py` and `renew_stranda_join.py` against
`research/in-flight/bus-20260707.jsonl` + `core.events.event_log`.
