// arsenal/web/shaderlab/toy-runtime.js -- the house's own runtime for the public Shadertoy interface.
//
// WHY THIS EXISTS. The shader school studies other people's shaders (state/arsenal/shaders/corpus/, saved whole as
// Shadertoy serves them). Reading the code is half the study; the other half is SEEING it, frame by frame, on this
// machine, without shadertoy.com and without a GPU (this host has an AMD display-driver crash history, so every pixel
// here is rendered by headless Chrome on SwiftShader, the CPU). That needs a runtime that honours the interface those
// shaders were written against: the uniform names, the pass graph, the channel inputs and their samplers.
//
// THE INTERFACE IS PUBLIC; THIS CODE IS OURS. Uniform names (iTime, iChannel0...), pass types (image, buffer, common,
// cubemap, sound), the output ids that name Buffer A-D in a saved shader, and the semantics a shader relies on (a
// buffer that reads itself sees the previous frame) are an interface. Everything below is written from that interface,
// not copied from shadertoy.com's site JavaScript and not from any corpus shader. Tests use synthetic shaders.
//
// WHAT IT DOES, in the order a frame needs it:
//   * Common is prepended to every pass; each pass gets our header (#version 300 es on line 1, precision highp, the
//     uniforms) and a footer main() that calls mainImage / mainCubemap / mainSound. Error logs are mapped back to the
//     pass's own line numbers ("ERROR: Buffer A:12: ..."), so a compile error points at the line a reader can open.
//   * Passes run in Shadertoy's order: the buffers in the order the shader saved them (not by letter: a save whose
//     buffers read A, D, B, C runs D before B), then Cube A, then Image. A buffer renders into a float target
//     (RGBA32F when EXT_color_buffer_float and OES_texture_float_linear allow, else RGBA16F, else RGBA8 with a
//     warning) and ping-pongs between two textures, so a read of itself, or of a pass later in the order, sees the
//     previous frame, and a read of an earlier pass sees this frame. passOrder() states that for every read.
//     A resize keeps each buffer's pixels where both sizes overlap, as Shadertoy does (resize()).
//   * Inputs by kind: buffer, texture (sampler filter/wrap/vflip/srgb honoured through WebGL2 sampler objects),
//     cubemap (six faces: <name>.<ext>, <name>_1..5.<ext>), volume (.bin 3D texture), keyboard (256x3), and audio
//     (music, musicstream, mic: the 512x2 texture, row 0 spectrum, row 1 waveform, fed by setAudio -- this is how the
//     piano drives audio-reactive shaders). Media that cannot be had become a deterministic procedural stand-in, and
//     stats().substituted names every one, so a render never pretends.
//   * A feedback shader's still is not a function of t: advance() steps a fixed dt from a reset, so the same t gives
//     the same pixels (the shader-craft floor: "cleared history plus a fixed settle, never a seek"). A shader with no
//     history (no read of an earlier frame) is a function of t, and jump() draws only the frame that walk ends on.
//   * SwiftShader is not the GPU the corpus was written on. Where a built-in's answer differs (tanh overflow, min/max
//     with a NaN operand), the header routes the call to a replacement that gives the GPU answer: PARITY_SHIMS.
//
// WHAT IT IS NOT: no sound playback (the Sound pass compiles, never plays), no video or webcam decode (stand-ins), no
// UI. render.html is the headless still-maker built on it; the lab pages come later.
//
// Everything above createToy() is pure (no WebGL, no DOM) and exported for the node tests in
// tests/shaderlab_runtime.test.mjs. Raw WebGL2, no libraries, no build step.

export const API = 'arsenal.shaderlab-runtime/v1';

// ---------------------------------------------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------------------------------------------

// The WebGL2 enums this file uses, by their spec values, so the pure helpers can name them without a context and the
// GL code reads the same table the tests check.
export const GL = Object.freeze({
  TEXTURE_2D: 0x0DE1, TEXTURE_3D: 0x806F, TEXTURE_CUBE_MAP: 0x8513, TEXTURE_CUBE_MAP_POSITIVE_X: 0x8515,
  TEXTURE0: 0x84C0,
  NEAREST: 0x2600, LINEAR: 0x2601, LINEAR_MIPMAP_LINEAR: 0x2703,
  REPEAT: 0x2901, CLAMP_TO_EDGE: 0x812F, MIRRORED_REPEAT: 0x8370,
  TEXTURE_MAG_FILTER: 0x2800, TEXTURE_MIN_FILTER: 0x2801,
  TEXTURE_WRAP_S: 0x2802, TEXTURE_WRAP_T: 0x2803, TEXTURE_WRAP_R: 0x8072,
  RGBA: 0x1908, RGB: 0x1907, RG: 0x8227, RED: 0x1903,
  RGBA8: 0x8058, RGB8: 0x8051, RG8: 0x822B, R8: 0x8229, SRGB8_ALPHA8: 0x8C43,
  RGBA16F: 0x881A, RGBA32F: 0x8814, RGB32F: 0x8815, RG32F: 0x8230, R32F: 0x822E,
  UNSIGNED_BYTE: 0x1401, FLOAT: 0x1406, HALF_FLOAT: 0x140B,
  UNPACK_ALIGNMENT: 0x0CF5, UNPACK_FLIP_Y_WEBGL: 0x9240, UNPACK_PREMULTIPLY_ALPHA_WEBGL: 0x9241,
  UNPACK_COLORSPACE_CONVERSION_WEBGL: 0x9243, NONE: 0,
  FRAMEBUFFER: 0x8D40, COLOR_ATTACHMENT0: 0x8CE0, FRAMEBUFFER_COMPLETE: 0x8CD5, COLOR_BUFFER_BIT: 0x4000,
  READ_FRAMEBUFFER: 0x8CA8, DRAW_FRAMEBUFFER: 0x8CA9,
  VERTEX_SHADER: 0x8B31, FRAGMENT_SHADER: 0x8B30, COMPILE_STATUS: 0x8B81, LINK_STATUS: 0x8B82, TRIANGLES: 0x0004,
  VENDOR: 0x1F00, RENDERER: 0x1F01, VERSION: 0x1F02, SHADING_LANGUAGE_VERSION: 0x8B8C,
  UNMASKED_VENDOR_WEBGL: 0x9245, UNMASKED_RENDERER_WEBGL: 0x9246,
  MAX_TEXTURE_SIZE: 0x0D33, NO_ERROR: 0,
  BLEND: 0x0BE2, DEPTH_TEST: 0x0B71, SCISSOR_TEST: 0x0C11, CULL_FACE: 0x0B44, DITHER: 0x0BD0,
});

// The output ids a saved shader uses to name its passes. They are how a buffer input says which buffer it reads
// (inputs[].id === the producing pass's outputs[0].id); the names ("Buffer A", "Buf A") vary, the ids do not.
export const PASS_IDS = Object.freeze({
  '4dXGR8': 'A', 'XsXGR8': 'B', '4sXGR8': 'C', 'XdfGR8': 'D',
  '4dX3Rr': 'cube', '4dfGRr': 'image', 'XsfGRr': 'sound',
});
// Older saves name a buffer input only by its preview path: /media/previz/buffer00.png is Buffer A, ...03 is D.
const PREVIZ_BUFFER = /previz\/buffer0([0-3])\.png/;
const PREVIZ_CUBE = /previz\/cubemap/;
const BUFFER_KEYS = ['A', 'B', 'C', 'D'];

// Shadertoy's execution order, by group: every buffer, then Cube A, then Image. Within the buffers the order is the
// saved renderpass order -- Shadertoy's client walks its pass list (built in saved order) once per group -- not the
// letter, and not the graph: a save that lists Buffer D before Buffer B was written knowing B sees D's frame from
// THIS frame, and one whose Buffer A reads Buffer D (saved later) knowing A sees D's PREVIOUS frame.
export const EXEC_GROUP = Object.freeze({ A: 0, B: 0, C: 0, D: 0, cube: 1, image: 2 });

export const DEFAULT_PASS_NAMES = Object.freeze({
  A: 'Buffer A', B: 'Buffer B', C: 'Buffer C', D: 'Buffer D', cube: 'Cube A', image: 'Image', sound: 'Sound',
  common: 'Common',
});

export const AUDIO = Object.freeze({ width: 512, height: 2, rows: { spectrum: 0, wave: 1 }, silenceWave: 128 });
export const KEYBOARD = Object.freeze({ width: 256, height: 3, rows: { down: 0, pressed: 1, toggle: 2 } });
export const SAMPLE_RATE = 44100;
export const DEFAULT_FPS = 60;
export const DEFAULT_CUBE_SIZE = 1024;     // Shadertoy's Cube A face size; a cube pass may index texels by fragCoord
export const STANDIN_SIZE = 256;           // a 2D stand-in: the size of the common noise textures
export const STANDIN_CUBE_SIZE = 128;      // per face
export const STANDIN_VOLUME_SIZE = 32;     // the common noise volumes are 32^3
// The house's noise textures pair their channels: G(x, y) = R(x - 37, y - 17), and A from B the same way, so one
// fetch of .yx returns two z-slices of a 3D lattice. Stand-ins keep that pairing, so noise that relies on it still
// reads as noise rather than as two unrelated layers.
export const NOISE_CHANNEL_OFFSET = Object.freeze([37, 17]);
export const VOLUME_HEADER_BYTES = 20;
export const GRID_EPS = 1e-6;              // how close t * fps must be to an integer to count as on the frame grid
const TIME_EPS = 1e-9;
const SCRATCH_UNIT = 7;                    // uploads and mip generation bind here, never on the channel units 0-3
const GL_ERROR_CHECK_FRAMES = 3;           // getError is a sync point; check only the first frames, where setup fails

export const CONTEXT_ATTRIBUTES = Object.freeze({
  alpha: false, antialias: false, depth: false, stencil: false, premultipliedAlpha: false,
  preserveDrawingBuffer: true,   // render.html reads the canvas back after the frame
  powerPreference: 'low-power',
  failIfMajorPerformanceCaveat: false,   // SwiftShader IS a major performance caveat, and it is the point
});

const DEFAULT_OPTIONS = Object.freeze({
  mediaUrl: null, audio: null, pixelRatio: 1, cubeSize: DEFAULT_CUBE_SIZE, hwPerformance: 1,
  mediaTimeoutMs: 15000, fps: DEFAULT_FPS, dateBase: null, bufferFormat: null, loseContextOnDestroy: true,
  parity: true,   // the GPU-parity shims (PARITY_SHIMS); false compiles every pass exactly as written
});

// ---------------------------------------------------------------------------------------------------------------
// Pure helpers: inputs, samplers, passes
// ---------------------------------------------------------------------------------------------------------------

function truthy(v) {
  return v === true || v === 1 || (typeof v === 'string' && /^(true|1|yes)$/i.test(v.trim()));
}

/** What an input is, as the runtime treats it: buffer, cubebuffer (Cube A), texture, cubemap, volume, keyboard,
 *  audio (music, musicstream, mic), video, webcam, or unknown. */
export function inputKind(input) {
  const t = String((input && (input.type || input.ctype)) || '').toLowerCase();
  switch (t) {
    case 'buffer': return 'buffer';
    case 'texture': return 'texture';
    case 'cubemap': {
      const src = String(input.filepath || input.src || '');
      return PASS_IDS[input.id] === 'cube' || PREVIZ_CUBE.test(src) ? 'cubebuffer' : 'cubemap';
    }
    case 'volume': return 'volume';
    case 'keyboard': return 'keyboard';
    case 'music': case 'musicstream': case 'mic': return 'audio';
    case 'video': return 'video';
    case 'webcam': return 'webcam';
    default: return 'unknown';
  }
}

/** The GLSL sampler type a channel is declared as. */
export function samplerTypeFor(input) {
  const kind = inputKind(input);
  if (kind === 'cubemap' || kind === 'cubebuffer') return 'samplerCube';
  if (kind === 'volume') return 'sampler3D';
  return 'sampler2D';
}

/** The pass a buffer/cubebuffer input reads ('A'..'D' or 'cube'), or null when it names none we can find. */
export function bufferKeyForInput(input) {
  const kind = inputKind(input);
  if (kind === 'cubebuffer') return 'cube';
  if (kind !== 'buffer') return null;
  const byId = PASS_IDS[input.id];
  if (BUFFER_KEYS.includes(byId)) return byId;
  const m = PREVIZ_BUFFER.exec(String(input.filepath || input.src || ''));
  return m ? BUFFER_KEYS[Number(m[1])] : null;
}

/** A pass's role: 'A'..'D', 'cube', 'image', 'common', 'sound', or null for a pass we cannot place. */
export function passKey(pass) {
  const type = String((pass && pass.type) || '').toLowerCase();
  if (type === 'image' || type === 'common' || type === 'sound') return type;
  if (type === 'cubemap') return 'cube';
  if (type !== 'buffer') return null;
  const out = (pass.outputs || [])[0];
  const byId = out && PASS_IDS[out.id];
  if (BUFFER_KEYS.includes(byId)) return byId;
  const m = /(?:^|\s)(?:buffer|buf)\s*([a-d])\s*$/i.exec(String(pass.name || ''));
  return m ? m[1].toUpperCase() : null;
}

export function passDisplayName(pass) {
  const name = String((pass && pass.name) || '').trim();
  if (name) return name;
  const key = passKey(pass);
  return (key && DEFAULT_PASS_NAMES[key]) || String((pass && pass.type) || 'pass');
}

/**
 * The draw passes in execution order (Common and Sound are not drawn): the buffers in saved order, then Cube A, then
 * Image (EXEC_GROUP). Each entry:
 *   {index, key, name, type, reads: [{channel, key, sees}]}
 * where sees is 'this-frame' (the producer ran earlier in this frame), 'previous-frame' (the producer is this pass
 * or a later one, so the read gets last frame's result through the ping-pong), or 'missing' (no such pass).
 * A second pass claiming a role already taken is kept out of the order and marked in .duplicates.
 */
