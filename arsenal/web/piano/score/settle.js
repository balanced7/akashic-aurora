// Bar states for a live score that settles without rewriting itself: arsenal/web/piano/score/settle.js (pure ES module:
// no DOM, no clock). Stage T9 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (section 6.7)
// and transcription.md T9.
//
//   const st = createSettle({ settleBeats: 4 });
//   st.upsert(index, { sig, endBeat, end_ms })      // the bar's current content; rev rises when an unsettled bar changes
//   st.advance({ T, beat, lastOnsetMs })            // open -> settling -> settled, returns the bars that moved
//   st.settleAll("hold" | "source" | "end")          // a hold, a source switch or the session end settles everything
//   st.drop(fromIndex)                              // forward-only correction: unsettled bars from here are rebuilt
//
// States (plan 6.7):
//   open      the playhead is inside the bar                                    everything may change
//   settling  the bar has ended (its end beat has arrived, or T passed its end)   rhythm, voices, staff, spelling, marks
//   settled   settleBeats (4) beats past its end, a pause of pauseMs (2 s) after the bar ended, a hold, a source
//             switch, or session end                                               never, in the live view
// A settled bar's content is final: upsert() on a settled bar with a different signature is refused and counted
// (violations(), receipt LR6a), and drop() never removes a settled bar. Corrections learned late (a level flip, "This is
// 1", a key change) start at firstUnsettled(). beat is a monotonic count of beats in the caller's unit (tactus beats).

export const SETTLE_API = "arsenal.piano.score.settle/v0";

export const SETTLE_PARAMS = Object.freeze({ settleBeats: 4, pauseMs: 2000 });

export function createSettle(params = {}) {
  const c = { ...SETTLE_PARAMS, ...params };
  const bars = new Map();
  let violations = 0, maxSettled = -Infinity;

  function upsert(index, { sig, endBeat = null, start_ms = null, end_ms = null, meta = null } = {}) {
    let b = bars.get(index);
    if (b && b.state === "settled") {
      if (sig !== b.sig) { violations++; return { changed: false, refused: true, rev: b.rev, state: b.state }; }
      return { changed: false, refused: false, rev: b.rev, state: b.state };
    }
    if (!b) {
      b = { index, state: "open", rev: 0, sig, endBeat, start_ms, end_ms, meta, settlingAt: null, settledAt: null, reason: null };
      bars.set(index, b);
      return { changed: true, refused: false, rev: 0, state: b.state };
    }
    b.endBeat = endBeat; b.start_ms = start_ms; b.end_ms = end_ms; if (meta) b.meta = meta;
    if (sig !== b.sig) { b.sig = sig; b.rev++; return { changed: true, refused: false, rev: b.rev, state: b.state }; }
    return { changed: false, refused: false, rev: b.rev, state: b.state };
  }

  function settle(b, T, reason) {
    b.state = "settled"; b.settledAt = T; b.reason = reason;
    if (b.index > maxSettled) maxSettled = b.index;
  }

  function advance({ T, beat = -Infinity, lastOnsetMs = null } = {}) {
    const settling = [], settled = [];
    const paused = lastOnsetMs != null && T - lastOnsetMs >= c.pauseMs;
    for (const b of [...bars.values()].sort((x, y) => x.index - y.index)) {
      if (b.state === "settled") continue;
      const ended = (b.endBeat != null && beat >= b.endBeat) || (b.end_ms != null && T >= b.end_ms);
      if (b.state === "open" && ended) { b.state = "settling"; b.settlingAt = T; settling.push(b.index); }
      if (b.state === "settling") {
        if (b.endBeat != null && beat >= b.endBeat + c.settleBeats) { settle(b, T, "beats"); settled.push(b.index); }
        else if (paused && b.end_ms != null && lastOnsetMs < b.end_ms && T >= b.end_ms) { settle(b, T, "pause"); settled.push(b.index); }
        else if (paused && b.end_ms != null && lastOnsetMs >= b.end_ms) { settle(b, T, "pause"); settled.push(b.index); }
      }
    }
    return { settling, settled };
  }

  function settleAll(reason, T = null, upto = Infinity) {
    const out = [];
    for (const b of [...bars.values()].sort((x, y) => x.index - y.index)) {
      if (b.state === "settled" || b.index > upto) continue;
      settle(b, T, reason); out.push(b.index);
    }
    return out;
  }

  function drop(fromIndex) {
    const out = [];
    for (const [i, b] of bars) if (i >= fromIndex && b.state !== "settled") { bars.delete(i); out.push(i); }
    return out.sort((a, b) => a - b);
  }

  function firstUnsettled() {
    let lo = Infinity;
    for (const b of bars.values()) if (b.state !== "settled" && b.index < lo) lo = b.index;
    return lo === Infinity ? (maxSettled === -Infinity ? null : maxSettled + 1) : lo;
  }

  return {
    upsert, advance, settleAll, drop, firstUnsettled,
    get: (i) => { const b = bars.get(i); return b ? { ...b } : null; },
    state: (i) => (bars.has(i) ? bars.get(i).state : null),
    list: () => [...bars.values()].sort((x, y) => x.index - y.index).map((b) => ({ ...b })),
    lastSettled: () => (maxSettled === -Infinity ? null : maxSettled),
    violations: () => violations,
    params: () => ({ ...c }),
  };
}
