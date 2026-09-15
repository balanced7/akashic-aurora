// Written accidentals of one bar: arsenal/web/piano/score/accidentals.js (pure ES module: no DOM, no clock). The one rule
// musicxml.js (the export) and layout.js (the lab's settled bars) both apply, per ls1-rulings.md "LS2close to LS5 rulings",
// Accidentals (standard engraving practice):
//   - state is tracked per staff and staff position (letter and octave), and the bar is read in written order: by time
//     position, then by pitch. A note prints its accidental when its alteration differs from the state (the key signature
//     until an accidental in the bar sets it), and the printed alteration becomes the state to the end of the bar.
//   - two alterations of one staff position at one time position (F4 and F#4) both print (a natural and a sharp).
//   - a piece a tie continues never prints one. After a note tied in across the bar line, a later different alteration of
//     that staff position in the bar prints a courtesy accidental (in parentheses) when no accidental would print otherwise;
//     a printed accidental (courtesy or not) ends that courtesy duty.
//   - duplicate pitches at one time position on one staff (two MusicXML lanes, or two voices) share the decision, so every
//     copy prints it.
//
//   decideAccidentals(items, sigAlters) -> Map(ref -> { acc: alteration | null, courtesy: boolean })
//     items: [{ ref, staff, pos, pitch (MIDI, for order), letter (0-6, C = 0), octave, alter, tieStop, tiedIn }]
//            tiedIn: a piece continuing a note from the previous bar (tieStop at the bar's start).
//     sigAlters: the key signature's alteration per letter ([C, D, E, F, G, A, B]).
// "That letter" in the courtesy rule is read as the same staff position (letter and octave), the unit the state is kept in.

export const ACCIDENTALS_API = "arsenal.piano.score.accidentals/v0";

export function decideAccidentals(items, sigAlters) {
  const out = new Map();
  const byStaff = new Map();
  for (const it of items) { if (!byStaff.has(it.staff)) byStaff.set(it.staff, []); byStaff.get(it.staff).push(it); }
  for (const list of byStaff.values()) {
    list.sort((a, b) => a.pos - b.pos || a.pitch - b.pitch);
    const state = new Map(), tied = new Map();
    for (let i = 0; i < list.length;) {
      let j = i;
      while (j < list.length && list[j].pos === list[i].pos) j++;
      const at = list.slice(i, j), P = list[i].pos;
      i = j;
      const byKey = new Map();
      for (const it of at) {
        const k = it.letter * 16 + it.octave;
        if (!byKey.has(k)) byKey.set(k, []);
        byKey.get(k).push(it);
        if (it.tiedIn && !tied.has(k)) tied.set(k, { alter: it.alter, pos: P });
      }
      for (const [k, group] of byKey) {
        const clash = new Set(group.map((x) => x.alter)).size > 1;
        const letter = group[0].letter;
        const alters = [];
        for (const it of group) if (!it.tieStop && !alters.includes(it.alter)) alters.push(it.alter);
        for (const a of alters) {
          const cur = state.has(k) ? state.get(k) : sigAlters[letter] || 0;
          let acc = null, courtesy = false;
          if (clash || cur !== a) acc = a;
          else if (tied.has(k) && tied.get(k).alter !== a && tied.get(k).pos < P) { acc = a; courtesy = true; }
          if (acc !== null) { state.set(k, a); tied.delete(k); }
          for (const it of group) if (!it.tieStop && it.alter === a) out.set(it.ref, { acc, courtesy });
        }
        for (const it of group) if (it.tieStop) out.set(it.ref, { acc: null, courtesy: false });
      }
    }
  }
  return out;
}
