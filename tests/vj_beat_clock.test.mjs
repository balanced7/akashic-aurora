// Node tests for the page side of the engine's beat clock (2026-10-24): parseEvent takes the beat event's new optional
// fields and the tap and track events, and an older engine's beat still parses as before. Zero dependencies:
//   node tests/vj_beat_clock.test.mjs
// The engine side: tests/test_keylab_vj_clock.py. The build spec: research/reviewed/keylab-liberation-2026-10-22/
// vj-lasers-v2-and-colour-themes-2026-10-24.md, section 3.1.
import * as C from "../arsenal/web/vj-core.js";

let pass = 0, fail = 0;
function check(name, cond, detail = "") {
  if (cond) pass++;
  else { fail++; console.log(`FAIL ${name}${detail ? `: ${detail}` : ""}`); }
}
const P = C.parseEvent;

// ------------------------------------------------------------------------------------------- the beat's new fields --
{
  const b = P({ t: "beat", due_ms: 240, bpm: 150, conf: 0.9, n: 12, on_beat: -0.8, src: "tap", bar: 3, bar_src: "tap",
                ver: 2, offset_ms: -190.5, wall_ms: 1761300000123.4 });
  check("on_beat is no longer clamped at 0: -0.8 stays -0.8", b.on_beat === -0.8);
  check("src, bar, bar_src, ver, offset_ms, wall_ms pass through", b.src === "tap" && b.bar === 3 && b.bar_src === "tap" &&
        b.ver === 2 && b.offset_ms === -190.5 && b.wall_ms === 1761300000123.4, JSON.stringify(b));
  check("on_beat still clamps to -1..1", P({ t: "beat", due_ms: 1, bpm: 150, on_beat: -3 }).on_beat === -1 &&
        P({ t: "beat", due_ms: 1, bpm: 150, on_beat: 2 }).on_beat === 1);
  for (const src of ["db", "track", "tap"]) check(`src ${src}`, P({ t: "beat", due_ms: 1, bpm: 150, src }).src === src);
  const odd = P({ t: "beat", due_ms: 1, bpm: 150, src: "<script>", bar: 5, bar_src: "dream", ver: "x", offset_ms: 1e9 });
  check("odd values fall back to the defaults", odd.src === "" && odd.bar === 0 && odd.bar_src === "" && odd.ver === -1 &&
        odd.offset_ms === 1000, JSON.stringify(odd));
  check("a bar that is not a whole number is unknown", P({ t: "beat", due_ms: 1, bpm: 150, bar: 2.5 }).bar === 0);
  const old = P({ t: "beat", due_ms: 220, bpm: 121.5, conf: 0.7, n: 7, on_beat: 0.6 });
  check("an older engine's beat parses as before, the new fields at their defaults",
        old.on_beat === 0.6 && old.src === "" && old.bar === 0 && old.bar_src === "" && old.ver === -1 &&
        old.offset_ms === null && old.wall_ms === null && old.bpm === 121.5 && old.n === 7);
  const clock = new C.BeatClock();
  clock.schedule(1000, b);
  check("the beat clock keeps a negative on-beat score for the HUD", clock.onBeat === -0.8);
}

// --------------------------------------------------------------------------------------- the tap and track events --
{
  for (const mode of ["resync", "run", "lock", "release", "return"]) {
    check(`tap mode ${mode}`, P({ t: "tap", count: 4, mode, bpm: 150, shift: null })?.mode === mode);
  }
  const lock = P({ t: "tap", count: 4, mode: "lock", bpm: 150, shift: null });
  check("tap lock", lock.count === 4 && lock.bpm === 150 && lock.shift === null, JSON.stringify(lock));
  const rs = P({ t: "tap", count: 1, mode: "resync", bpm: null, shift: -0.499 });
  check("tap resync carries its shift", rs.shift === -0.499 && rs.bpm === null);
  check("a tap with an unknown mode is refused", P({ t: "tap", count: 1, mode: "dance" }) === null && P({ t: "tap" }) === null);
  check("a tap's numbers are clamped", P({ t: "tap", count: -3, mode: "run", bpm: 9000, shift: 4 }).count === 0 &&
        P({ t: "tap", count: 2, mode: "run", bpm: 9000 }).bpm === 300 && P({ t: "tap", mode: "resync", shift: 4 }).shift === 0.5);
  const tr = P({ t: "track", bpm_db: 150, key_db: null });
  check("track with a database tempo", tr.t === "track" && tr.bpm_db === 150 && tr.key_db === "");
  check("track with none", P({ t: "track", bpm_db: null }).bpm_db === null);
  check("track key_db only when chordsense could have written it", P({ t: "track", bpm_db: 128, key_db: "F minor" }).key_db === "F minor" &&
        P({ t: "track", key_db: "<b>" }).key_db === "");
}

console.log(`vj_beat_clock: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
