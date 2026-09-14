const Theory = (() => {
  const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
  const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
  const mod = (a, n) => ((a % n) + n) % n;

  // A spelling is { letter: 0..6, acc: -2..2 }.
  const pcOf = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);
  const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
  const nameOf = (sp) => LETTERS[sp.letter] + accText(sp.acc);
  const octaveOf = (midi, sp) => Math.floor((midi - sp.acc) / 12) - 1;  // B#3 is MIDI 60
  const diatonicOf = (midi, sp) => octaveOf(midi, sp) * 7 + sp.letter;  // C4 = 28

  function spellInterval(rootSp, semis, steps) {
    const letter = mod(rootSp.letter + steps, 7);
    const target = mod(pcOf(rootSp) + semis, 12);
    return { letter, acc: mod(target - LETTER_PC[letter] + 6, 12) - 6 };
  }

  function spellingsOf(pc) {
    const out = [];
    for (let letter = 0; letter < 7; letter++) {
      const acc = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
      if (Math.abs(acc) <= 1) out.push({ letter, acc });
    }
    return out;
  }

  // keyBias: +1 in sharp keys, -1 in flat keys, 0 when neutral or unknown.
  const ODD = new Set(["E#", "B#", "Cb", "Fb"]);
  const NEUTRAL = { 1: -1, 3: -1, 6: 1, 8: -1, 10: -1 };  // Db Eb F# Ab Bb
  function spellCost(sp, keyBias) {
    const a = Math.abs(sp.acc);
    let c = a === 2 ? 3 : a;
    if (ODD.has(nameOf(sp))) c += 1;
    if (keyBias > 0 && sp.acc < 0) c += 0.6 * a;
    if (keyBias < 0 && sp.acc > 0) c += 0.6 * a;
    return c;
  }
  function neutralTie(pc, sp) {
    const want = NEUTRAL[pc];
    return want && Math.sign(sp.acc) !== want ? 0.01 : 0;
  }
  function spellAlone(pc, keyBias) {
    let best = null;
    for (const sp of spellingsOf(pc)) {
      const c = spellCost(sp, keyBias) + neutralTie(pc, sp);
      if (!best || c < best.c) best = { sp, c };
    }
    return best.sp;
  }

  // Chord templates. tones: [semitones above the root, letter steps above the root].
  // cost: lower is a simpler, likelier reading. omit5: the perfect fifth may be missing.
  const T = (suffix, tones, cost, omit5 = false) => ({ suffix, tones, cost, omit5 });
  const TEMPLATES = [
    T("",        [[0, 0], [4, 2], [7, 4]], 0),
    T("m",       [[0, 0], [3, 2], [7, 4]], 0.1),
    T("dim",     [[0, 0], [3, 2], [6, 4]], 1.0),
    T("aug",     [[0, 0], [4, 2], [8, 4]], 1.2),
    T("sus4",    [[0, 0], [5, 3], [7, 4]], 1.5),
    T("sus2",    [[0, 0], [2, 1], [7, 4]], 1.6),
    T("7",       [[0, 0], [4, 2], [7, 4], [10, 6]], 1.0, true),
    T("maj7",    [[0, 0], [4, 2], [7, 4], [11, 6]], 1.0, true),
    T("m7",      [[0, 0], [3, 2], [7, 4], [10, 6]], 1.0, true),
    T("m7b5",    [[0, 0], [3, 2], [6, 4], [10, 6]], 1.4),
    T("dim7",    [[0, 0], [3, 2], [6, 4], [9, 5]], 1.5),  // 7th spelled as a 6th: C Eb Gb A, as lead sheets write it
    T("6",       [[0, 0], [4, 2], [7, 4], [9, 5]], 1.3, true),
    T("m6",      [[0, 0], [3, 2], [7, 4], [9, 5]], 1.5, true),
    T("add9",    [[0, 0], [2, 1], [4, 2], [7, 4]], 1.4, true),
    T("m(add9)", [[0, 0], [2, 1], [3, 2], [7, 4]], 1.6, true),
    T("m(maj7)", [[0, 0], [3, 2], [7, 4], [11, 6]], 1.8, true),
    T("7sus4",   [[0, 0], [5, 3], [7, 4], [10, 6]], 1.8, true),
    T("add11",   [[0, 0], [4, 2], [5, 3], [7, 4]], 2.0),
    T("7#5",     [[0, 0], [4, 2], [8, 4], [10, 6]], 2.0),
    T("maj7#5",  [[0, 0], [4, 2], [8, 4], [11, 6]], 2.2),
    T("7b5",     [[0, 0], [4, 2], [6, 4], [10, 6]], 2.2),
    T("6/9",     [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5]], 2.0, true),
    T("m6/9",    [[0, 0], [2, 1], [3, 2], [7, 4], [9, 5]], 2.2, true),
    T("9",       [[0, 0], [2, 1], [4, 2], [7, 4], [10, 6]], 2.0, true),
    T("maj9",    [[0, 0], [2, 1], [4, 2], [7, 4], [11, 6]], 2.0, true),
    T("m9",      [[0, 0], [2, 1], [3, 2], [7, 4], [10, 6]], 2.0, true),
    T("9sus4",   [[0, 0], [2, 1], [5, 3], [7, 4], [10, 6]], 2.4, true),
    T("7b9",     [[0, 0], [1, 1], [4, 2], [7, 4], [10, 6]], 2.4, true),
    T("7#9",     [[0, 0], [3, 1], [4, 2], [7, 4], [10, 6]], 2.4, true),
    T("maj7#11", [[0, 0], [4, 2], [6, 3], [7, 4], [11, 6]], 2.4, true),
    T("7#11",    [[0, 0], [4, 2], [6, 3], [7, 4], [10, 6]], 2.6, true),
    T("13",      [[0, 0], [4, 2], [7, 4], [9, 5], [10, 6]], 2.3, true),
    T("13",      [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5], [10, 6]], 2.8, true),
    T("maj13",   [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5], [11, 6]], 2.8, true),
    T("m11",     [[0, 0], [2, 1], [3, 2], [5, 3], [7, 4], [10, 6]], 2.5, true),
    T("m13",     [[0, 0], [2, 1], [3, 2], [7, 4], [9, 5], [10, 6]], 2.8, true),
    T("11",      [[0, 0], [2, 1], [4, 2], [5, 3], [7, 4], [10, 6]], 2.8, true),
  ];
  const keyOf = (semis) => [...semis].sort((a, b) => a - b).join(",");
  for (const t of TEMPLATES) {
    const semis = t.tones.map((x) => x[0]);
    t.key = keyOf(semis);
    t.keyNo5 = t.omit5 && semis.includes(7) ? keyOf(semis.filter((s) => s !== 7)) : null;
  }

  // Best reading of a set of distinct pitch classes (listed from the bass up).
  function matchSet(pcs, bassPc) {
    let best = null;
    for (const root of pcs) {
      const key = keyOf(pcs.map((p) => mod(p - root, 12)));
      for (const t of TEMPLATES) {
        const omitted = t.key !== key;
        if (omitted && t.keyNo5 !== key) continue;
        let cost = t.cost + (omitted ? 0.4 : 0);
        if (bassPc !== undefined && bassPc !== root) {
          const steps = t.tones.find((x) => x[0] === mod(bassPc - root, 12))[1];
          cost += steps === 2 || steps === 4 || steps === 6 ? 0.6 : 1.5;  // 3rd/5th/7th vs an extension
        }
        if (!best || cost < best.cost - 1e-9) best = { root, t, cost };
      }
    }
    return best;
  }

  const SIMPLE = ["unison", "minor 2nd", "major 2nd", "minor 3rd", "major 3rd", "perfect 4th", "tritone",
                  "perfect 5th", "minor 6th", "major 6th", "minor 7th", "major 7th", "octave"];
  const COMPOUND = { 13: "minor 9th", 14: "major 9th", 15: "minor 10th", 16: "major 10th", 17: "perfect 11th",
                     18: "augmented 11th", 19: "perfect 12th", 20: "minor 13th", 21: "major 13th" };
  const IV_STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6];

  function spelledNotes(notes, spellFor) {
    return notes.map((midi) => {
      const sp = spellFor(mod(midi, 12));
      return { midi, letter: sp.letter, acc: sp.acc, name: nameOf(sp), octave: octaveOf(midi, sp), diatonic: diatonicOf(midi, sp) };
    });
  }

  // midiNotes: every sounding MIDI note. Returns null for silence.
  function detect(midiNotes, keyBias = 0) {
    const notes = [...new Set(midiNotes)].sort((a, b) => a - b);
    if (!notes.length) return null;
    const bassPc = mod(notes[0], 12);
    const pcs = [];
    for (const n of notes) if (!pcs.includes(mod(n, 12))) pcs.push(mod(n, 12));

    if (pcs.length === 1) {
      const sp = spellAlone(pcs[0], keyBias);
      const out = spelledNotes(notes, () => sp);
      return { kind: "note", root: sp, suffix: "", bass: null, name: nameOf(sp) + (notes.length === 1 ? out[0].octave : ""),
               sub: notes.length === 1 ? "" : "octaves", octave: notes.length === 1 ? out[0].octave : null,
               pcNames: [nameOf(sp)], notes: out };
    }

    if (pcs.length === 2) {
      const lo = notes[0];
      const hi = notes.find((n) => mod(n, 12) !== bassPc);
      const semis = hi - lo;
      const ic = mod(semis, 12);
      let pick = null;
      for (const lsp of spellingsOf(bassPc)) {
        const hsp = spellInterval(lsp, ic, IV_STEPS[ic]);
        const c = spellCost(lsp, keyBias) + spellCost(hsp, keyBias) + neutralTie(bassPc, lsp);
        if (!pick || c < pick.c) pick = { lsp, hsp, c };
      }
      const map = { [bassPc]: pick.lsp, [mod(hi, 12)]: pick.hsp };
      const out = spelledNotes(notes, (pc) => map[pc]);
      const power = ic === 7;
      return { kind: power ? "chord" : "interval", root: pick.lsp, suffix: power ? "5" : "", bass: null, upper: pick.hsp,
               name: power ? nameOf(pick.lsp) + "5" : `${nameOf(pick.lsp)}-${nameOf(pick.hsp)}`,
               sub: power ? "power chord" : (semis > 12 ? (COMPOUND[semis] || SIMPLE[ic] + " (compound)") : SIMPLE[semis]),
               pcNames: [nameOf(pick.lsp), nameOf(pick.hsp)], notes: out };
    }

    let best = matchSet(pcs, bassPc);
    let slash = false;
    const lowestOther = notes.find((n) => mod(n, 12) !== bassPc);
    const bassOnlyLow = notes.every((n) => mod(n, 12) !== bassPc || n < lowestOther);
    if (bassOnlyLow && pcs.length >= 4) {
      const upper = matchSet(pcs.slice(1), undefined);
      // A foreign bass under a simple upper chord ("C/D") beats a strained full-set reading ("D9sus4"),
      // but not a plain one: B D F A stays Bm7b5, Bb C E G stays C7/Bb.
      if (upper && (!best || upper.cost + 1.7 < best.cost)) { best = { ...upper, cost: upper.cost + 1.7 }; slash = true; }
    }
    if (!best) {
      const map = {};
      for (const pc of pcs) map[pc] = spellAlone(pc, keyBias);
      return { kind: "cluster", root: null, suffix: "", bass: null, name: pcs.map((pc) => nameOf(map[pc])).join(" "),
               sub: "no chord name", pcNames: pcs.map((pc) => nameOf(map[pc])), notes: spelledNotes(notes, (pc) => map[pc]) };
    }

    // Spell the root so the chord's own tones read most simply, then spell every tone from it.
    let pick = null;
    for (const rsp of spellingsOf(best.root)) {
      const map = {};
      let c = neutralTie(best.root, rsp) + (ODD.has(nameOf(rsp)) ? 4 : 0);  // never a B# or Fb root
      for (const [semis, steps] of best.t.tones) {
        const pc = mod(best.root + semis, 12);
        if (!pcs.includes(pc)) continue;
        map[pc] = spellInterval(rsp, semis, steps);
        c += spellCost(map[pc], keyBias);
      }
      if (slash) {
        const semis = mod(bassPc - best.root, 12);
        let bsp = spellInterval(rsp, semis, IV_STEPS[semis]);
        if (spellCost(bsp, 0) > 1) bsp = spellAlone(bassPc, keyBias);
        map[bassPc] = bsp;
        c += spellCost(bsp, keyBias);
      }
      if (!pick || c < pick.c) pick = { rsp, map, c };
    }
    const bassSp = bassPc !== best.root ? pick.map[bassPc] : null;
    const name = nameOf(pick.rsp) + best.t.suffix + (bassSp ? "/" + nameOf(bassSp) : "");
    return { kind: "chord", root: pick.rsp, suffix: best.t.suffix, bass: bassSp, name, sub: "",
             pcNames: pcs.map((pc) => nameOf(pick.map[pc])), notes: spelledNotes(notes, (pc) => pick.map[pc]),
             cost: best.cost };
  }

  // Krumhansl-Kessler key finding over a pitch-class weight histogram.
  const KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
  const KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];
  const MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  const MINOR_KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];
  function pearson(xs, ys) {
    const n = xs.length;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; }
    return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : 0;
  }
  function estimateKey(hist) {
    if (hist.reduce((a, b) => a + b, 0) < 2) return null;
    let best = null;
    for (let tonic = 0; tonic < 12; tonic++) {
      const rotated = hist.map((_, i) => hist[mod(i + tonic, 12)]);
      for (const [mode, profile] of [["major", KK_MAJOR], ["minor", KK_MINOR]]) {
        const r = pearson(rotated, profile);
        if (!best || r > best.r) best = { tonic, mode, r };
      }
    }
    if (best.r < 0.5) return null;
    const relMajor = best.mode === "major" ? best.tonic : mod(best.tonic + 3, 12);
    const fifths = mod(relMajor * 7, 12);
    const bias = fifths === 0 ? 0 : fifths <= 6 ? 1 : -1;
    const name = (best.mode === "major" ? MAJOR_KEY_NAMES : MINOR_KEY_NAMES)[best.tonic] + (best.mode === "major" ? " major" : " minor");
    return { ...best, bias, name };
  }

  return { LETTERS, LETTER_PC, mod, pcOf, nameOf, accText, octaveOf, diatonicOf, spellInterval, spellingsOf,
           spellAlone, detect, estimateKey, TEMPLATES };
})();
export { Theory };
