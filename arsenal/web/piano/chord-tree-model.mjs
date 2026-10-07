import { spellInterval, nameOf } from './spell.js';

export const ROOTS = [
  ['C', 0, 0], ['D♭', 1, -1], ['D', 1, 0], ['E♭', 2, -1],
  ['E', 2, 0], ['F', 3, 0], ['F♯', 3, 1], ['G', 4, 0],
  ['A♭', 5, -1], ['A', 5, 0], ['B♭', 6, -1], ['B', 6, 0],
].map(([name, letter, acc], pc) => ({ name, letter, acc, pc, hue: (38 + (pc * 7 % 12) * 30) % 360 }));

export const QUALITIES = {
  major: { name: 'Major', suffix: '', third: [4, 2, '3', 'major third'], fifth: [7, 4, '5', 'perfect fifth'], spread: 1, curl: 0, modifier: 'Open branches · major third' },
  minor: { name: 'Minor', suffix: 'm', third: [3, 2, '♭3', 'minor third'], fifth: [7, 4, '5', 'perfect fifth'], spread: .88, curl: .9, modifier: 'Inward curves · minor third' },
  sus2: { name: 'Suspended 2nd', suffix: 'sus2', third: [2, 1, '2', 'suspended second'], fifth: [7, 4, '5', 'perfect fifth'], spread: 1.04, curl: -.65, modifier: 'Forked tip · second replaces the third' },
  sus4: { name: 'Suspended 4th', suffix: 'sus4', third: [5, 3, '4', 'suspended fourth'], fifth: [7, 4, '5', 'perfect fifth'], spread: 1.08, curl: -.9, modifier: 'Forked tip · fourth replaces the third' },
  dim: { name: 'Diminished', suffix: 'dim', third: [3, 2, '♭3', 'minor third'], fifth: [6, 4, '♭5', 'diminished fifth'], spread: .73, curl: 1.3, modifier: 'Contracted crown · faceted lowered fifth' },
  aug: { name: 'Augmented', suffix: 'aug', third: [4, 2, '3', 'major third'], fifth: [8, 4, '♯5', 'augmented fifth'], spread: 1.16, curl: -.5, modifier: 'Outward crown · elongated raised fifth' },
};
export const SEVENTHS = {
  none: null, minor: [10, 6, '♭7', 'minor seventh'], major: [11, 6, '7', 'major seventh'], dim: [9, 6, '𝄫7', 'diminished seventh'],
};
export const SHADES = [.25, .39, .48, .58, .69, .79, .87];
export const pretty = name => name.replace(/bb/g, '𝄫').replace(/##/g, '𝄪').replace(/b/g, '♭').replace(/#/g, '♯');

export function normalizeChord(input = {}) {
  const root = Number.isInteger(input.root) ? ((input.root % 12) + 12) % 12 : 0;
  const quality = Object.hasOwn(QUALITIES, input.quality) ? input.quality : 'major';
  let seventh = Object.hasOwn(SEVENTHS, input.seventh) ? input.seventh : 'major';
  if (seventh === 'dim' && quality !== 'dim') seventh = 'minor';
  let sharp11 = Boolean(input.sharp11) && quality !== 'dim';
  const occupied = new Set([0, QUALITIES[quality].third[0], QUALITIES[quality].fifth[0]]);
  if (SEVENTHS[seventh]) occupied.add(SEVENTHS[seventh][0]);
  const extensions = [9, 11, 13].filter(degree => {
    if (!(input.extensions ?? [9]).includes(degree)) return false;
    const pitch = degree === 9 ? 2 : degree === 11 ? sharp11 ? 6 : 5 : 9;
    if (occupied.has(pitch)) return false;
    occupied.add(pitch); return true;
  });
  if (!extensions.includes(11)) sharp11 = false;
  return { root, quality, seventh, extensions, sharp11 };
}

function symbol(s) {
  const r = ROOTS[s.root].name, q = QUALITIES[s.quality];
  const ext = s.extensions.map(x => x === 11 && s.sharp11 ? '♯11' : String(x));
  const added = xs => xs.length ? `(add${xs.join(',add')})` : '';
  if (s.seventh === 'none') return r + q.suffix + added(ext);
  if (s.quality === 'dim') {
    const suffix = s.seventh === 'dim' ? 'dim7' : s.seventh === 'minor' ? 'm7(♭5)' : 'm(maj7,♭5)';
    return r + suffix + added(ext);
  }
  let level = 7, used = 0;
  if (ext[0] === '9') { level = 9; used = 1; }
  if (ext[1] === '11' && level === 9) { level = 11; used = 2; }
  if (ext[2] === '13' && level === 11) { level = 13; used = 3; }
  const numeral = s.seventh === 'major' ? `maj${level}` : String(level);
  const base = s.quality === 'minor' ? (s.seventh === 'major' ? `${r}m(${numeral})` : `${r}m${level}`) : r + numeral;
  const suffix = s.quality === 'aug' ? '(♯5)' : s.quality.startsWith('sus') ? s.quality : '';
  return base + suffix + added(ext.slice(used));
}

export function buildChord(input) {
  const state = normalizeChord(input), root = ROOTS[state.root], family = QUALITIES[state.quality];
  const specs = [
    [0, 0, '1', 'root'], family.third, family.fifth, SEVENTHS[state.seventh],
    state.extensions.includes(9) ? [14, 1, '9', 'ninth'] : null,
    state.extensions.includes(11) ? [state.sharp11 ? 18 : 17, 3, state.sharp11 ? '♯11' : '11', state.sharp11 ? 'raised eleventh' : 'eleventh'] : null,
    state.extensions.includes(13) ? [21, 5, '13', 'thirteenth'] : null,
  ];
  const tones = specs.map((spec, slot) => {
    if (!spec) return null;
    const [semitones, steps, degree, role] = spec;
    return { slot, semitones, degree, role, pc: (state.root + semitones) % 12,
      note: pretty(nameOf(spellInterval(root, semitones, steps))), shade: SHADES[slot], hue: root.hue };
  });
  return { state, root, family, tones, name: symbol(state),
    notes: tones.filter(Boolean).map(t => t.note),
    modifier: state.sharp11 ? `${family.modifier} · spiral on ♯11` : family.modifier };
}
