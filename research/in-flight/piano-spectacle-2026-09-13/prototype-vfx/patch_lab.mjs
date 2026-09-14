// Patches the LAB copy arsenal/web/piano-lab-vfx.js (never piano.js) with the spectacle prototype.
import { readFileSync, writeFileSync } from "node:fs";
const FILE = "E:/AI-Setup/arsenal/web/piano-lab-vfx.js";
const MODULE = "C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/fx_module.js";
let src = readFileSync(FILE, "utf8").replace(/\r\n/g, "\n");
const once = (from, to) => {
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error(`expected exactly one match (${n}) for:\n${from}`);
  src = src.replace(from, to);
};

once(`uPedalHist: { value: pedalHist }, uDensity: { value: 1 } };`,
     `uPedalHist: { value: pedalHist }, uDensity: { value: 1 },
                        // LAB spectacle: the shimmer band (fxTrigger sets these)
                        uShimT0: { value: -1e6 }, uShimX0: { value: 0 }, uShimX1: { value: 0 }, uShimGain: { value: 0 }, uShimGold: { value: 0 } };`);
once(`    attribute vec3 aColor;
    varying vec2 vP;`, `    attribute vec3 aColor;
    varying vec2 vP;
    varying float vX;`);
once(`vW = aW; vColor = aColor;`, `vW = aW; vColor = aColor; vX = aX;`);
once(`    uniform float uTop, uSpeed, uNow, uBaseY, uLife, uDensity;`,
     `    uniform float uTop, uSpeed, uNow, uBaseY, uLife, uDensity;
    uniform float uShimT0, uShimX0, uShimX1, uShimGain, uShimGold;
    varying float vX;`);
once(`      col += vColor * vFoot * exp(-fd * 1.9) * 1.1;
      gl_FragColor = vec4(col * fade, 1.0);`,
     `      col += vColor * vFoot * exp(-fd * 1.9) * 1.1;
      // LAB spectacle: a shimmer band that rides up the chord's columns 3.2x faster than they rise; gold adds a second
      // band and a dispersion fringe (red leading, blue trailing)
      float sAge = uNow - uShimT0;
      if (uShimGain > 0.0 && sAge > 0.0 && sAge < 2.6) {
        float inX = smoothstep(uShimX0 - 0.8, uShimX0, vX) * (1.0 - smoothstep(uShimX1, uShimX1 + 0.8, vX));
        float bw = 0.8 + 0.5 * sAge;
        float lit = clamp(energy * 1.6, 0.0, 1.0) * (1.0 - smoothstep(1.4, 2.6, sAge)) * inX * uShimGain;
        vec3 shim = vec3(0.0);
        for (int b = 0; b < 2; b++) {
          float dy = vP.y - (uBaseY + (sAge - 0.45 * float(b)) * uSpeed * 3.2);
          float g = exp(-dy * dy / (bw * bw)) * (b == 0 ? 1.0 : 0.55 * uShimGold);
          float s2 = 0.3 * bw * bw;
          vec3 fringe = vec3(exp(-(dy - 0.5 * bw) * (dy - 0.5 * bw) / s2), exp(-dy * dy / s2), exp(-(dy + 0.5 * bw) * (dy + 0.5 * bw) / s2));
          shim += mix(mix(vColor, vec3(1.0), 0.15) * g, vec3(1.0, 0.62, 0.22) * g * 0.8 + fringe * g * 0.3, uShimGold);
        }
        col += shim * (core * (0.45 + 0.8 * axis * axis) + halo * 0.3) * lit;
      }
      gl_FragColor = vec4(col * fade, 1.0);`);
once(`  const dist = cam.span / 2 / tanH + 7;
  const elev = THREE.MathUtils.degToRad(framing.follow ? 22 : 17) + Math.sin(t * 0.13) * 0.012;
  const yaw = Math.sin(t * 0.071) * (framing.follow ? 0.06 : 0.035);`,
     `  const dist = (cam.span / 2 / tanH + 7) * (1 - fxCam.push);  // LAB spectacle: a push-in on Epic and Legendary
  const elev = THREE.MathUtils.degToRad(framing.follow ? 22 : 17) + Math.sin(t * 0.13) * 0.012 + fxCam.elev;
  const yaw = Math.sin(t * 0.071) * (framing.follow ? 0.06 : 0.035) + fxCam.yaw;`);
once(`    overlayCam.updateProjectionMatrix();
    this.invalidate();
  },`, `    overlayCam.updateProjectionMatrix();
    this.invalidate();
    fxBuildOverlay();
  },`);
once(`const densityTarget = Math.min(1, LIGHT_BUDGET / Math.max(trails.scan(t).oldLoad, 1e-3));`,
     `const densityTarget = Math.min(1, LIGHT_BUDGET / Math.max(trails.scan(t).oldLoad, 1e-3)) * fxState.dim;  // LAB: house lights`);
once(`  overlay.update(info, t, dt);
  composer.render(dt);`, `  overlay.update(info, t, dt);
  fxUpdate(dt, t);
  composer.render(dt);`);
once(`  get lastUpload() { return lastUpload; },
};`, `  get lastUpload() { return lastUpload; },
  // LAB spectacle hooks
  clock: () => clock(),
  fx(tier, notes = null) { return fxTrigger(tier, clock(), notes, "hook"); },
  fxLog() { return fxState.log; },
  // mean ms per frame over n synchronous frames, each forced to finish on the GPU with a 1-pixel read
  bench(n = 120) {
    const gl = renderer.getContext(), px = new Uint8Array(4);
    renderFrame(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const t0 = performance.now();
    for (let i = 0; i < n; i++) { renderFrame(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); }
    return +((performance.now() - t0) / n).toFixed(3);
  },
};`);
once(`  stats.noteOns++;`, `  stats.noteOns++;
  fxNoteOn(vel, t);  // LAB spectacle: velocity history for the accent score`);
once(`// ----------------------------------------------------------- notes engine --`,
     readFileSync(MODULE, "utf8").replace(/\r\n/g, "\n") + `// ----------------------------------------------------------- notes engine --`);
writeFileSync(FILE, src);
console.log("patched", FILE, src.split("\n").length, "lines");
