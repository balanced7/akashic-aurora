// The practice verbs' bridge to the piano page's own chord namer (arsenal/practice.py calls it once per session).
// Zero dependencies:  node arsenal/practice_theory.mjs < request.json > answer.json
//
// It slices the THEORY block out of arsenal/web/piano.js between its "// ===== THEORY BEGIN" and
// "// ===== THEORY END" markers (the same way tests/nashville_js.test.mjs does), so an offline window is named by
// exactly the code that names chords on Daniel's screen.
//
// Request (stdin):  {"source": "<path to piano.js, optional>", "items": [{"notes": [midi, ...], "bias": -1|0|1}, ...]}
// Answer (stdout):  {"ok": true, "source": "<path>", "templates": [{suffix, tones, cost, omit5}, ...],
//                    "results": [null | {kind, name, root, suffix, bass, upper, pcNames, notes, cost}, ...]}
// A spelling is {letter: 0..6, acc: -2..2}; notes are [{midi, name, octave}]. On any failure: {"ok": false, "error"}.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

function readStdin() {
  try { return readFileSync(0, "utf8"); } catch (err) { return ""; }
}

function loadTheory(source) {
  const src = readFileSync(source, "utf8");
  const a = src.indexOf("// ===== THEORY BEGIN"), b = src.indexOf("// ===== THEORY END");
  if (a < 0 || b <= a) throw new Error(`THEORY markers not found in ${source}`);
  return new Function(src.slice(a, b) + "\nreturn Theory;")();
}

const plain = (sp) => (sp ? { letter: sp.letter, acc: sp.acc } : null);

function main() {
  let request;
  try {
    request = JSON.parse(readStdin() || "{}");
  } catch (err) {
    return { ok: false, error: `bad request: ${err.message}` };
  }
  const source = request.source || fileURLToPath(new URL("./web/piano.js", import.meta.url));
  let Theory;
  try {
    Theory = loadTheory(source);
  } catch (err) {
    return { ok: false, error: String(err && err.message || err), source };
  }
  const results = (request.items || []).map((item) => {
    const notes = (item && Array.isArray(item.notes) ? item.notes : []).filter(Number.isInteger);
    const info = Theory.detect(notes, Number.isInteger(item && item.bias) ? item.bias : 0);
    if (!info) return null;
    return {
      kind: info.kind, name: info.name, root: plain(info.root), suffix: info.suffix || "", bass: plain(info.bass),
      upper: plain(info.upper), pcNames: info.pcNames, cost: info.cost ?? null,
      notes: info.notes.map((n) => ({ midi: n.midi, name: n.name, octave: n.octave })),
    };
  });
  const templates = Theory.TEMPLATES.map((t) => ({ suffix: t.suffix, tones: t.tones, cost: t.cost, omit5: t.omit5 }));
  return { ok: true, source, templates, results };
}

process.stdout.write(JSON.stringify(main()));
