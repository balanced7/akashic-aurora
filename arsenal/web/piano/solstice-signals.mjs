import { damp } from './crystal-performance.mjs';

export const PITCH_CLASSES = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'];
export const LIGHT_ROWS = ['Attack', 'Held', 'Pedal'];

// Row-major 3 x 12 light field, independent of ornament geometry and animation clock.
// Octaves share a column. Maximum energy keeps doubled octaves from clipping to white.
export function createSolsticeSignals() {
  const cells = new Float32Array(36), levels = new Float64Array(36), target = new Float64Array(36);
  const attacks = new Float64Array(12), identities = new Map();
  return {
    cells,
    update(dt, t, state) {
      dt = Math.max(0, dt); target.fill(0);
      for (let pc = 0; pc < 12; pc++) attacks[pc] *= Math.exp(-dt / .28);
      for (const [midi, e] of state.sounding) {
        if (!Number.isInteger(midi) || midi < 21 || midi > 108) continue;
        const pc = midi % 12, velocity = Math.max(0, Math.min(1, e.vel / 127));
        const identity = e.strike ?? e.t0;
        if (identities.get(midi) !== identity) {
          identities.set(midi, identity);
          // Old notes encountered on a form change do not manufacture a new attack.
          attacks[pc] = Math.max(attacks[pc], velocity * Math.exp(-Math.max(0, t - e.t0) / .28));
        }
        const held = state.pressed.has(midi);
        if (held) target[12 + pc] = Math.max(target[12 + pc], velocity);
        else if (state.pedal) target[24 + pc] = Math.max(target[24 + pc], velocity * .88);
      }
      for (const midi of identities.keys()) if (!state.sounding.has(midi)) identities.delete(midi);
      for (let pc = 0; pc < 12; pc++) cells[pc] = attacks[pc] < .001 ? 0 : attacks[pc];
      for (let i = 12; i < 36; i++) {
        levels[i] = damp(levels[i], target[i], dt, target[i] > levels[i] ? .045 : .16);
        if (target[i] === 0 && levels[i] < .001) levels[i] = 0;
        cells[i] = levels[i];
      }
      return cells;
    },
    clear() { cells.fill(0); levels.fill(0); attacks.fill(0); target.fill(0); identities.clear(); },
  };
}
