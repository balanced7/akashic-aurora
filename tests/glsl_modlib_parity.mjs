// node tests/glsl_modlib_parity.mjs <module dir> <name>...  -> prints lib.prelude(names) exactly, for
// tests/test_glsl_modules.py to compare byte for byte with the Python composer (arsenal/shaders/modules.py).
//
// node tests/glsl_modlib_parity.mjs --plan <plan.json>  -> runs the S1 parity plan (struct, const, hook, quarantine,
// target, composed header, both index shapes, sha256, the review-fix fixture, and round 2's unknown providers, decode
// table, data-symbol and nesting cases; files go in as bytes) and prints one JSON result that the
// Python test rebuilds from modules.py and compares field by field. Its page_loads (the fetch door, which Python does
// not have) are checked against expected records instead. WHY a plan and not more argv modes: the extensions interact (a quarantined
// struct changes what a hook-bearing module resolves to), so one fixture library has to go through both twins whole.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ModuleError, createLibrary, decodeSource, libraryFromSources, loadLibrary, parseModule, sha256 } from '../arsenal/web/glsl/modlib.js';

// Load order is the module's path relative to its directory, POSIX-spelled and sorted by code unit: the same rule
// as load_library() in modules.py, so "the later module in path order" names the same file in both twins.
function walk(dir, rel = '') {
  const out = [];
  for (const name of readdirSync(join(dir, rel))) {
    const r = rel ? `${rel}/${name}` : name;
    if (statSync(join(dir, r)).isDirectory()) out.push(...walk(dir, r));
    else if (name.endsWith('.glsl')) out.push(r);
  }
  return rel ? out : out.sort().map((r) => join(dir, ...r.split('/')));
}

function attempt(fn) {
  try {
    return { ok: fn() };
  } catch (e) {
    if (!(e instanceof ModuleError)) throw e;
    return { error: e.message };
  }
}

const hexBytes = (h) => Uint8Array.from(h.match(/../g) || [], (b) => parseInt(b, 16));

async function runPlan(plan) {
  const out = { libraries: [], index_loads: [], sha256: plan.sha256.map((t) => sha256(t)),
    decode: plan.decode.map((h) => decodeSource(hexBytes(h), 'x.glsl')) };
  for (const spec of plan.libraries) {
    // The files' BYTES go in, as a page's arrayBuffer() hands them over, so decoding is the library's own; a file the
    // spec calls unreadable goes in as [path, null, problem], worded as load_library words an OSError.
    const unreadable = spec.unreadable || {};
    const sources = spec.dirs.filter((d) => existsSync(d)).flatMap((d) => walk(d)).map((p) => (
      Object.prototype.hasOwnProperty.call(unreadable, p) ? [p, null, `${p}: cannot be read (${unreadable[p]})`]
        : [p, readFileSync(p)]));
    let lib;
    try {
      lib = libraryFromSources(sources, { strict: spec.strict });
    } catch (e) {
      if (!(e instanceof ModuleError)) throw e;
      out.libraries.push({ load_error: e.message });
      continue;
    }
    const modules = {};
    for (const n of lib.names()) {
      const m = lib.modules.get(n);
      modules[n] = { provides: m.provides, calls: m.calls, uses: m.uses, declared: m.declared, hooks: m.hooks,
        version: m.version, needs: m.targetNeeds, deps: attempt(() => lib.deps(n)),
        unresolved: attempt(() => lib.unresolved(n)) };
    }
    const cases = spec.cases.map((c) => {
      const target = c.target ?? null;
      if (c.op === 'compose') return attempt(() => lib.compose(c.names, target));
      if (c.op === 'prelude') return attempt(() => lib.prelude(c.names, target));
      return attempt(() => lib.resolve(c.names));
    });
    out.libraries.push({ names: lib.names(), problems: lib.problems, unknown: lib.unknown, modules, cases });
  }
  // loadLibrary in the page fetches; here fetch reads the fixture's files so both index shapes go through the real
  // loader ({files: ["a.glsl"]} from before S1, and {files: [{path, sha256}]} from `lib index --write`). A path with
  // "unreachable" in it rejects the way a dropped connection does (a TypeError, not a response). The response is a
  // browser's: arrayBuffer() is the bytes, and text() decodes them as the Fetch standard does (UTF-8, a leading BOM
  // dropped, each malformed sequence replaced), so a page reading text() is modelled faithfully.
  let textOnly = false;   // a page load with text_only gets a shim with no arrayBuffer(), as a minimal test double has
  globalThis.fetch = async (url) => {
    const p = fileURLToPath(String(url));
    if (p.includes('unreachable')) throw new TypeError('fetch failed');
    if (!existsSync(p)) return { ok: false, status: 404 };
    const bytes = new Uint8Array(readFileSync(p));
    const text = async () => new TextDecoder().decode(bytes);
    const res = { ok: true, status: 200, text, json: async () => JSON.parse(await text()) };
    return textOnly ? res : { ...res, arrayBuffer: async () => bytes.slice().buffer };
  };
  for (const load of plan.index_loads) {
    const lib = await loadLibrary(pathToFileURL(load.index).href);
    out.index_loads.push({ names: lib.names(), problems: lib.problems, compose: lib.compose(load.names) });
  }
  // The page door alone (Python has no fetch): a lenient load quarantines what it cannot fetch, decode or parse.
  out.page_loads = [];
  for (const load of plan.page_loads || []) {
    textOnly = Boolean(load.text_only);
    try {
      const lib = await loadLibrary(pathToFileURL(load.index).href, { strict: load.strict });
      out.page_loads.push({ names: lib.names(), problems: lib.problems, unknown: lib.unknown,
        cases: load.cases.map((names) => attempt(() => lib.compose(names))) });
    } catch (e) {
      if (!(e instanceof ModuleError)) throw e;
      out.page_loads.push({ error: e.message });
    }
  }
  return out;
}

const args = process.argv.slice(2);
if (args[0] === '--plan') {
  const plan = JSON.parse(readFileSync(args[1], 'utf8'));
  process.stdout.write(JSON.stringify(await runPlan(plan)));
} else {
  const [dir, ...names] = args;
  const lib = createLibrary(walk(dir).map((p) => parseModule(readFileSync(p, 'utf8'), p)));
  process.stdout.write(lib.prelude(names));
}
