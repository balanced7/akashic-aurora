// arsenal/web/edit/api.js
// The editor's door to the server: one function per /api/edit route of the EDITOR v0 CONTRACT
// (arsenal/media/editapi.py answers them). Paths are root-relative so the page works on any port.
//
// Failures come back as ApiError with the server's own words: a 503 means the primitive behind the route is not
// built yet ("<module> not built yet"), and the panels say exactly that instead of pretending to work.

export class ApiError extends Error {
  constructor(status, body, path) {
    const msg = (body && (body.error || body.message)) || `HTTP ${status}`;
    super(msg);
    this.status = status;
    this.body = body || {};
    this.path = path;
  }
  get notBuilt() { return this.status === 503; }
}

const enc = encodeURIComponent;

async function call(method, path, body, { allow = [], keepalive = false } = {}) {
  const init = { method, cache: "no-store", headers: {}, keepalive };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, init);
  } catch (err) {
    throw new ApiError(0, { error: `the server did not answer (${err && err.message ? err.message : err})` }, path);
  }
  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch (_) { data = { error: text.slice(0, 200) }; }
  }
  if (res.ok || allow.includes(res.status)) return { status: res.status, data: data || {} };
  throw new ApiError(res.status, data, path);
}

const get = async (path) => (await call("GET", path)).data;

// ------------------------------------------------------------------ media --

/** A dropped File: the server finds the real file by name + size (+ mtime) under its library roots; nothing uploads. */
export async function importDropped(file) {
  return (await call("POST", "/api/edit/import", {
    name: file.name, size: file.size, lastModified: file.lastModified,
  })).data;
}

export async function importPath(path) {
  return (await call("POST", "/api/edit/import", { path })).data;
}

export const listMedia = () => get("/api/edit/media");
export const media = (mid) => get(`/api/edit/media/${enc(mid)}`);
export const peaks = (mid, n) => get(`/api/edit/media/${enc(mid)}/peaks/${n}`);
export const shots = (mid) => get(`/api/edit/media/${enc(mid)}/shots`);
export const keyframes = (mid) => get(`/api/edit/media/${enc(mid)}/keyframes`);
export const cutplan = (mid, start, end) =>
  get(`/api/edit/media/${enc(mid)}/cutplan?start=${start.toFixed(6)}&end=${end.toFixed(6)}`);

export const videoUrl = (mid) => `/api/edit/media/${enc(mid)}/video`;
export const audioUrl = (mid, n) => `/api/edit/media/${enc(mid)}/audio/${n}`;

// --------------------------------------------------------------- projects --

export const listProjects = () => get("/api/edit/projects");
export const project = (pid) => get(`/api/edit/projects/${enc(pid)}`);
export async function createProject(name) {
  return (await call("POST", "/api/edit/projects", { name })).data;
}

/**
 * PUT the document at the revision the page last saw. 200 -> {ok: true, project} (rev + 1);
 * 409 -> {ok: false, project}: someone else wrote first, and this is their copy.
 * keepalive lets the request outlive a closing tab (browsers cap such bodies at 64 KB).
 */
export async function saveProject(pid, doc, { keepalive = false } = {}) {
  const r = await call("PUT", `/api/edit/projects/${enc(pid)}`, { project: doc }, { allow: [409], keepalive });
  return { ok: r.status !== 409, project: r.data.project || null, error: r.data.error || null };
}

// ----------------------------------------------------------------- render --

export async function render(pid, preset, out) {
  const body = { preset };
  if (out) body.out = out;
  return (await call("POST", `/api/edit/projects/${enc(pid)}/render`, body)).data;
}

export const job = (jid) => get(`/api/edit/jobs/${enc(jid)}`);
export const presets = () => get("/api/edit/presets");