export function passOrder(renderpass) {
  const entries = [];
  const duplicates = [];
  const seen = new Set();
  (renderpass || []).forEach((pass, index) => {
    const key = passKey(pass);
    if (!key || key === 'common' || key === 'sound') return;
    if (seen.has(key)) { duplicates.push({ index, key, name: passDisplayName(pass) }); return; }
    seen.add(key);
    entries.push({ index, key, name: passDisplayName(pass), type: pass.type, inputs: pass.inputs || [] });
  });
  // A stable sort by group: entries arrive in saved order, so the buffers keep it among themselves.
  entries.sort((a, b) => EXEC_GROUP[a.key] - EXEC_GROUP[b.key]);
  const rank = new Map(entries.map((e, i) => [e.key, i]));
  for (const e of entries) {
    e.reads = [];
    for (const input of e.inputs) {
      const kind = inputKind(input);
      if (kind !== 'buffer' && kind !== 'cubebuffer') continue;
      const src = bufferKeyForInput(input);
      let sees = 'missing';
      if (src && rank.has(src)) sees = rank.get(src) < rank.get(e.key) ? 'this-frame' : 'previous-frame';
      e.reads.push({ channel: Number(input.channel), key: src, sees });
    }
    delete e.inputs;
  }
  Object.defineProperty(entries, 'duplicates', { value: duplicates, enumerable: false });
  return entries;
}

const FILTERS = {
  nearest: { min: GL.NEAREST, mag: GL.NEAREST, mipmaps: false },
  linear: { min: GL.LINEAR, mag: GL.LINEAR, mipmaps: false },
  mipmap: { min: GL.LINEAR_MIPMAP_LINEAR, mag: GL.LINEAR, mipmaps: true },
};
const WRAPS = { clamp: GL.CLAMP_TO_EDGE, repeat: GL.REPEAT, mirror: GL.MIRRORED_REPEAT };
// What an input samples with when its saved sampler says nothing (the common case in the corpus per kind).
const SAMPLER_DEFAULTS = {
  buffer: { filter: 'linear', wrap: 'clamp' }, cubebuffer: { filter: 'linear', wrap: 'clamp' },
  texture: { filter: 'mipmap', wrap: 'repeat' }, cubemap: { filter: 'mipmap', wrap: 'clamp' },
  volume: { filter: 'mipmap', wrap: 'repeat' }, video: { filter: 'linear', wrap: 'clamp' },
  webcam: { filter: 'linear', wrap: 'clamp' }, keyboard: { filter: 'nearest', wrap: 'clamp' },
  audio: { filter: 'linear', wrap: 'clamp' }, unknown: { filter: 'linear', wrap: 'clamp' },
};
// Only pixels we upload from an image can be flipped or decoded from sRGB; a rendered buffer, a data texture
// (keyboard, audio) and a volume are used as they are.
const FLIPPABLE = new Set(['texture', 'cubemap', 'video', 'webcam']);
const SRGB_CAPABLE = new Set(['texture', 'cubemap']);

/**
 * An input's sampler, resolved: the saved words (filter nearest|linear|mipmap, wrap clamp|repeat|mirror, vflip,
 * srgb -- saved as the strings "true"/"false") and the GL state they mean. mipmaps says the texture needs a mip chain;
 * flipY is the upload flip (images only); internalFormat is SRGB8_ALPHA8 for an sRGB image, RGBA8 otherwise.
 */
