// Virtual Stage v0, the show runner: arsenal/web/stage/show.js (pure ES module). Tests: tests/stage_show.test.mjs.
//
// How the rig is played (design section 3.7, the Q-dance practice: about 90 % live, firing prepared building blocks to
// the beat). The show block of the scene names SECTIONS (intro, build, drop, break, groove), and each section names its
// look (programmer.js), its kinetic formation (kinetics.js, landed in time priority), its laser look (lasers.js), its
// camera sequence (camera.js) and its speed per bar. Everything changes ON BAR LINES.
//
//   demo mode   the scene's demo plan runs the sections in a loop by bars, and fires its pads on scheduled beats (KICK on
//               every drop downbeat, a laser hit every other bar, FLY-OUT on the drop's first ONE, a held laser gate into
//               the drop, DROP NOW in the build's last bar), so the receipts and Daniel's first look need nothing plugged in;
//   engine mode the section is "groove" until the player presses a pad: DROP NOW (pad 10) drops on the next downbeat and
//               runs the drop for its length, then back to groove.
//
// The pads (v0 subset of the design's KeyLab map): 1 KICK, 2 LASERS (press / release = hold is a gate), 6 FLY-OUT,
// 10 DROP NOW. The faders (absolute, CC105-113 as Arturia's FL script reads them): F1 strand, F4 lasers, F5 haze target,
// F6 speed (detents 1/4, 1/2, 1, 2, 4), F9 grand master.
//
// v1 (2026-10-25): a section may name a PHRASE ({name, repeats, camera}: phrases.js runs it from the section's ONE, and it
// ends with the section); the pads add 3 PHRASE GO (arm the phrase on the next bar line; pressed while one runs, the next
// repeat from the next bar line), 4 PHRASE NEXT (the step ends on the next bar line) and 7 PHRASE STOP. A demo pad rule
// may say from_bar / to_bar (the bars of its section it plays in).

export const SHOW_API = "arsenal.stage-show/v1";
export const SPEED_DETENTS = Object.freeze([0.25, 0.5, 1, 2, 4]);
export const speedFromFader = (v) => SPEED_DETENTS[Math.max(0, Math.min(4, Math.round(v * 4)))];

