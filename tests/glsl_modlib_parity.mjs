// node tests/glsl_modlib_parity.mjs <module dir> <name>...  -> prints lib.prelude(names) exactly, for
// tests/test_glsl_modules.py to compare byte for byte with the Python composer (arsenal/shaders/modules.py).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { createLibrary, parseModule } from '../arsenal/web/glsl/modlib.js';

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith('.glsl')) out.push(p);
  }
  return out;
}

const [dir, ...names] = process.argv.slice(2);
const lib = createLibrary(walk(dir).map((p) => parseModule(readFileSync(p, 'utf8'), p)));
process.stdout.write(lib.prelude(names));