export function samplerFor(input) {
  const kind = inputKind(input);
  const saved = (input && input.sampler) || {};
  const def = SAMPLER_DEFAULTS[kind] || SAMPLER_DEFAULTS.unknown;
  const filter = FILTERS[saved.filter] ? saved.filter : def.filter;
  const wrap = WRAPS[saved.wrap] !== undefined ? saved.wrap : def.wrap;
  const vflip = truthy(saved.vflip);
  const srgb = truthy(saved.srgb);
  const f = FILTERS[filter];
  const w = WRAPS[wrap];
  const flipY = FLIPPABLE.has(kind) && vflip;
  const isSrgb = SRGB_CAPABLE.has(kind) && srgb;
  return {
    kind, filter, wrap, vflip, srgb,
    minFilter: f.min, magFilter: f.mag, wrapS: w, wrapT: w, wrapR: w,
    mipmaps: f.mipmaps, flipY, internalFormat: isSrgb ? GL.SRGB8_ALPHA8 : GL.RGBA8,
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Pure helpers: source assembly and error mapping
// ---------------------------------------------------------------------------------------------------------------

function countLines(text) {
  let n = 0;
  for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 10) n++;
  return n;
}

/**
 * Source text the GLSL ES compiler will take: CRLF to LF, no BOM, and every character outside printable ASCII
 * (a "(c)" sign, an accented name, a non-breaking space in a comment) replaced by a space so no line moves.
 * Ends with exactly the newlines it had, plus one if it had none.
 */
export function sanitizeGlsl(code) {
  let s = String(code || '').replace(/^\ufeff/, '').replace(/\r\n?/g, '\n');
  s = s.replace(/[^\n\t\x20-\x7E]/g, ' ');
  if (s && !s.endsWith('\n')) s += '\n';
  return s;
}

// GPU-PARITY SHIMS. Built-ins whose SwiftShader result differs from the GPUs the corpus was written on (D3D11 through
// ANGLE, NVIDIA, AMD, Apple), each replaced by a version that gives the GPU answer. The header defines the
// replacement, then a macro routes the shader's calls to it (the macro comes after the bodies, so a replacement's own
// call still reaches the real built-in). GLSL ES 3.00 forbids redefining or overloading a built-in, so no shader that
// compiles on Shadertoy defines these names itself. Measured with synthetic probes on this host's SwiftShader
// (Chrome 155, 2026-10-13):
//   tanh: SwiftShader computes (e^x - e^-x) / (e^x + e^-x); once |x| passes about 88 both exponentials overflow and
//     the quotient is inf / inf = NaN, which stores as black. GPUs return +-1. Probe: tanh(1001.0) read NaN,
//     tanh(50.0) read 1.0. Clamping to +-TANH_CLAMP changes no float result (tanh(15) already rounds to 1.0f).
//   min, max: SwiftShader returned the SECOND operand whenever either was NaN (the x86 minps rule), so min(0.5, NaN)
//     read NaN while min(NaN, 0.5) read 0.5. GPUs return the operand that is not NaN (IEEE minNum, the D3D11 rule).
//     Raymarchers lean on that: an SDF term that is 0/0 on the ray's first step (sin(p)/p at p = 0) vanishes inside
//     min() on a GPU and poisons the whole march here. One corpus tunnel drew solid black for exactly this reason.
//     The probe saw one operand order on one build; SPIR-V leaves a NaN operand's result undefined, so an optimizer
//     may swap the operands. The shim therefore tests BOTH operands and does not rely on which one the built-in keeps.
// The macro has a cost a GPU never charges: a call to a user function is not a constant expression, so a shader
// that uses min/max/tanh in a const initializer, a global initializer or an array size does not compile with the
// shims. compile() then retries with fewer shims (PARITY_LEVELS) and names the level each pass compiled at.
export const TANH_CLAMP = 15;
const FLOAT_TYPES = ['float', 'vec2', 'vec3', 'vec4'];
const INT_FAMILIES = [['int', 'ivec2', 'ivec3', 'ivec4'], ['uint', 'uvec2', 'uvec3', 'uvec4']];

function minMaxShim(fn) {
  // Two selects per call, no branch: a NaN b gives a, then a NaN a gives b (so both NaN gives NaN), whatever the
  // built-in itself returns for a NaN operand. tests/shaderlab_runtime.test.mjs evaluates the float body under both
  // operand rules.
  const out = [];
  for (const t of FLOAT_TYPES) {
    out.push(`${t} shaderlab_${fn}(${t} a, ${t} b) { return mix(mix(${fn}(a, b), a, isnan(b)), b, isnan(a)); }`);
    if (t !== 'float') {
      out.push(`${t} shaderlab_${fn}(${t} a, float b) { return mix(mix(${fn}(a, b), a, b${t}(isnan(b))), ${t}(b), isnan(a)); }`);
    }
  }
  // The integer overloads only pass through: the macro renames every call, so every built-in signature needs a twin.
  for (const [s, ...vecs] of INT_FAMILIES) {
    out.push(`${s} shaderlab_${fn}(${s} a, ${s} b) { return ${fn}(a, b); }`);
    for (const t of vecs) {
      out.push(`${t} shaderlab_${fn}(${t} a, ${t} b) { return ${fn}(a, b); }`, `${t} shaderlab_${fn}(${t} a, ${s} b) { return ${fn}(a, b); }`);
    }
  }
  out.push(`#define ${fn} shaderlab_${fn}`);
  return out;
}

export const PARITY_SHIMS = Object.freeze({
  tanh: Object.freeze([
    ...FLOAT_TYPES.map((t) => `${t} shaderlab_tanh(${t} x) { return tanh(clamp(x, -${TANH_CLAMP}.0, ${TANH_CLAMP}.0)); }`),
    '#define tanh shaderlab_tanh',
  ]),
  minmax: Object.freeze([...minMaxShim('min'), ...minMaxShim('max')]),
});
// The shim sets compile() tries, in order, for each pass: all of them, then without min/max (the shim a const
// initializer most often trips), then without tanh (a tanh in a const initializer keeps the min/max fix), then none
// (the shader exactly as written).
export const PARITY_LEVELS = Object.freeze([
  Object.freeze({ name: 'full', shims: Object.freeze(['tanh', 'minmax']) }),
  Object.freeze({ name: 'tanh-only', shims: Object.freeze(['tanh']) }),
  Object.freeze({ name: 'minmax-only', shims: Object.freeze(['minmax']) }),
  Object.freeze({ name: 'none', shims: Object.freeze([]) }),
]);

/** The input a channel holds: the LAST input saved on it, the rule the header, the binding and iChannelTime share. */
export function channelInput(inputs, channel) {
  const list = inputs || [];
  for (let i = list.length - 1; i >= 0; i--) if (Number(list[i] && list[i].channel) === channel) return list[i];
  return null;
}

// The input types whose media has a playback clock. Shadertoy's client sets iChannelTime[c] to that media's
// currentTime (a music, musicstream or video channel) and leaves 0 for every other channel: buffers, textures,
// cubemaps, volumes, the keyboard, the webcam, a live microphone, and an empty channel. Here media are not played
// (silence and stand-ins), so a clocked channel reads as media playing from the start alongside iTime.
const PLAYBACK_CLOCK = new Set(['music', 'musicstream', 'video']);

/** iChannelTime for a pass: [t, 0, ...] per channel, t on a channel whose input has a playback clock. */
export function channelTimes(inputs, time) {
  const out = [0, 0, 0, 0];
  for (let c = 0; c < 4; c++) {
    const input = channelInput(inputs, c);
    const type = String((input && (input.type || input.ctype)) || '').toLowerCase();
    if (PLAYBACK_CLOCK.has(type)) out[c] = Number(time) || 0;
  }
  return out;
}

/**
 * Our header for one pass. Line 1 is #version 300 es (it must be); then precision, HW_PERFORMANCE, the uniforms of
 * the interface, and iChannel0..3 declared by what each channel holds (sampler2D / samplerCube / sampler3D; an empty
 * channel is a sampler2D); then the GPU-parity shims named in opts.shims (default: all of them). A Sound pass gets the
 * sound set instead (no iResolution, iTime, iTimeDelta, iFrameRate, iFrame, iMouse; plus iBlockOffset and the block
 * size its footer uses); a Cube A pass gets the face basis its footer uses.
 */
export function buildHeader(passType, inputs = [], opts = {}) {
  const type = String(passType || 'image').toLowerCase();
  const hw = opts.hwPerformance === 0 || opts.hwPerformance === '0' ? 0 : 1;
  const lines = [
    '#version 300 es',
    `// shaderlab header (${type} pass): our implementation of the Shadertoy interface`,
    'precision highp float;',
    'precision highp int;',
    'precision highp sampler2D;',
    'precision highp samplerCube;',
    'precision highp sampler3D;',
    `#define HW_PERFORMANCE ${hw}`,
    // A Sound pass sees fewer uniforms than a picture pass: no iResolution, iTime, iTimeDelta, iFrameRate, iFrame or
    // iMouse (a corpus sound pass declares its own iResolution and iMouse globals, which only compiles without ours).
    ...(type === 'sound' ? [] : ['uniform vec3 iResolution;', 'uniform float iTime;', 'uniform float iTimeDelta;',
      'uniform float iFrameRate;', 'uniform int iFrame;']),
    'uniform float iChannelTime[4];',
    'uniform vec3 iChannelResolution[4];',
    ...(type === 'sound' ? [] : ['uniform vec4 iMouse;']),
    'uniform vec4 iDate;',
    'uniform float iSampleRate;',
  ];
  for (let c = 0; c < 4; c++) {
    // Two inputs on one channel: the last one, the one createToy binds ("the last one wins").
    const input = channelInput(inputs, c);
    lines.push(`uniform ${input ? samplerTypeFor(input) : 'sampler2D'} iChannel${c};`);
  }
  const shims = Array.isArray(opts.shims) ? opts.shims : PARITY_LEVELS[0].shims;
  for (const name of shims) if (PARITY_SHIMS[name]) lines.push(...PARITY_SHIMS[name]);
  if (type === 'sound') lines.push('uniform float iBlockOffset;', 'uniform vec2 shaderlab_blockSize;');
  if (type === 'cubemap') {
    lines.push('uniform vec3 shaderlab_faceCenter;', 'uniform vec3 shaderlab_faceRight;', 'uniform vec3 shaderlab_faceUp;');
  }
  return lines.join('\n') + '\n';
}

/** The footer main() for a pass type, given the pass's own code (the Sound signature is read from it). */
export function buildFooter(passType, code = '') {
  const type = String(passType || 'image').toLowerCase();
  if (type === 'sound') {
    // mainSound(int samp, float time) in current saves, mainSound(float time) in older ones.
    const call = /\bmainSound\s*\(\s*(?:in\s+)?int\b/.test(code)
      ? 'mainSound(shaderlab_sample, shaderlab_t)' : 'mainSound(shaderlab_t)';
    return [
      'out vec4 shaderlab_out;',
      'void main() {',
      '  int shaderlab_sample = int(iBlockOffset * iSampleRate) + int(gl_FragCoord.y) * int(shaderlab_blockSize.x) + int(gl_FragCoord.x);',
      '  float shaderlab_t = float(shaderlab_sample) / iSampleRate;',
      `  vec2 shaderlab_v = ${call};`,
      '  shaderlab_out = vec4(shaderlab_v, 0.0, 1.0);',
      '}',
    ].join('\n') + '\n';
  }
  if (type === 'cubemap') {
    // st in [-1, 1] across the face, row 0 at t = -1: the GL cube-map selection table, inverted (cubeFaceBasis).
    return [
      'out vec4 shaderlab_out;',
      'void main() {',
      '  vec2 shaderlab_st = (gl_FragCoord.xy / iResolution.xy) * 2.0 - 1.0;',
      '  vec3 shaderlab_dir = normalize(shaderlab_faceCenter + shaderlab_st.x * shaderlab_faceRight + shaderlab_st.y * shaderlab_faceUp);',
      '  vec4 shaderlab_color = vec4(vec3(0.0), 1.0);',
      '  mainCubemap(shaderlab_color, gl_FragCoord.xy, vec3(0.0), shaderlab_dir);',
      '  shaderlab_out = shaderlab_color;',
      '}',
    ].join('\n') + '\n';
  }
  // Image writes an opaque pixel; a buffer keeps its alpha (buffers store data in all four channels).
  const store = type === 'image' ? 'vec4(shaderlab_color.rgb, 1.0)' : 'shaderlab_color';
  return [
    'out vec4 shaderlab_out;',
    'void main() {',
    '  vec4 shaderlab_color = vec4(vec3(0.0), 1.0);',
    '  mainImage(shaderlab_color, gl_FragCoord.xy);',
    `  shaderlab_out = ${store};`,
    '}',
  ].join('\n') + '\n';
}

/**
 * One pass's full fragment source: header + Common + the pass's code + footer, and the line counts that map a
 * compiler line number back to where it came from.
 *   {source, headerLines, commonLines, passLines, footerLines, entry}
 */
export function assembleSource(pass, commonCode = '', opts = {}) {
  const type = String((pass && pass.type) || 'image').toLowerCase();
  const header = buildHeader(type, (pass && pass.inputs) || [], opts);
  const common = sanitizeGlsl(commonCode);
  const code = sanitizeGlsl(pass && pass.code);
  const footer = buildFooter(type, code);
  const entry = type === 'sound' ? 'mainSound' : type === 'cubemap' ? 'mainCubemap' : 'mainImage';
  return {
    source: header + common + code + footer,
    headerLines: countLines(header), commonLines: countLines(common), passLines: countLines(code),
    footerLines: countLines(footer), entry,
  };
}

/** Where line `line` of an assembled source came from: {section: header|common|pass|footer, line}. */
export function locateLine(line, headerLines, commonLines = 0, passLines = Infinity) {
  if (line <= headerLines) return { section: 'header', line };
  if (line <= headerLines + commonLines) return { section: 'common', line: line - headerLines };
  if (line <= headerLines + commonLines + passLines) return { section: 'pass', line: line - headerLines - commonLines };
  return { section: 'footer', line: line - headerLines - commonLines - passLines };
}

const LOG_LINE = /^(\s*)(ERROR|WARNING):\s*(\d+):(\d+):/;

/**
 * A compiler log with each "ERROR: 0:<n>:" rewritten to where line n came from: "ERROR: <pass name>:<line>:" for the
 * pass's own code, "ERROR: Common:<line>:" for Common, "header:"/"footer:" for ours. headerLines is a number;
 * layout = {commonLines, passLines, passName, commonName} (all optional; with none, every line past the header is
 * the pass's). Lines that are not compiler diagnostics pass through unchanged.
 */
export function mapErrorLog(log, headerLines, layout = {}) {
  const commonLines = layout.commonLines || 0;
  const passLines = Number.isFinite(layout.passLines) ? layout.passLines : Infinity;
  const passName = layout.passName || 'pass';
  const commonName = layout.commonName || 'Common';
  return String(log || '').replace(/\u0000/g, '').split('\n').map((text) => text.replace(LOG_LINE, (m, ws, sev, src, ln) => {
    const at = locateLine(Number(ln), Number(headerLines) || 0, commonLines, passLines);
    const where = at.section === 'pass' ? passName : at.section === 'common' ? commonName : at.section;
    return `${ws}${sev}: ${where}:${at.line}:`;
  })).join('\n');
}

/** The diagnostics of a (mapped or raw) log as rows: [{severity, section, line, message}]. */
export function parseErrorLog(log) {
  const rows = [];
  for (const text of String(log || '').split('\n')) {
    const m = /^\s*(ERROR|WARNING):\s*([^:]+):(\d+):\s*(.*)$/.exec(text);
    if (m) rows.push({ severity: m[1], section: m[2].trim(), line: Number(m[3]), message: m[4].trim() });
  }
  return rows;
}

// ---------------------------------------------------------------------------------------------------------------
// Pure helpers: data textures, media, time
// ---------------------------------------------------------------------------------------------------------------

/** The six face paths of a saved cubemap: <name>.<ext> is +X, then <name>_1 .. <name>_5 (-X, +Y, -Y, +Z, -Z). */
export function cubemapFacePaths(src) {
  const s = String(src || '');
  const slash = s.lastIndexOf('/');
  const dot = s.lastIndexOf('.');
  const base = dot > slash ? s.slice(0, dot) : s;
  const ext = dot > slash ? s.slice(dot) : '';
  return [s, ...[1, 2, 3, 4, 5].map((i) => `${base}_${i}${ext}`)];
}

/** Which face image (index into cubemapFacePaths) each GL face (+X, -X, +Y, -Y, +Z, -Z) uploads. Shadertoy uploads a
 *  cubemap whose sampler says vflip with UNPACK_FLIP_Y AND its _2 and _3 images traded (the upside-down cube's top
 *  is the saved bottom); without vflip, in saved order. */
export function cubemapUploadOrder(flipY) {
  return flipY ? [0, 1, 3, 2, 4, 5] : [0, 1, 2, 3, 4, 5];
}

// Face i of a cube map (GL order +X, -X, +Y, -Y, +Z, -Z): the direction at face coordinates (sc, tc) in [-1, 1] is
// center + sc * right + tc * up. This is the GL cube-map selection table inverted, so what Cube A writes for a
// direction is exactly what texture(samplerCube, direction) reads back.
export const CUBE_FACES = Object.freeze([
  Object.freeze({ name: '+X', center: [1, 0, 0], right: [0, 0, -1], up: [0, -1, 0] }),
  Object.freeze({ name: '-X', center: [-1, 0, 0], right: [0, 0, 1], up: [0, -1, 0] }),
  Object.freeze({ name: '+Y', center: [0, 1, 0], right: [1, 0, 0], up: [0, 0, 1] }),
  Object.freeze({ name: '-Y', center: [0, -1, 0], right: [1, 0, 0], up: [0, 0, -1] }),
  Object.freeze({ name: '+Z', center: [0, 0, 1], right: [1, 0, 0], up: [0, -1, 0] }),
  Object.freeze({ name: '-Z', center: [0, 0, -1], right: [-1, 0, 0], up: [0, -1, 0] }),
]);
export function cubeFaceBasis(face) { return CUBE_FACES[face]; }

// The .bin volume: a 20-byte little-endian header (4-byte signature, uint32 width, height, depth, uint8 channels,
// uint8 layout, uint16 format: 0 = 8-bit unsigned, 10 = 32-bit float), then the texels, x fastest.
const VOLUME_FORMATS = { 0: 'u8', 10: 'f32' };
const VOLUME_GL = {
  u8: [null, [GL.R8, GL.RED], [GL.RG8, GL.RG], [GL.RGB8, GL.RGB], [GL.RGBA8, GL.RGBA]],
  f32: [null, [GL.R32F, GL.RED], [GL.RG32F, GL.RG], [GL.RGB32F, GL.RGB], [GL.RGBA32F, GL.RGBA]],
};

/** Parse a .bin volume: {signature, width, height, depth, channels, layout, format ('u8'|'f32'), formatCode, data,
 *  dataOffset, trailingBytes, glInternal, glFormat, glType}. Throws with a reason a reader can act on. */
export function parseVolumeBin(buffer) {
  let ab = buffer;
  if (ArrayBuffer.isView(buffer)) ab = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
  if (!(ab instanceof ArrayBuffer)) throw new Error('volume .bin: expected an ArrayBuffer');
  if (ab.byteLength < VOLUME_HEADER_BYTES) {
    throw new Error(`volume .bin: ${ab.byteLength} bytes is shorter than the ${VOLUME_HEADER_BYTES}-byte header`);
  }
  const v = new DataView(ab);
  const signature = String.fromCharCode(v.getUint8(0), v.getUint8(1), v.getUint8(2), v.getUint8(3)).replace(/\0+$/, '');
  const width = v.getUint32(4, true);
  const height = v.getUint32(8, true);
  const depth = v.getUint32(12, true);
  const channels = v.getUint8(16);
  const layout = v.getUint8(17);
  const formatCode = v.getUint16(18, true);
  const format = VOLUME_FORMATS[formatCode];
  if (!format) throw new Error(`volume .bin: unknown texel format ${formatCode} (known: 0 = u8, 10 = f32)`);
  if (channels < 1 || channels > 4) throw new Error(`volume .bin: ${channels} channels (1 to 4 are possible)`);
  if (!width || !height || !depth) throw new Error(`volume .bin: empty size ${width}x${height}x${depth}`);
  const bytesPerTexel = channels * (format === 'u8' ? 1 : 4);
  const need = width * height * depth * bytesPerTexel;
  const have = ab.byteLength - VOLUME_HEADER_BYTES;
  if (have < need) {
    throw new Error(`volume .bin: header says ${width}x${height}x${depth}x${channels} ${format} (${need} bytes), file holds ${have}`);
  }
  const data = format === 'u8'
    ? new Uint8Array(ab, VOLUME_HEADER_BYTES, need)
    : new Float32Array(ab, VOLUME_HEADER_BYTES, need / 4);
  const [glInternal, glFormat] = VOLUME_GL[format][channels];
  return {
    signature, width, height, depth, channels, layout, format, formatCode, data,
    dataOffset: VOLUME_HEADER_BYTES, trailingBytes: have - need,
    glInternal, glFormat, glType: format === 'u8' ? GL.UNSIGNED_BYTE : GL.FLOAT,
  };
}

/** The keyboard texture: 256 x 3, one byte per texel (R8). Row 0 holds keys down now, row 1 keys that went down
 *  this frame (cleared after each frame), row 2 a toggle flipped on every press. A key's texel is x = keyCode. */
export function keyboardTextureLayout() {
  const { width, height, rows } = KEYBOARD;
  return {
    width, height, rows: { ...rows }, bytes: width * height, on: 255, off: 0,
    internalFormat: GL.R8, format: GL.RED, type: GL.UNSIGNED_BYTE,
    index: (keyCode, row) => row * width + (keyCode & 0xff),
    // The texel centre a texture() lookup must hit for row r, for shaders that do not use texelFetch.
    rowV: (row) => (row + 0.5) / height,
  };
}

/** Live keyboard state packed as the keyboard texture's bytes. set() on a held key (auto-repeat) changes nothing. */
export function createKeyboardState() {
  const L = keyboardTextureLayout();
  const bytes = new Uint8Array(L.bytes);
  let dirty = true;
  return {
    bytes,
    get dirty() { return dirty; },
    markClean() { dirty = false; },
    set(keyCode, down) {
      const k = Number(keyCode) & 0xff;
      const wasDown = bytes[L.index(k, L.rows.down)] !== 0;
      if (down && !wasDown) {
        bytes[L.index(k, L.rows.down)] = L.on;
        bytes[L.index(k, L.rows.pressed)] = L.on;
        bytes[L.index(k, L.rows.toggle)] ^= L.on;
        dirty = true;
      } else if (!down && wasDown) {
        bytes[L.index(k, L.rows.down)] = L.off;
        dirty = true;
      }
    },
    endFrame() {
      const row = bytes.subarray(L.rows.pressed * L.width, (L.rows.pressed + 1) * L.width);
      if (row.some((b) => b !== 0)) { row.fill(0); dirty = true; }
    },
    clear() { bytes.fill(0); dirty = true; },
  };
}

function resampleAt(src, i, n) {
  const len = src.length;
  if (len === n) return src[i];
  if (len === 1) return src[0];
  const x = (i * (len - 1)) / (n - 1);
  const i0 = Math.floor(x);
  const i1 = Math.min(i0 + 1, len - 1);
  const f = x - i0;
  return src[i0] + (src[i1] - src[i0]) * f;
}
const finiteOr = (v, d) => (Number.isFinite(v) ? v : d);

/**
 * The 512 x 2 audio texture's bytes. fft: spectrum magnitudes in 0..1 (row 0, byte = round(v * 255)); wave:
 * waveform samples in -1..1 (row 1, 0 -> 128, the value silence has). Any other length is resampled linearly across
 * its whole range; to match an AnalyserNode with fftSize 2048, pass its first 512 bins. null means silence.
 */
export function packAudioTexture(fft, wave, out = new Uint8Array(AUDIO.width * AUDIO.height)) {
  const n = AUDIO.width;
  for (let i = 0; i < n; i += 1) {
    const v = fft && fft.length ? finiteOr(resampleAt(fft, i, n), 0) : 0;
    out[i] = Math.round(Math.min(1, Math.max(0, v)) * 255);
  }
  for (let i = 0; i < n; i += 1) {
    const v = wave && wave.length ? finiteOr(resampleAt(wave, i, n), 0) : 0;
    out[n + i] = Math.round((Math.min(1, Math.max(-1, v)) * 0.5 + 0.5) * 255);
  }
  return out;
}

/** iDate: [year, month (0-based), day, seconds since local midnight]. Takes a Date, a timestamp, or a ready vec4. */
export function dateUniform(date) {
  if (Array.isArray(date) || ArrayBuffer.isView(date)) return [0, 1, 2, 3].map((i) => Number(date[i]) || 0);
  const d = date instanceof Date ? date : new Date(date === undefined || date === null ? Date.now() : date);
  return [d.getFullYear(), d.getMonth(), d.getDate(),
    d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds() + d.getMilliseconds() / 1000];
}

// iMouse as Shadertoy's page builds it each frame: xy is the pointer (it follows a drag while the button is down and
// stays put otherwise), zw is where the last click landed, with signs that carry the button: z > 0 while the button is
// held and -|z| after release; w > 0 on the ONE frame of the click and -|w| on every other frame. Never clicked:
// all four are 0. Shaders test these signs (iMouse.z > 0.0: dragging; iMouse.w > 0.0: just clicked).
const unsignedZero = (v) => (v === 0 ? 0 : v);   // -0 -> 0, so a never-clicked mouse is exactly (0, 0, 0, 0)

/** The iMouse vec4 for a mouse state {x, y, clickX, clickY, down, clicked}; clickX and clickY are magnitudes (pixels
 *  from the bottom-left), the flags set the signs. */
export function mouseUniform({ x = 0, y = 0, clickX = 0, clickY = 0, down = false, clicked = false } = {}) {
  const cx = Math.abs(Number(clickX) || 0);
  const cy = Math.abs(Number(clickY) || 0);
  return [Number(x) || 0, Number(y) || 0, unsignedZero(down ? cx : -cx), unsignedZero(clicked ? cy : -cy)];
}

/** The iMouse of the frame after `mouse` when nothing new happens: the click signal (w > 0) lasts one frame. */
export function mouseAfterFrame(mouse) {
  const m = [0, 1, 2, 3].map((i) => Number(mouse && mouse[i]) || 0);
  return [m[0], m[1], unsignedZero(m[2]), unsignedZero(-Math.abs(m[3]))];
}

// render()'s mouse argument: a raw vec4 is used as given; a state object goes through mouseUniform.
function mouseVec(m) {
  if (Array.isArray(m) || ArrayBuffer.isView(m)) return [0, 1, 2, 3].map((i) => Number(m[i]) || 0);
  if (m && typeof m === 'object') return mouseUniform(m);
  return null;
}

/** True when t lands on the frame grid of fps (t * fps is an integer, within GRID_EPS). */
export function onFrameGrid(t, fps) {
  const n = Number(t) * Number(fps);
  return Number.isFinite(n) && Math.abs(n - Math.round(n)) < GRID_EPS;
}

/**
 * The frames advance() renders to reach toTime: frame n at time n / fps (fixed dt) while that is before toTime,
 * then one last frame exactly at toTime (snapped to n / fps when toTime is on the grid). From a reset
 * (fromFrame 0, lastTime null) the same toTime always gives the same list -- a feedback shader's still is
 * reproducible. Continuing from an on-grid stop gives exactly the frames a fresh run would; from an off-grid stop
 * it does not, so render.html resets then. Returns [] when lastTime already reached toTime (or passed it: reset).
 * maxFrames cuts the list; calling again continues where it stopped, and the pieces join to the uncut list.
 */
export function advanceSchedule(fromFrame, lastTime, toTime, fps = DEFAULT_FPS, maxFrames = Infinity) {
  const rate = Number(fps) > 0 ? Number(fps) : DEFAULT_FPS;
  const dt = 1 / rate;
  const target = onFrameGrid(toTime, rate) ? Math.round(toTime * rate) / rate : Number(toTime);
  const out = [];
  let prev = lastTime === null || lastTime === undefined ? null : Number(lastTime);
  if (!Number.isFinite(target) || (prev !== null && prev >= target - TIME_EPS)) return out;
  let n = Math.max(0, Math.floor(Number(fromFrame) || 0));
  while (out.length < maxFrames) {
    const tn = n / rate;
    if (tn >= target - TIME_EPS) break;
    if (prev === null || tn > prev + TIME_EPS) {
      out.push({ frame: n, time: tn, timeDelta: prev === null ? dt : tn - prev, final: false });
      prev = tn;
    }
    n++;
  }
  if (out.length < maxFrames) out.push({ frame: n, time: target, timeDelta: prev === null ? dt : target - prev, final: true });
  return out;
}

/**
 * The last frame of advanceSchedule(0, null, toTime, fps), found without listing the frames before it:
 * {frame, time, timeDelta, final: true}. A shader with no history (needsHistory false) draws the same pixels for that
 * frame whether or not the frames before it were drawn, so its still can be this one frame (toy.jump) instead of a
 * walk from a reset. tests/shaderlab_runtime.test.mjs holds the two equal over a sweep of times and rates.
 */
export function jumpStep(toTime, fps = DEFAULT_FPS) {
  const rate = Number(fps) > 0 ? Number(fps) : DEFAULT_FPS;
  const target = onFrameGrid(toTime, rate) ? Math.round(toTime * rate) / rate : Number(toTime);
  if (!Number.isFinite(target)) return null;
  // The first frame whose grid time reaches the target (within TIME_EPS), the same test advanceSchedule stops on.
  let n = Math.max(0, Math.ceil((target - TIME_EPS) * rate));
  while (n > 0 && (n - 1) / rate >= target - TIME_EPS) n--;
  while (n / rate < target - TIME_EPS) n++;
  return { frame: n, time: target, timeDelta: n === 0 ? 1 / rate : target - (n - 1) / rate, final: true };
}

/**
 * Whether a frame depends on the frames before it: true when any drawn pass reads a buffer (or Cube A) that holds
 * the PREVIOUS frame's result (passOrder's 'previous-frame': a buffer reading itself or a pass later in the order).
 * Without such a read every frame is a pure function of its uniforms, and a still needs no walk.
 */
export function needsHistory(renderpass) {
  return passOrder(renderpass).some((e) => e.reads.some((r) => r.sees === 'previous-frame'));
}

/** The order in which buffer formats are tried, best first, for the extensions a context has. */
export const BUFFER_FORMATS = Object.freeze({
  RGBA32F: Object.freeze({ name: 'RGBA32F', internal: GL.RGBA32F, format: GL.RGBA, type: GL.FLOAT, bits: 32 }),
  RGBA16F: Object.freeze({ name: 'RGBA16F', internal: GL.RGBA16F, format: GL.RGBA, type: GL.HALF_FLOAT, bits: 16 }),
  RGBA8: Object.freeze({ name: 'RGBA8', internal: GL.RGBA8, format: GL.RGBA, type: GL.UNSIGNED_BYTE, bits: 8 }),
});
export function bufferFormatCandidates(caps = {}) {
  const out = [];
  // RGBA32F only with float linear filtering: a linear-filtered buffer read is the common case, and an unfilterable
  // texture samples as black.
  if (caps.colorBufferFloat && caps.floatLinear) out.push(BUFFER_FORMATS.RGBA32F);
  if (caps.colorBufferFloat || caps.colorBufferHalfFloat) out.push(BUFFER_FORMATS.RGBA16F);
  out.push(BUFFER_FORMATS.RGBA8);
  return out;
}
export function chooseBufferFormat(caps = {}) { return bufferFormatCandidates(caps)[0]; }

/** FNV-1a, 32-bit: a stable seed from a media path. */
export function hashString(s) {
  let h = 0x811c9dc5;
  const str = String(s);
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A deterministic RGBA8 stand-in (value noise on the texel lattice, seeded by `seed`), with the channel pairing of
 *  NOISE_CHANNEL_OFFSET: G(x, y) = R(x - 37, y - 17) and A(x, y) = B(x - 37, y - 17), wrapping. */
export function proceduralTexture(seed, width = STANDIN_SIZE, height = STANDIN_SIZE) {
  const rnd = mulberry32(hashString(seed));
  const n = width * height;
  const r = new Uint8Array(n);
  const b = new Uint8Array(n);
  for (let i = 0; i < n; i += 1) { r[i] = (rnd() * 256) | 0; b[i] = (rnd() * 256) | 0; }
  const [ox, oy] = NOISE_CHANNEL_OFFSET;
  const out = new Uint8Array(n * 4);
  for (let y = 0; y < height; y++) {
    const sy = (((y - oy) % height) + height) % height;
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const j = sy * width + ((((x - ox) % width) + width) % width);
      out[i * 4] = r[i];
      out[i * 4 + 1] = r[j];
      out[i * 4 + 2] = b[i];
      out[i * 4 + 3] = b[j];
    }
  }
  return out;
}

/** A deterministic RGBA8 noise volume (size^3), seeded by `seed`. */
export function proceduralVolume(seed, size = STANDIN_VOLUME_SIZE) {
  const rnd = mulberry32(hashString(seed));
  const out = new Uint8Array(size * size * size * 4);
  for (let i = 0; i < out.length; i++) out[i] = (rnd() * 256) | 0;
  return out;
}

// WHICH STAND-IN. A missing file is replaced by something with the statistics its kind usually has, so a render
// without the corpus media still reads as the shader rather than as static. Shadertoy's noise textures are PNG
// (lossless, so a hash survives), its photographs and material textures are JPEG, and its cubemaps are photographed
// environments. So: .png -> per-texel value noise (proceduralTexture, the house noise layout), .jpg/.jpeg -> a smooth
// photo-like field (proceduralPhoto), cubemap -> a soft sky-and-ground environment (proceduralEnvironment). Every one
// is still listed in stats().substituted, with its style.
//
// Four of the corpus's PNGs are pinned down further by how the corpus's own shaders address them (a usage census of
// state/arsenal/shaders/corpus, 2026-10-13): their size, which a texelFetch or a "(p + 0.5) / 64.0" lookup depends
// on, and for one its kind. A stand-in of the wrong size reads zeros past its edge (texelFetch) or a different
// lattice; this table keeps the stand-in addressable the way the shader expects. Keys are the files' basenames.
export const KNOWN_MEDIA = Object.freeze({
  // texelFetch(..., p % 1024) in a dozen shaders: a 1024 x 1024 noise (dither / random-number source)
  'cb49c003b454385aa9975733aff4571c62182ccdda480aaba9a8d250014f00ec.png': Object.freeze({ size: 1024, style: 'noise' }),
  // (floor(p).xy + vec2(37, 17) + f.xy + 0.5) / 64.0: a 64 x 64 noise with the paired channels
  '3083c722c0c738cad0f468383167a0d246f91af2bfa373e9c5c094fb8c8413e0.png': Object.freeze({ size: 64, style: 'noise' }),
  // (uv + 0.5) / 64.0: a 64 x 64 noise
  '0a40562379b63dfb89227e6d172f39fdce9022cba76623f1054a2c83d6c0ba5d.png': Object.freeze({ size: 64, style: 'noise' }),
  // sampled at low frequency as terrain, weather and skin fields: a smooth image, not per-texel noise
  'ad56fba948dfba9ae698198c109e71f118a54d209c0ea50d77ea546abad89c57.png': Object.freeze({ style: 'photo' }),
});
const knownMedia = (src) => KNOWN_MEDIA[String(src || '').split(/[?#]/)[0].split('/').pop()] || null;

export function standinStyle(kind, src) {
  if (kind === 'cubemap') return 'environment';
  if (kind === 'video' || kind === 'webcam') return 'photo';   // moving pictures of the world, not hash tables
  const known = knownMedia(src);
  if (known && known.style) return known.style;
  return /\.jpe?g$/i.test(String(src || '').split(/[?#]/)[0]) ? 'photo' : 'noise';
}

/** The side of a 2D stand-in: KNOWN_MEDIA's size for a file the corpus pins down, else STANDIN_SIZE. */
export function standinSize(kind, src) {
  const known = (kind === 'texture') ? knownMedia(src) : null;
  return (known && known.size) || STANDIN_SIZE;
}

/** The RGBA8 pixels (standinSize^2) of a 2D stand-in in the style standinStyle picks. */
export function standinPixels(kind, src) {
  const n = standinSize(kind, src);
  return standinStyle(kind, src) === 'photo' ? proceduralPhoto(src, n, n) : proceduralTexture(src, n, n);
}

// Tiling value noise: a `cells` x `cells` lattice of seeded values over the texture, smoothstep-interpolated, wrapping.
function tilingValueNoise(rnd, cells) {
  const lattice = new Float32Array(cells * cells);
  for (let i = 0; i < lattice.length; i++) lattice[i] = rnd();
  return (u, v) => {   // u, v in [0, 1)
    const x = u * cells, y = v * cells;
    const x0 = Math.floor(x), y0 = Math.floor(y);
    const fx = x - x0, fy = y - y0;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const at = (i, j) => lattice[(((j % cells) + cells) % cells) * cells + (((i % cells) + cells) % cells)];
    const a = at(x0, y0) + (at(x0 + 1, y0) - at(x0, y0)) * sx;
    const b = at(x0, y0 + 1) + (at(x0 + 1, y0 + 1) - at(x0, y0 + 1)) * sx;
    return a + (b - a) * sy;
  };
}
export const PHOTO_OCTAVES = Object.freeze([4, 8, 16, 32, 64]);   // lattice cells across the texture, coarse to fine
// A summed fbm crowds around 0.5; a photograph's histogram is wider and sits a little below the middle. The field is
// stretched by PHOTO_CONTRAST about PHOTO_MEAN (clamped), and each channel gets a seeded tint within PHOTO_TINT.
// (Tuned on the corpus: a brighter, narrower stand-in made a height-field shader that thresholds its texture at
// about 0.66 stop on its first step and draw black.)
export const PHOTO_MEAN = 0.42;
export const PHOTO_CONTRAST = 1.9;
export const PHOTO_TINT = 0.15;

/** A deterministic RGBA8 stand-in for a photograph or material texture: fbm of tiling value noise (PHOTO_OCTAVES,
 *  gain 0.5) widened to a photo-like histogram, channels correlated the way a photo's are (one luminance field, a
 *  seeded tint, a slow second field for colour drift), opaque. It tiles, so a repeat-wrapped lookup shows no seam. */
export function proceduralPhoto(seed, width = STANDIN_SIZE, height = STANDIN_SIZE) {
  const rnd = mulberry32(hashString(`${seed}#photo`));
  const octaves = PHOTO_OCTAVES.map((c) => tilingValueNoise(rnd, c));
  const drift = tilingValueNoise(rnd, 3);
  const tint = [0, 1, 2].map(() => 1 - PHOTO_TINT + 2 * PHOTO_TINT * rnd());
  const out = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const u = x / width, v = y / height;
      let lum = 0, amp = 0.5, norm = 0;
      for (const n of octaves) { lum += amp * n(u, v); norm += amp; amp *= 0.5; }
      lum = Math.max(0, Math.min(1, PHOTO_MEAN + (lum / norm - 0.5) * PHOTO_CONTRAST));
      const d = drift(u, v) - 0.5;
      const i = (y * width + x) * 4;
      for (let c = 0; c < 3; c++) {
        const shift = c === 0 ? d : c === 2 ? -d : 0;
        out[i + c] = Math.max(0, Math.min(255, Math.round(255 * lum * tint[c] * (1 + 0.6 * shift))));
      }
      out[i + 3] = 255;
    }
  }
  return out;
}

/** Six RGBA8 faces (GL order +X, -X, +Y, -Y, +Z, -Z, each size^2) of a soft environment: a sky brightening toward
 *  the zenith, a warm horizon, a darker ground, one seeded sun glow, and a little low-frequency variation. Face texel
 *  (i, j) looks along CUBE_FACES[f].center + sc * right + tc * up with sc, tc at the texel centre in [-1, 1] -- the
 *  same table Cube A renders with, so texture(samplerCube, d) reads the colour of direction d. */
export function proceduralEnvironment(seed, size = STANDIN_CUBE_SIZE) {
  const rnd = mulberry32(hashString(`${seed}#environment`));
  const sunZ = rnd() * 2 - 1, sunA = rnd() * 2 * Math.PI, sunY = 0.2 + 0.5 * rnd();
  const sr = Math.sqrt(Math.max(0, 1 - sunY * sunY));
  const sun = [Math.cos(sunA) * sr, sunY, Math.sin(sunA) * sr];
  const phase = [rnd() * 6.283, rnd() * 6.283, rnd() * 6.283];
  const mixc = (a, b, t) => a.map((v, k) => v + (b[k] - v) * t);
  const ZENITH = [0.35, 0.5, 0.75], HORIZON = [0.85, 0.78, 0.7], GROUND = [0.22, 0.2, 0.18], SUN = [1.0, 0.92, 0.8];
  return CUBE_FACES.map((F) => {
    const face = new Uint8Array(size * size * 4);
    for (let j = 0; j < size; j++) {
      const tc = ((j + 0.5) / size) * 2 - 1;
      for (let i = 0; i < size; i++) {
        const sc = ((i + 0.5) / size) * 2 - 1;
        const d = [0, 1, 2].map((k) => F.center[k] + sc * F.right[k] + tc * F.up[k]);
        const len = Math.hypot(d[0], d[1], d[2]);
        const [x, y, z] = d.map((v) => v / len);
        let c = y >= 0 ? mixc(HORIZON, ZENITH, Math.pow(y, 0.6)) : mixc(HORIZON, GROUND, Math.pow(-y, 0.4));
        const s = Math.max(0, x * sun[0] + y * sun[1] + z * sun[2]);
        c = mixc(c, SUN, 0.6 * Math.pow(s, 24) + 0.15 * Math.pow(s, 4));
        const wobble = 0.08 * (Math.sin(3 * x + phase[0]) * Math.sin(2 * z + phase[1]) + Math.sin(4 * y + 2 * x + phase[2]));
        const o = (j * size + i) * 4;
        for (let k = 0; k < 3; k++) face[o + k] = Math.max(0, Math.min(255, Math.round(255 * c[k] * (1 + wobble))));
        face[o + 3] = 255;
      }
    }
    return face;
  });
}

/** A shader JSON from whatever a fetch returned: the saved {info, renderpass}, the API's {Shader: {...}}, or a list. */
export function normalizeShader(json) {
  let s = json;
  if (Array.isArray(s)) s = s[0];
  if (s && s.Shader) s = s.Shader;
  if (!s || !Array.isArray(s.renderpass)) throw new Error('not a shader: no renderpass list');
  return s;
}

/** A single-pass shader JSON around a bare mainImage source (a .frag sketch). */
export function shaderFromGlsl(code, { name = 'sketch', id = 'local' } = {}) {
  return {
    info: { id, name, username: 'local', description: '' },
    renderpass: [{ name: 'Image', type: 'image', code: String(code || ''), inputs: [], outputs: [{ id: '4dfGRr', channel: 0 }] }],
  };
}

// The house's renderer rule, the same one the headless driver (arsenal/shaders/headless.mjs) and render.py apply: a
// renderer string must name SwiftShader AND name no hardware ("SwiftShader via Direct3D11" is hardware until proved
// otherwise). tests/shaderlab_runtime.test.mjs holds this copy equal to the driver's over the harness's table.
export const HARDWARE_HINT = /\b(amd|radeon|ati|nvidia|geforce|quadro|rtx|intel|iris|uhd graphics|adreno|mali|apple m\d|direct3d\d*|d3d\d+)\b/i;
/** {ok, reason}: ok only for a renderer string that names SwiftShader and no hardware. */
export function judgeRenderer(renderer) {
  if (typeof renderer !== 'string' || !renderer.trim()) {
    return { ok: false, reason: 'no renderer string (no WebGL2 context, or WEBGL_debug_renderer_info is unavailable)' };
  }
  if (!/swiftshader/i.test(renderer)) return { ok: false, reason: `the renderer is not SwiftShader: ${renderer}` };
  const hw = HARDWARE_HINT.exec(renderer);
  if (hw) return { ok: false, reason: `the renderer names hardware (${hw[0]}): ${renderer}` };
  return { ok: true, reason: null };
}

/** Renderer facts from a live context; swiftshader says whether the CPU rasteriser is the one drawing (judgeRenderer
 *  passed: the string names SwiftShader and no hardware), judged carries the rule's reason when it did not. */
export function rendererInfo(gl) {
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const renderer = String(gl.getParameter(dbg ? GL.UNMASKED_RENDERER_WEBGL : GL.RENDERER) || '');
  const vendor = String(gl.getParameter(dbg ? GL.UNMASKED_VENDOR_WEBGL : GL.VENDOR) || '');
  // A masked renderer ("WebKit WebGL") names no SwiftShader, so it fails the rule on its own; a browser that reports
  // the real string through RENDERER without the extension is judged on that string.
  const judged = judgeRenderer(renderer);
  return {
    renderer, vendor, version: String(gl.getParameter(GL.VERSION) || ''),
    glsl: String(gl.getParameter(GL.SHADING_LANGUAGE_VERSION) || ''),
    swiftshader: judged.ok, judged, unmasked: !!dbg,
  };
}

// ---------------------------------------------------------------------------------------------------------------
// The runtime
// ---------------------------------------------------------------------------------------------------------------

// A fullscreen triangle from gl_VertexID: no vertex buffer, no attributes (the house template).
const VERTEX_SOURCE = [
  '#version 300 es',
  'precision highp float;',
  'void main() {',
  '  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));',
  '  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);',
  '}',
].join('\n');

const UNIFORM_NAMES = [
  'iResolution', 'iTime', 'iTimeDelta', 'iFrameRate', 'iFrame', 'iChannelTime', 'iChannelResolution', 'iMouse',
  'iDate', 'iSampleRate', 'iBlockOffset', 'shaderlab_blockSize', 'iChannel0', 'iChannel1', 'iChannel2', 'iChannel3',
  'shaderlab_faceCenter', 'shaderlab_faceRight', 'shaderlab_faceUp',
];
const TARGETS = [GL.TEXTURE_2D, GL.TEXTURE_CUBE_MAP, GL.TEXTURE_3D];

function loadImageElement(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    if (typeof Image === 'undefined') { reject(new Error('no Image in this realm')); return; }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    let settled = false;
    const done = (fn, v) => { if (!settled) { settled = true; clearTimeout(timer); fn(v); } };
    const timer = setTimeout(() => done(reject, new Error(`timed out after ${timeoutMs} ms`)), timeoutMs);
    img.onload = () => done(resolve, img);
    img.onerror = () => done(reject, new Error('load failed'));
    img.src = url;
  });
}

async function fetchArrayBuffer(url, timeoutMs) {
  if (typeof fetch !== 'function') throw new Error('no fetch in this realm');
  const ctl = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = setTimeout(() => ctl && ctl.abort(), timeoutMs);
  try {
    const res = await fetch(url, ctl ? { signal: ctl.signal } : undefined);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.arrayBuffer();
  } catch (e) {
    throw new Error(e && e.name === 'AbortError' ? `timed out after ${timeoutMs} ms` : (e && e.message) || String(e));
  } finally {
    clearTimeout(timer);
  }
}

/**
 * A runnable Shadertoy-interface shader on `canvas`.
 *   shader:  the saved JSON ({info, renderpass}) exactly as corpus/shaders/<id>/shader.json holds it.
 *   options: {mediaUrl(src) -> url|null, audio: {fft, wave}|null, pixelRatio, cubeSize, hwPerformance (0|1),
 *             mediaTimeoutMs, fps (advance's default), dateBase ([y, m, d, s]: iDate = base + iTime, for
 *             reproducible stills; default the real clock), bufferFormat ('RGBA16F' to force one), loseContextOnDestroy,
 *             parity (default true: the GPU-parity shims; false compiles each pass exactly as written)}
 * Media start loading at once; await toy.ready (or toy.load()) before rendering a still, or the first frames use
 * the stand-ins. The canvas keeps the size the caller gave it until resize().
 */
export function createToy(canvas, shader, options = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...(options || {}) };
  const gl = canvas.getContext('webgl2', CONTEXT_ATTRIBUTES);
  if (!gl) throw new Error('shaderlab: WebGL2 is not available on this canvas');
  const sh = normalizeShader(shader);
  const rp = sh.renderpass;
  const commonCode = rp.filter((p) => String(p.type).toLowerCase() === 'common').map((p) => p.code || '').join('\n');
  const order = passOrder(rp);
  const history = order.some((e) => e.reads.some((r) => r.sees === 'previous-frame'));   // needsHistory(rp)
  const info = rendererInfo(gl);
  const warnings = [];
  const unsupported = [];
  const substituted = new Map();
  const state = { frame: 0, time: 0, lastTime: null, mouse: [0, 0, 0, 0], lost: false, destroyed: false,
    framesRendered: 0, glErrors: [], compiled: null };
  const pending = [];

  // style names the stand-in drawn in the file's place (standinStyle), or is absent when the read is black.
  const substitute = (src, kind, reason, style) => {
    const key = `${src}|${reason}`;
    if (!substituted.has(key)) substituted.set(key, style ? { src, kind, reason, style } : { src, kind, reason });
  };
  if (typeof canvas.addEventListener === 'function') {
    canvas.addEventListener('webglcontextlost', (e) => { if (e && e.preventDefault) e.preventDefault(); state.lost = true; });
  }

  // ---- fixed GL state ----
  for (const cap of [GL.BLEND, GL.DEPTH_TEST, GL.SCISSOR_TEST, GL.CULL_FACE, GL.DITHER]) gl.disable(cap);
  gl.pixelStorei(GL.UNPACK_ALIGNMENT, 1);
  gl.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(GL.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.pixelStorei(GL.UNPACK_COLORSPACE_CONVERSION_WEBGL, GL.NONE);
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);
  const caps = {
    colorBufferFloat: !!gl.getExtension('EXT_color_buffer_float'),
    floatLinear: !!gl.getExtension('OES_texture_float_linear'),
    colorBufferHalfFloat: !!gl.getExtension('EXT_color_buffer_half_float'),
  };

  // ---- what cannot run ----
  rp.forEach((p) => {
    if (!passKey(p)) unsupported.push({ what: 'pass', name: passDisplayName(p), type: p.type, reason: 'unknown pass type or buffer name' });
  });
  for (const d of order.duplicates) unsupported.push({ what: 'pass', name: d.name, type: d.key, reason: `a second ${d.key} pass; the first one runs` });
  if (rp.some((p) => passKey(p) === 'sound')) {
    unsupported.push({ what: 'sound playback', name: 'Sound', reason: 'the Sound pass compiles but is never played' });
  }

  // ---- texture helpers (all binding on the scratch unit) ----
  const scratch = (target, tex) => { gl.activeTexture(GL.TEXTURE0 + SCRATCH_UNIT); gl.bindTexture(target, tex); };
  const plainParams = (target) => {
    gl.texParameteri(target, GL.TEXTURE_MIN_FILTER, GL.NEAREST);
    gl.texParameteri(target, GL.TEXTURE_MAG_FILTER, GL.NEAREST);
    gl.texParameteri(target, GL.TEXTURE_WRAP_S, GL.CLAMP_TO_EDGE);
    gl.texParameteri(target, GL.TEXTURE_WRAP_T, GL.CLAMP_TO_EDGE);
    if (target !== GL.TEXTURE_2D) gl.texParameteri(target, GL.TEXTURE_WRAP_R, GL.CLAMP_TO_EDGE);
  };
  const tex2D = (w, h, internal, format, type, data, mips) => {
    const t = gl.createTexture();
    scratch(GL.TEXTURE_2D, t);
    gl.texImage2D(GL.TEXTURE_2D, 0, internal, w, h, 0, format, type, data);
    plainParams(GL.TEXTURE_2D);
    if (mips) gl.generateMipmap(GL.TEXTURE_2D);
    return t;
  };
  const texCube = (size, internal, format, type, faces, mips) => {
    const t = gl.createTexture();
    scratch(GL.TEXTURE_CUBE_MAP, t);
    for (let f = 0; f < 6; f++) {
      gl.texImage2D(GL.TEXTURE_CUBE_MAP_POSITIVE_X + f, 0, internal, size, size, 0, format, type, faces ? faces[f] : null);
    }
    plainParams(GL.TEXTURE_CUBE_MAP);
    if (mips) gl.generateMipmap(GL.TEXTURE_CUBE_MAP);
    return t;
  };
  const tex3D = (w, h, d, internal, format, type, data, mips) => {
    const t = gl.createTexture();
    scratch(GL.TEXTURE_3D, t);
    gl.texImage3D(GL.TEXTURE_3D, 0, internal, w, h, d, 0, format, type, data);
    plainParams(GL.TEXTURE_3D);
    if (mips) gl.generateMipmap(GL.TEXTURE_3D);
    return t;
  };
  const black = new Uint8Array([0, 0, 0, 255]);
  const dummy = {
    [GL.TEXTURE_2D]: tex2D(1, 1, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, black, false),
    [GL.TEXTURE_CUBE_MAP]: texCube(1, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, [black, black, black, black, black, black], false),
    [GL.TEXTURE_3D]: tex3D(1, 1, 1, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, black, false),
  };

  // ---- render targets: buffers A-D and Cube A ----
  const drawn = order;
  const buffers = new Map();
  let cube = null;
  const wantMips = new Set();
  for (const e of drawn) {
    for (const input of (rp[e.index].inputs || [])) {
      const k = bufferKeyForInput(input);
      if (k && samplerFor(input).mipmaps) wantMips.add(k);
    }
  }
  const sizeNow = () => [Math.max(1, gl.drawingBufferWidth || canvas.width || 1), Math.max(1, gl.drawingBufferHeight || canvas.height || 1)];

  const makeTarget = (fmt, w, h) => {
    const tex = tex2D(w, h, fmt.internal, fmt.format, fmt.type, null, false);
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(GL.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(GL.FRAMEBUFFER, GL.COLOR_ATTACHMENT0, GL.TEXTURE_2D, tex, 0);
    const ok = gl.checkFramebufferStatus(GL.FRAMEBUFFER) === GL.FRAMEBUFFER_COMPLETE;
    return { tex, fbo, ok };
  };
  const dropTarget = (t) => { gl.deleteFramebuffer(t.fbo); gl.deleteTexture(t.tex); };

  // Pick the best format this context can actually render into (a 4x4 probe per candidate).
  let candidates = bufferFormatCandidates(caps);
  if (opts.bufferFormat && BUFFER_FORMATS[opts.bufferFormat]) {
    candidates = [BUFFER_FORMATS[opts.bufferFormat], ...candidates.filter((c) => c.name !== opts.bufferFormat)];
  }
  let fmt = BUFFER_FORMATS.RGBA8;
  const needTargets = drawn.some((e) => e.key !== 'image');
  if (needTargets) {
    fmt = null;
    for (const c of candidates) {
      const probe = makeTarget(c, 4, 4);
      dropTarget(probe);
      if (probe.ok) { fmt = c; break; }
    }
    if (!fmt) { fmt = BUFFER_FORMATS.RGBA8; warnings.push('no buffer format is renderable on this context; buffers will not draw'); }
    if (fmt.name === 'RGBA8') warnings.push('buffers are 8-bit (no float render targets): values clamp to 0..1 and lose precision');
    else if (fmt.name === 'RGBA16F') warnings.push('buffers are RGBA16F (half float): RGBA32F was not available with linear filtering');
  }
  // Cube A in half float when that renders: a 1024^2 x 6 x 2 cube in RGBA32F is 192 MB of system memory on SwiftShader.
  const cubeFmt = fmt.name === 'RGBA32F' && candidates.includes(BUFFER_FORMATS.RGBA16F) ? BUFFER_FORMATS.RGBA16F : fmt;

  const clearFbo = (fbo) => {
    gl.bindFramebuffer(GL.FRAMEBUFFER, fbo);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(GL.COLOR_BUFFER_BIT);
  };
  // A cleared target that is read with the mipmap filter needs its mip chain rebuilt from the cleared level 0: before
  // its first render it has none (an incomplete texture samples as opaque black, not as zero), and after a reset the
  // old levels would still hold the previous run's pixels, so a "fresh" still would not be fresh.
  const remip = (target, tex) => { scratch(target, tex); gl.generateMipmap(target); };
  // Buffers sized to the canvas. A buffer already at that size is kept as it is. A buffer whose size changes gets two
  // new cleared targets, and each old half is copied texel for texel into the same half of the new pair over the
  // region both sizes share (bottom-left; the rest stays 0), then the ping-pong index goes back to half 0. That is
  // Shadertoy's resize, quirk included: if the newest frame sat in half 1, the next frame reads the older half 0.
  const allocBuffers = () => {
    const [w, h] = sizeNow();
    const old = new Map(buffers);
    buffers.clear();
    for (const e of drawn) {
      if (!BUFFER_KEYS.includes(e.key)) continue;
      const prev = old.get(e.key);
      if (prev && prev.w === w && prev.h === h) { buffers.set(e.key, prev); old.delete(e.key); continue; }
      const targets = [makeTarget(fmt, w, h), makeTarget(fmt, w, h)];
      if (!targets[0].ok || !targets[1].ok) warnings.push(`${e.name}: its ${fmt.name} target is incomplete`);
      targets.forEach((t) => clearFbo(t.fbo));
      if (prev) {
        const cw = Math.min(w, prev.w), ch = Math.min(h, prev.h);
        prev.targets.forEach((half, i) => {   // old half i into new half i
          gl.bindFramebuffer(GL.READ_FRAMEBUFFER, half.fbo);
          gl.bindFramebuffer(GL.DRAW_FRAMEBUFFER, targets[i].fbo);
          gl.blitFramebuffer(0, 0, cw, ch, 0, 0, cw, ch, GL.COLOR_BUFFER_BIT, GL.NEAREST);
        });
      }
      if (wantMips.has(e.key)) targets.forEach((t) => remip(GL.TEXTURE_2D, t.tex));
      buffers.set(e.key, { targets, cur: 0, w, h, mips: wantMips.has(e.key) });
    }
    for (const b of old.values()) b.targets.forEach(dropTarget);
    gl.bindFramebuffer(GL.FRAMEBUFFER, null);
  };
  const allocCube = () => {
    if (!drawn.some((e) => e.key === 'cube')) return;
    const size = Math.max(1, Math.floor(Number(opts.cubeSize) || DEFAULT_CUBE_SIZE));
    const texs = [0, 1].map(() => texCube(size, cubeFmt.internal, cubeFmt.format, cubeFmt.type, null, false));
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(GL.FRAMEBUFFER, fbo);
    for (const t of texs) {
      for (let f = 0; f < 6; f++) {
        gl.framebufferTexture2D(GL.FRAMEBUFFER, GL.COLOR_ATTACHMENT0, GL.TEXTURE_CUBE_MAP_POSITIVE_X + f, t, 0);
        if (f === 0 && gl.checkFramebufferStatus(GL.FRAMEBUFFER) !== GL.FRAMEBUFFER_COMPLETE) {
          warnings.push(`Cube A: its ${cubeFmt.name} faces are not renderable`);
        }
        gl.clearColor(0, 0, 0, 0);
        gl.clear(GL.COLOR_BUFFER_BIT);
      }
    }
    gl.bindFramebuffer(GL.FRAMEBUFFER, null);
    cube = { texs, fbo, cur: 0, size, mips: wantMips.has('cube') };
    if (cube.mips) texs.forEach((t) => remip(GL.TEXTURE_CUBE_MAP, t));
  };
  const clearTargets = () => {
    for (const b of buffers.values()) {
      b.targets.forEach((t) => clearFbo(t.fbo));
      if (b.mips) b.targets.forEach((t) => remip(GL.TEXTURE_2D, t.tex));
      b.cur = 0;
    }
    if (cube) {
      gl.bindFramebuffer(GL.FRAMEBUFFER, cube.fbo);
      for (const t of cube.texs) {
        for (let f = 0; f < 6; f++) {
          gl.framebufferTexture2D(GL.FRAMEBUFFER, GL.COLOR_ATTACHMENT0, GL.TEXTURE_CUBE_MAP_POSITIVE_X + f, t, 0);
          gl.clearColor(0, 0, 0, 0);
          gl.clear(GL.COLOR_BUFFER_BIT);
        }
      }
      if (cube.mips) cube.texs.forEach((t) => remip(GL.TEXTURE_CUBE_MAP, t));
      cube.cur = 0;
    }
    gl.bindFramebuffer(GL.FRAMEBUFFER, null);
  };
  allocBuffers();
  allocCube();

  // ---- data textures: keyboard and audio ----
  const keyboard = createKeyboardState();
  const KL = keyboardTextureLayout();
  const keyboardTex = tex2D(KL.width, KL.height, GL.R8, GL.RED, GL.UNSIGNED_BYTE, keyboard.bytes, false);
  const audioBytes = packAudioTexture(null, null);
  const audioTex = tex2D(AUDIO.width, AUDIO.height, GL.R8, GL.RED, GL.UNSIGNED_BYTE, audioBytes, false);
  let audioDirty = false;
  let audioFed = false;
  let audioMipsWanted = false;
  let keyboardMipsWanted = false;
  const setAudioBytes = (a) => {
    packAudioTexture(a && a.fft, a && a.wave, audioBytes);
    audioDirty = true;
    audioFed = !!(a && (a.fft || a.wave));
  };
  if (opts.audio) setAudioBytes(opts.audio);

  // ---- samplers ----
  const samplerCache = new Map();
  const samplerObject = (s) => {
    const key = `${s.minFilter}/${s.magFilter}/${s.wrapS}`;
    if (!samplerCache.has(key)) {
      const so = gl.createSampler();
      gl.samplerParameteri(so, GL.TEXTURE_MIN_FILTER, s.minFilter);
      gl.samplerParameteri(so, GL.TEXTURE_MAG_FILTER, s.magFilter);
      gl.samplerParameteri(so, GL.TEXTURE_WRAP_S, s.wrapS);
      gl.samplerParameteri(so, GL.TEXTURE_WRAP_T, s.wrapT);
      gl.samplerParameteri(so, GL.TEXTURE_WRAP_R, s.wrapR);
      samplerCache.set(key, so);
    }
    return samplerCache.get(key);
  };

  // ---- media: stand-in first, the real file when it arrives ----
  const media = new Map();
  const urlFor = (src) => {
    try { return typeof opts.mediaUrl === 'function' ? opts.mediaUrl(src) || null : null; } catch (e) { return null; }
  };
  const timeoutMs = Math.max(1, Number(opts.mediaTimeoutMs) || DEFAULT_OPTIONS.mediaTimeoutMs);
  const track = (p) => { pending.push(p); return p; };
  const live = () => !state.destroyed && !state.lost;

  const media2D = (src, s, kind) => {
    const key = `2d|${src}|${s.flipY}|${s.internalFormat}`;
    if (media.has(key)) return media.get(key);
    const n = standinSize(kind, src);
    const m = { target: GL.TEXTURE_2D, src, kind, w: n, h: n, d: 1, status: 'standin',
      tex: tex2D(n, n, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, standinPixels(kind, src), true) };
    const style = standinStyle(kind, src);
    media.set(key, m);
    if (kind === 'video') { substitute(src, kind, 'video playback is not supported: procedural stand-in', style); return m; }
    if (kind === 'webcam') { substitute(src || 'webcam', kind, 'no webcam: procedural stand-in', style); return m; }
    const url = urlFor(src);
    if (!url) { substitute(src, kind, 'no media url: procedural stand-in', style); return m; }
    m.status = 'loading';
    track(loadImageElement(url, timeoutMs).then((img) => {
      if (!live()) return;
      const t = gl.createTexture();
      scratch(GL.TEXTURE_2D, t);
      gl.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, s.flipY);
      gl.texImage2D(GL.TEXTURE_2D, 0, s.internalFormat, GL.RGBA, GL.UNSIGNED_BYTE, img);
      gl.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, false);
      plainParams(GL.TEXTURE_2D);
      gl.generateMipmap(GL.TEXTURE_2D);
      gl.deleteTexture(m.tex);
      Object.assign(m, { tex: t, w: img.naturalWidth || img.width, h: img.naturalHeight || img.height, status: 'loaded' });
    }).catch((err) => { m.status = 'failed'; substitute(src, kind, `${err.message}: procedural stand-in`, style); }));
    return m;
  };

  const mediaCube = (src, s) => {
    const key = `cube|${src}|${s.flipY}|${s.internalFormat}`;
    if (media.has(key)) return media.get(key);
    const N = STANDIN_CUBE_SIZE;
    const faces = proceduralEnvironment(src, N);
    const m = { target: GL.TEXTURE_CUBE_MAP, src, kind: 'cubemap', w: N, h: N, d: 1, status: 'standin',
      tex: texCube(N, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, faces, true) };
    media.set(key, m);
    const urls = cubemapFacePaths(src).map(urlFor);
    if (urls.some((u) => !u)) { substitute(src, 'cubemap', 'no media url: procedural stand-in', 'environment'); return m; }
    m.status = 'loading';
    track(Promise.all(urls.map((u, f) => loadImageElement(u, timeoutMs).catch((e) => {
      throw new Error(`face ${f} ${e.message}`);
    }))).then((imgs) => {
      if (!live()) return;
      const size = imgs[0].naturalWidth || imgs[0].width;
      if (imgs.some((im) => (im.naturalWidth || im.width) !== size || (im.naturalHeight || im.height) !== size)) {
        throw new Error('faces are not one square size');
      }
      const t = gl.createTexture();
      scratch(GL.TEXTURE_CUBE_MAP, t);
      gl.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, s.flipY);
      cubemapUploadOrder(s.flipY).forEach((image, f) => {
        gl.texImage2D(GL.TEXTURE_CUBE_MAP_POSITIVE_X + f, 0, s.internalFormat, GL.RGBA, GL.UNSIGNED_BYTE, imgs[image]);
      });
      gl.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, false);
      plainParams(GL.TEXTURE_CUBE_MAP);
      gl.generateMipmap(GL.TEXTURE_CUBE_MAP);
      gl.deleteTexture(m.tex);
      Object.assign(m, { tex: t, w: size, h: size, status: 'loaded' });
    }).catch((err) => { m.status = 'failed'; substitute(src, 'cubemap', `${err.message}: procedural stand-in`, 'environment'); }));
    return m;
  };

  // One texture per volume file, however many inputs read it and with whatever filter: so the loaded volume always
  // gets its mip chain (like media2D), and an input that samples it with the mipmap filter never finds it missing.
  const mediaVolume = (src) => {
    const key = `3d|${src}`;
    if (media.has(key)) return media.get(key);
    const N = STANDIN_VOLUME_SIZE;
    const m = { target: GL.TEXTURE_3D, src, kind: 'volume', w: N, h: N, d: N, status: 'standin',
      tex: tex3D(N, N, N, GL.RGBA8, GL.RGBA, GL.UNSIGNED_BYTE, proceduralVolume(src, N), true) };
    media.set(key, m);
    const url = urlFor(src);
    if (!url) { substitute(src, 'volume', 'no media url: procedural stand-in', 'noise'); return m; }
    m.status = 'loading';
    track(fetchArrayBuffer(url, timeoutMs).then((ab) => {
      if (!live()) return;
      const vol = parseVolumeBin(ab);
      if (vol.signature !== 'BIN') warnings.push(`${src}: volume signature "${vol.signature}" (expected "BIN"); loaded anyway`);
      const t = tex3D(vol.width, vol.height, vol.depth, vol.glInternal, vol.glFormat, vol.glType, vol.data, false);
      checkGlError(`volume ${src}`);   // an error pending from before is recorded, so the check below is the mips' own
      gl.generateMipmap(GL.TEXTURE_3D);
      if (gl.getError() !== GL.NO_ERROR) {
        warnings.push(`${src}: no mip chain for a ${vol.channels}-channel ${vol.format} volume; mipmap reads of it may be black`);
      }
      gl.deleteTexture(m.tex);
      Object.assign(m, { tex: t, w: vol.width, h: vol.height, d: vol.depth, status: 'loaded' });
    }).catch((err) => { m.status = 'failed'; substitute(src, 'volume', `${err.message}: procedural stand-in`, 'noise'); }));
    return m;
  };

  // ---- each drawn pass's four channels ----
  // A binding answers, at draw time, which texture and target a channel reads and its iChannelResolution.
  const bindingFor = (entry, input) => {
    const kind = inputKind(input);
    const s = samplerFor(input);
    const src = String(input.filepath || input.src || '');
    const base = { kind, src, sampler: samplerObject(s), desc: s };
    if (kind === 'buffer') {
      const k = bufferKeyForInput(input);
      if (!k || !drawn.some((e) => e.key === k)) {
        substitute(src || `buffer ${k}`, 'buffer', `${entry.name} reads ${k ? `Buffer ${k}` : 'a buffer'} that this shader lacks: black`);
        return { ...base, resolve: () => [GL.TEXTURE_2D, dummy[GL.TEXTURE_2D], [0, 0, 0]] };
      }
      return { ...base, resolve: () => {
        const b = buffers.get(k);
        return b ? [GL.TEXTURE_2D, b.targets[b.cur].tex, [b.w, b.h, 1]] : [GL.TEXTURE_2D, dummy[GL.TEXTURE_2D], [0, 0, 0]];
      } };
    }
    if (kind === 'cubebuffer') {
      if (!drawn.some((e) => e.key === 'cube')) {
        substitute(src || 'Cube A', 'cubebuffer', `${entry.name} reads Cube A, which this shader lacks: black`);
        return { ...base, resolve: () => [GL.TEXTURE_CUBE_MAP, dummy[GL.TEXTURE_CUBE_MAP], [0, 0, 0]] };
      }
      return { ...base, resolve: () => (cube
        ? [GL.TEXTURE_CUBE_MAP, cube.texs[cube.cur], [cube.size, cube.size, 1]]
        : [GL.TEXTURE_CUBE_MAP, dummy[GL.TEXTURE_CUBE_MAP], [0, 0, 0]]) };
    }
    if (kind === 'texture' || kind === 'video' || kind === 'webcam') {
      const m = media2D(src, s, kind);
      return { ...base, resolve: () => [m.target, m.tex, [m.w, m.h, 1]] };
    }
    if (kind === 'cubemap') {
      const m = mediaCube(src, s);
      return { ...base, resolve: () => [m.target, m.tex, [m.w, m.h, 1]] };
    }
    if (kind === 'volume') {
      const m = mediaVolume(src);
      return { ...base, resolve: () => [m.target, m.tex, [m.w, m.h, m.d]] };
    }
    if (kind === 'keyboard') {
      if (s.mipmaps) keyboardMipsWanted = true;
      return { ...base, resolve: () => [GL.TEXTURE_2D, keyboardTex, [KL.width, KL.height, 1]] };
    }
    if (kind === 'audio') {
      if (s.mipmaps) audioMipsWanted = true;
      return { ...base, audio: true, resolve: () => [GL.TEXTURE_2D, audioTex, [AUDIO.width, AUDIO.height, 1]] };
    }
    unsupported.push({ what: 'input', name: entry.name, type: input.type || input.ctype, channel: Number(input.channel),
      reason: 'unknown input type: black' });
    return { ...base, resolve: () => [GL.TEXTURE_2D, dummy[GL.TEXTURE_2D], [0, 0, 0]] };
  };
  const audioInputs = [];
  for (const e of drawn) {
    e.channels = [null, null, null, null];
    for (const input of (rp[e.index].inputs || [])) {
      const c = Number(input.channel);
      if (!(c >= 0 && c < 4)) { warnings.push(`${e.name}: input on channel ${input.channel} ignored (channels are 0-3)`); continue; }
      if (e.channels[c]) warnings.push(`${e.name}: two inputs on channel ${c}; the last one wins`);
      e.channels[c] = bindingFor(e, input);
      if (e.channels[c].audio) audioInputs.push(e.channels[c].src || String(input.type || input.ctype));
    }
  }
  if (keyboardMipsWanted) { scratch(GL.TEXTURE_2D, keyboardTex); gl.generateMipmap(GL.TEXTURE_2D); }
  if (audioMipsWanted) { scratch(GL.TEXTURE_2D, audioTex); gl.generateMipmap(GL.TEXTURE_2D); }

  const ready = Promise.all(pending.map((p) => p.catch(() => undefined))).then(() => toy);

  // ---- programs ----
  let vertexShader = null;
  const programs = new Map();
  const compileShader = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    return { shader: s, ok: !!gl.getShaderParameter(s, GL.COMPILE_STATUS), log: String(gl.getShaderInfoLog(s) || '') };
  };
  // Each pass compiles at the first parity level that works (see PARITY_LEVELS); with opts.parity false, only 'none'.
  const levels = opts.parity === false ? PARITY_LEVELS.filter((l) => l.name === 'none') : PARITY_LEVELS;
  const buildPass = (pass) => {
    let built = null;
    for (const level of levels) {
      built = buildPassAt(pass, level.shims);
      built.parity = level.name;
      if (built.ok) break;
    }
    if (!built.ok) built.parity = null;
    return built;
  };
  const buildPassAt = (pass, shims) => {
    const name = passDisplayName(pass);
    const asm = assembleSource(pass, commonCode, { hwPerformance: opts.hwPerformance, shims });
    const layout = { commonLines: asm.commonLines, passLines: asm.passLines, passName: name };
    const fs = compileShader(GL.FRAGMENT_SHADER, asm.source);
    if (!fs.ok) {
      gl.deleteShader(fs.shader);
      return { ok: false, name, asm, log: fs.log, mappedLog: mapErrorLog(fs.log, asm.headerLines, layout) };
    }
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fs.shader);
    gl.linkProgram(program);
    const linked = !!gl.getProgramParameter(program, GL.LINK_STATUS);
    const linkLog = String(gl.getProgramInfoLog(program) || '');
    gl.detachShader(program, fs.shader);
    gl.deleteShader(fs.shader);
    if (!linked) {
      gl.deleteProgram(program);
      return { ok: false, name, asm, log: linkLog, mappedLog: mapErrorLog(linkLog, asm.headerLines, layout) };
    }
    const uniforms = {};
    for (const u of UNIFORM_NAMES) uniforms[u] = gl.getUniformLocation(program, u);
    gl.useProgram(program);
    // Every channel sampler points at its own unit, so a samplerCube on 0 and an unused sampler2D can never share one.
    for (let c = 0; c < 4; c++) if (uniforms[`iChannel${c}`]) gl.uniform1i(uniforms[`iChannel${c}`], c);
    return { ok: true, name, asm, program, uniforms, log: fs.log, mappedLog: mapErrorLog(fs.log, asm.headerLines, layout) };
  };

  // ---- drawing ----
  const channelRes = new Float32Array(12);
  const bindChannels = (entry) => {
    for (let c = 0; c < 4; c++) {
      const b = entry.channels[c];
      const [target, tex, res] = b ? b.resolve() : [GL.TEXTURE_2D, dummy[GL.TEXTURE_2D], [0, 0, 0]];
      gl.activeTexture(GL.TEXTURE0 + c);
      // Bind this channel's texture on its target and nothing on the other two, so no texture a pass is writing can
      // be left bound on a channel unit from an earlier pass (WebGL2 refuses that draw as a feedback loop).
      for (const t of TARGETS) gl.bindTexture(t, t === target ? tex : null);
      gl.bindSampler(c, b ? b.sampler : null);
      channelRes[c * 3] = res[0]; channelRes[c * 3 + 1] = res[1]; channelRes[c * 3 + 2] = res[2];
    }
  };
  const setUniforms = (u, w, h, f, entry) => {
    if (u.iResolution) gl.uniform3f(u.iResolution, w, h, 1);
    if (u.iTime) gl.uniform1f(u.iTime, f.time);
    if (u.iTimeDelta) gl.uniform1f(u.iTimeDelta, f.timeDelta);
    if (u.iFrameRate) gl.uniform1f(u.iFrameRate, f.frameRate);
    if (u.iFrame) gl.uniform1i(u.iFrame, f.frame);
    if (u.iChannelTime) gl.uniform1fv(u.iChannelTime, channelTimes(rp[entry.index].inputs, f.time));
    if (u.iChannelResolution) gl.uniform3fv(u.iChannelResolution, channelRes);
    if (u.iMouse) gl.uniform4fv(u.iMouse, f.mouse);
    if (u.iDate) gl.uniform4fv(u.iDate, f.date);
    if (u.iSampleRate) gl.uniform1f(u.iSampleRate, SAMPLE_RATE);
    if (u.iBlockOffset) gl.uniform1f(u.iBlockOffset, 0);
  };
  const drawPass = (entry, f) => {
    const prog = programs.get(entry.key);
    if (!prog) return;
    gl.useProgram(prog.program);
    bindChannels(entry);
    if (entry.key === 'image') {
      gl.bindFramebuffer(GL.FRAMEBUFFER, null);
      const [w, h] = sizeNow();
      setUniforms(prog.uniforms, w, h, f, entry);
      gl.viewport(0, 0, w, h);
      gl.drawArrays(GL.TRIANGLES, 0, 3);
      return;
    }
    if (entry.key === 'cube') {
      if (!cube) return;
      const back = 1 - cube.cur;
      setUniforms(prog.uniforms, cube.size, cube.size, f, entry);
      gl.bindFramebuffer(GL.FRAMEBUFFER, cube.fbo);
      gl.viewport(0, 0, cube.size, cube.size);
      for (let face = 0; face < 6; face++) {
        gl.framebufferTexture2D(GL.FRAMEBUFFER, GL.COLOR_ATTACHMENT0, GL.TEXTURE_CUBE_MAP_POSITIVE_X + face, cube.texs[back], 0);
        const B = CUBE_FACES[face];
        if (prog.uniforms.shaderlab_faceCenter) gl.uniform3fv(prog.uniforms.shaderlab_faceCenter, B.center);
        if (prog.uniforms.shaderlab_faceRight) gl.uniform3fv(prog.uniforms.shaderlab_faceRight, B.right);
        if (prog.uniforms.shaderlab_faceUp) gl.uniform3fv(prog.uniforms.shaderlab_faceUp, B.up);
        gl.drawArrays(GL.TRIANGLES, 0, 3);
      }
      if (cube.mips) { scratch(GL.TEXTURE_CUBE_MAP, cube.texs[back]); gl.generateMipmap(GL.TEXTURE_CUBE_MAP); }
      cube.cur = back;
      return;
    }
    const b = buffers.get(entry.key);
    if (!b) return;
    const back = 1 - b.cur;
    setUniforms(prog.uniforms, b.w, b.h, f, entry);
    gl.bindFramebuffer(GL.FRAMEBUFFER, b.targets[back].fbo);
    gl.viewport(0, 0, b.w, b.h);
    gl.drawArrays(GL.TRIANGLES, 0, 3);
    if (b.mips) { scratch(GL.TEXTURE_2D, b.targets[back].tex); gl.generateMipmap(GL.TEXTURE_2D); }
    b.cur = back;
  };
  const uploadDynamic = () => {
    if (keyboard.dirty) {
      scratch(GL.TEXTURE_2D, keyboardTex);
      gl.texSubImage2D(GL.TEXTURE_2D, 0, 0, 0, KL.width, KL.height, GL.RED, GL.UNSIGNED_BYTE, keyboard.bytes);
      if (keyboardMipsWanted) gl.generateMipmap(GL.TEXTURE_2D);
      keyboard.markClean();
    }
    if (audioDirty) {
      scratch(GL.TEXTURE_2D, audioTex);
      gl.texSubImage2D(GL.TEXTURE_2D, 0, 0, 0, AUDIO.width, AUDIO.height, GL.RED, GL.UNSIGNED_BYTE, audioBytes);
      if (audioMipsWanted) gl.generateMipmap(GL.TEXTURE_2D);
      audioDirty = false;
    }
  };
  const checkGlError = (where) => {
    const err = gl.getError();
    if (err && err !== GL.NO_ERROR) state.glErrors.push({ where, frame: state.frame, error: `0x${err.toString(16)}` });
  };
  const alive = () => {
    if (state.destroyed) throw new Error('shaderlab: this toy was destroyed');
    if (state.lost || (gl.isContextLost && gl.isContextLost())) { state.lost = true; throw new Error('shaderlab: the WebGL context was lost'); }
  };
  const dateFor = (time, given) => {
    if (given !== undefined && given !== null) return dateUniform(given);
    if (opts.dateBase) { const d = dateUniform(opts.dateBase); d[3] += time; return d; }
    return dateUniform(new Date());
  };

  const toy = {
    api: API,
    gl,
    canvas,
    /** True when a frame reads an earlier frame (a feedback buffer): its stills need the walk from a reset. */
    history,
    get ready() { return ready; },
    load() { return ready; },
    info() { return { ...info, caps: { ...caps }, bufferFormat: fmt.name, cubeFormat: cube ? cubeFmt.name : null, history }; },

    /** Compile every pass (Common prepended), all or nothing: the new programs replace the old ones only when every
     *  drawn pass linked, so a frame never mixes a new Buffer A with an old Image; otherwise every pass keeps the
     *  program it had. ok: every pass compiled; drawable: every drawn pass (all but Sound) compiled. */
    compile() {
      alive();
      if (!vertexShader) {
        const vs = compileShader(GL.VERTEX_SHADER, VERTEX_SOURCE);
        if (!vs.ok) throw new Error(`shaderlab: the fullscreen vertex shader failed: ${vs.log}`);
        vertexShader = vs.shader;
      }
      const passes = [];
      const out = { ok: true, drawable: true, passes, warnings: [] };
      const fresh = new Map();   // key -> built pass, committed after the loop only if every drawn pass linked
      for (const pass of rp) {
        const key = passKey(pass);
        if (!key || key === 'common') continue;
        if (key !== 'sound' && !drawn.some((e) => e.key === key && rp[e.index] === pass)) continue;   // a duplicate
        const built = buildPass(pass);
        const errors = parseErrorLog(built.mappedLog).filter((r) => r.severity === 'ERROR');
        passes.push({
          name: built.name, type: pass.type, key, ok: built.ok, log: built.log, mappedLog: built.mappedLog,
          firstError: built.ok ? null : (errors[0] ? `${errors[0].section}:${errors[0].line}: ${errors[0].message}` : (built.log.split('\n')[0] || 'failed')),
          lines: built.asm.passLines, parity: built.parity,
        });
        if (built.ok && built.parity !== levels[0].name) {
          out.warnings.push(`${built.name}: compiled at parity level "${built.parity}" (a GPU-parity shim did not compile here, `
            + 'typically min, max or tanh in a const initializer); SwiftShader\'s own answers apply to what the missing shims cover');
        }
        if (!built.ok) {
          out.ok = false;
          if (key !== 'sound') out.drawable = false;
          else out.warnings.push('the Sound pass failed to compile (it is never played; the picture is unaffected)');
          continue;
        }
        if (key === 'sound') { gl.deleteProgram(built.program); continue; }   // compile-only
        fresh.set(key, built);
      }
      if (!drawn.some((e) => e.key === 'image')) {
        out.ok = false; out.drawable = false; out.warnings.push('this shader has no Image pass');
      }
      if (out.drawable) {
        for (const [key, built] of fresh) {
          const old = programs.get(key);
          if (old) gl.deleteProgram(old.program);
          programs.set(key, built);
        }
      } else {
        for (const built of fresh.values()) gl.deleteProgram(built.program);
        if (programs.size) out.warnings.push('a drawn pass failed, so no pass was replaced: every pass keeps its previous program');
      }
      out.warnings.push(...warnings);
      checkGlError('compile');
      state.compiled = out;
      return out;
    },

    /** Draw one frame: every buffer in saved order, Cube A, then Image. {time, frame, timeDelta, frameRate, mouse,
     *  date}; unset fields continue from the last frame (frame + 1, the same time, timeDelta since the last frame,
     *  iFrameRate 1 / timeDelta, the last mouse with its click consumed). mouse is a state for mouseUniform
     *  ({x, y, clickX, clickY, down, clicked}) or a ready iMouse vec4; either way its click (w > 0) lasts this frame. */
    render(args = {}) {
      alive();
      if (!state.compiled) toy.compile();
      const frame = Number.isFinite(args.frame) ? Math.floor(args.frame) : state.frame;
      const time = Number.isFinite(args.time) ? args.time : state.time;
      let timeDelta = Number.isFinite(args.timeDelta) ? args.timeDelta
        : (state.lastTime === null ? 1 / (Number(opts.fps) || DEFAULT_FPS) : time - state.lastTime);
      if (!(timeDelta >= 0)) timeDelta = 0;
      const mouse = mouseVec(args.mouse) || state.mouse;
      const frameRate = Number(args.frameRate) > 0 ? Number(args.frameRate)
        : (timeDelta > 0 ? 1 / timeDelta : (Number(opts.fps) || DEFAULT_FPS));
      const f = { frame, time, timeDelta, mouse, date: dateFor(time, args.date), frameRate };
      uploadDynamic();
      for (const entry of drawn) drawPass(entry, f);
      state.mouse = mouseAfterFrame(mouse);
      state.frame = frame + 1;
      state.time = time;
      state.lastTime = time;
      state.framesRendered++;
      keyboard.endFrame();
      if (state.framesRendered <= GL_ERROR_CHECK_FRAMES) checkGlError('render');
      return { frame, time };
    },

    /** Step frames at a fixed dt (1 / fps) from the current frame up to toTime, ending exactly on toTime (see
     *  advanceSchedule). {fps, maxFrames, mouse, date}. iFrameRate is the walk's nominal fps on every frame, the
     *  shorter last step included. o.mouse is the mouse at the first frame this call draws; later frames continue
     *  from it with its click consumed. Returns {frames, frame, time, reached, behind}: reached is false only when
     *  maxFrames cut the walk short -- call again to continue. behind: already past toTime (reset). */
    advance(toTime, o = {}) {
      alive();
      const fps = Number(o.fps) > 0 ? Number(o.fps) : (Number(opts.fps) || DEFAULT_FPS);
      const maxFrames = Number.isFinite(o.maxFrames) ? Math.max(0, Math.floor(o.maxFrames)) : Infinity;
      const steps = advanceSchedule(state.frame, state.lastTime, toTime, fps, maxFrames);
      steps.forEach((s, i) => toy.render({ frame: s.frame, time: s.time, timeDelta: s.timeDelta, frameRate: fps,
        mouse: i === 0 ? o.mouse : undefined, date: o.date }));
      const target = onFrameGrid(toTime, fps) ? Math.round(toTime * fps) / fps : Number(toTime);
      const at = state.lastTime !== null && state.lastTime >= target - TIME_EPS;
      return {
        frames: steps.length, frame: state.frame, time: state.time,
        reached: steps.length ? steps[steps.length - 1].final : at,
        behind: state.lastTime !== null && state.lastTime > target + TIME_EPS,
      };
    },

    /** Draw only the frame advance() would end on when walking from a reset to toTime (jumpStep), for a shader with
     *  no history: its pixels then equal the walk's, at the cost of one frame instead of t * fps. {fps, mouse, date}:
     *  the same uniforms as that frame, so iFrameRate is fps and a click in o.mouse is already consumed unless the
     *  walk is the single frame 0. Throws for a shader whose frames read earlier frames (toy.history): a jump there
     *  would be a different picture. */
    jump(toTime, o = {}) {
      alive();
      if (history) throw new Error('shaderlab: this shader reads earlier frames (a feedback buffer); walk to t with advance()');
      const fps = Number(o.fps) > 0 ? Number(o.fps) : (Number(opts.fps) || DEFAULT_FPS);
      const s = jumpStep(toTime, fps);
      if (!s) throw new Error(`shaderlab: cannot jump to t=${toTime}`);
      const given = mouseVec(o.mouse);
      const mouse = given && s.frame > 0 ? mouseAfterFrame(given) : (given || undefined);
      toy.render({ frame: s.frame, time: s.time, timeDelta: s.timeDelta, frameRate: fps, mouse, date: o.date });
      return { frames: 1, frame: s.frame, time: s.time, timeDelta: s.timeDelta };
    },

    /** Clear every buffer and Cube A (both ping-pong halves), the keyboard, and the clock: frame 0, no history. */
    reset() {
      alive();
      clearTargets();
      keyboard.clear();
      state.frame = 0; state.time = 0; state.lastTime = null; state.mouse = [0, 0, 0, 0];
    },

    /** Feed the audio texture: fft in 0..1, wave in -1..1 (Float32Array or array; null = silence). */
    setAudio(a) { setAudioBytes(a || null); },

    setKeyboard(keyCode, down) { keyboard.set(keyCode, !!down); },

    /** Resize the canvas to w x h CSS pixels times pixelRatio. Each buffer whose size changes keeps its pixels where
     *  the old and new sizes overlap (bottom-left, texel for texel; 0 elsewhere) and restarts its ping-pong on half 0,
     *  as Shadertoy does; a buffer already at that size is untouched. Cube A has a fixed size and is untouched. */
    resize(w, h) {
      alive();
      const pr = Number(opts.pixelRatio) > 0 ? Number(opts.pixelRatio) : 1;
      canvas.width = Math.max(1, Math.round(w * pr));
      canvas.height = Math.max(1, Math.round(h * pr));
      allocBuffers();
    },

    stats() {
      const sub = [...substituted.values()];
      if (!audioFed) for (const src of new Set(audioInputs)) sub.push({ src, kind: 'audio', reason: 'no audio fed: silence' });
      return {
        api: API, frame: state.frame, time: state.time, framesRendered: state.framesRendered,
        passes: (state.compiled ? state.compiled.passes : []).map((p) => ({ name: p.name, type: p.type, key: p.key, ok: p.ok })),
        order: drawn.map((e) => e.key), history,
        reads: drawn.map((e) => ({ key: e.key, reads: e.reads })),
        substituted: sub, unsupported: unsupported.slice(),
        loading: [...media.values()].filter((m) => m.status === 'loading').length,
        bufferFormat: needTargets ? fmt.name : null, cubeSize: cube ? cube.size : null,
        renderer: info.renderer, warnings: warnings.slice(), glErrors: state.glErrors.slice(), lost: state.lost,
      };
    },

    destroy() {
      if (state.destroyed) return;
      state.destroyed = true;
      try {
        for (const p of programs.values()) gl.deleteProgram(p.program);
        if (vertexShader) gl.deleteShader(vertexShader);
        for (const b of buffers.values()) b.targets.forEach(dropTarget);
        if (cube) { cube.texs.forEach((t) => gl.deleteTexture(t)); gl.deleteFramebuffer(cube.fbo); }
        for (const m of media.values()) gl.deleteTexture(m.tex);
        for (const t of Object.values(dummy)) gl.deleteTexture(t);
        gl.deleteTexture(keyboardTex);
        gl.deleteTexture(audioTex);
        for (const s of samplerCache.values()) gl.deleteSampler(s);
        gl.deleteVertexArray(vao);
        if (opts.loseContextOnDestroy) {
          const ext = gl.getExtension('WEBGL_lose_context');
          if (ext) ext.loseContext();
        }
      } catch (e) { /* a lost context has nothing left to free */ }
    },
  };
  return toy;
}