export class Show {
  constructor(rig, { demo = true } = {}) {
    this.rig = rig;
    this.show = rig.show || {};
    this.sections = this.show.sections || {};
    this.demo = demo;
    this.plan = (this.show.demo && this.show.demo.plan) || [];
    this.planBars = this.plan.reduce((s, p) => s + p.bars, 0);
    this.planStart = null;       // the beat position of the plan's first bar
    this.section = null;         // {name, startPos, bars}
    this.lastBar = null;
    this.lastBeat = null;
    this.pendingDrop = null;     // beat position a DROP NOW lands on
    this.dropUntil = null;
    this.events = [];
    this.padRules = (this.show.demo && this.show.demo.pads) || [];
    this.releases = [];          // [{pad, at (pos)}]
    this.log = [];
  }
  // the section the demo plan has at bar index b (from the plan start), and the bar's index inside it
  planAt(b) {
    if (!this.planBars) return { name: "groove", bar: b, bars: 16 };
    let q = ((b % this.planBars) + this.planBars) % this.planBars;
    for (const p of this.plan) { if (q < p.bars) return { name: p.section, bar: q, bars: p.bars }; q -= p.bars; }
    return { name: this.plan[0].section, bar: 0, bars: this.plan[0].bars };
  }
  // DROP NOW: the drop starts on the next downbeat after pos
  dropNow(grid, pos) {
    this.pendingDrop = grid.nextBarPos(pos);
    return this.pendingDrop;
  }
  // Advance to beat position pos. Returns the events since the last call: {type: "section", name, pos, bars} on a bar line
  // where the section changes, {type: "bar", pos, index}, {type: "pad", pad, vel, on, pos} (demo pads), {type: "speed", s}.
  update(grid, pos) {
    const ev = this.events;
    ev.length = 0;
    if (this.planStart === null) this.planStart = grid.nextBarPos(pos - 4 + 1e-6) - 0;   // the bar line at or before pos
    const barIdx = Math.floor((pos - this.planStart) / 4 + 1e-9);
    const beatIdx = Math.floor(pos + 1e-9);
    if (this.lastBar === null || barIdx !== this.lastBar) {
      const barPos = this.planStart + 4 * barIdx;
      // DROP NOW landing on this bar line re-aligns the plan so this bar is the drop's first
      if (this.pendingDrop !== null && barPos >= this.pendingDrop - 1e-6) {
        this.pendingDrop = null;
        if (this.demo && this.planBars) {
          let before = 0;
          for (const p of this.plan) { if (p.section === "drop") break; before += p.bars; }
          this.planStart = barPos - 4 * before;
        } else {
          const len = (this.sections.drop && this.sections.drop.bars) || 16;
          this.dropUntil = barPos + 4 * len;
          this._enter("drop", barPos, len);
        }
      }
      const b2 = Math.floor((pos - this.planStart) / 4 + 1e-9);
      if (this.demo) {
        const at = this.planAt(b2);
        this._speedFor(at);                     // first: a look's new effects are born at the section's speed
        if (!this.section || at.name !== this.section.name) this._enter(at.name, this.planStart + 4 * b2 - 4 * at.bar, at.bars);
        // v1: a bar before a section that carries a phrase, say so (the stage pre-rolls its heads in black)
        const nx = this.planAt(b2 + 1);
        if (nx.bar === 0 && nx.name !== at.name && this.sections[nx.name] && this.sections[nx.name].phrase) {
          ev.push({ type: "prepare", section: nx.name, phrase: this.sections[nx.name].phrase.name, pos: this.planStart + 4 * (b2 + 1) });
        }
      } else {
        if (this.dropUntil !== null && barPos >= this.dropUntil - 1e-6) { this.dropUntil = null; this._enter("groove", barPos, 16); }
        if (!this.section) this._enter("groove", barPos, 16);
      }
      ev.push({ type: "bar", pos: barPos, index: barIdx });
      this.lastBar = barIdx;
    }
    if (this.lastBeat === null || beatIdx !== this.lastBeat) {
      if (this.demo) this._demoPads(grid, beatIdx);
      for (let i = this.releases.length - 1; i >= 0; i--) {
        if (this.releases[i].at <= pos + 1e-9) { ev.push({ type: "pad", pad: this.releases[i].pad, vel: 0, on: false, pos }); this.releases.splice(i, 1); }
      }
      this.lastBeat = beatIdx;
    }
    return ev;
  }
  _enter(name, startPos, bars) {
    this.section = { name, startPos, bars };
    this.events.push({ type: "section", name, pos: startPos, bars });
    if (this.log.length < 256) this.log.push({ name, pos: +startPos.toFixed(3) });
  }
  _speedFor(at) {
    const sec = this.sections[at.name];
    if (!sec || !sec.speed_by_bar) return;
    const s = sec.speed_by_bar[Math.min(sec.speed_by_bar.length - 1, at.bar)];
    if (s !== this._speed) { this._speed = s; this.events.push({ type: "speed", s }); }
  }
  _demoPads(grid, beatIdx) {
    const rel = beatIdx - this.planStart;
    if (rel < 0) return;
    const b = Math.floor(rel / 4), beat = (rel % 4) + 1;
    const at = this.planAt(b);
    for (const r of this.padRules) {
      if (r.section !== at.name || r.beat !== beat) continue;
      if (r.bar !== undefined && r.bar !== at.bar) continue;
      if (r.from_bar !== undefined && at.bar < r.from_bar) continue;
      if (r.to_bar !== undefined && at.bar >= r.to_bar) continue;
      if (r.every_bars !== undefined && at.bar % r.every_bars !== (r.offset_bars || 0)) continue;
      this.events.push({ type: "pad", pad: r.pad, vel: r.vel ?? 0.85, on: true, pos: beatIdx });
      this.releases.push({ pad: r.pad, at: beatIdx + (r.hold_beats ?? 0.25) });
    }
  }
}
