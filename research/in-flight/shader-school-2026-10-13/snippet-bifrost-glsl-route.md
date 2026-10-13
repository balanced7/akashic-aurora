# Snippet for Heimdall: serve the shared shader composer from the Bifrost console (`/glsl/` and `/vfx-codegen.js`)

**From:** the S5 slice of the shader school (2026-10-13), for Vandor to hand to Heimdall. **For:** `scripts/bifrost_ui.py`,
which DeepSeek owns; nobody else edits it, so this page is the whole change, ready to paste.

## Why

The VFX bench (`/vfx`, `scripts/vfx.html`) now writes its GLSL through the house module composer
(`arsenal/web/glsl/modlib.js`) via a new ES module, `scripts/vfx-codegen.js`. The page imports both at run time:

```js
import('/vfx-codegen.js')      // scripts/vfx-codegen.js
import('/glsl/modlib.js')      // arsenal/web/glsl/modlib.js
```

The console serves neither path today, so on :8787 the import fails, the bench keeps its legacy writers, and its status
line (left card, under the subject note) says so and names this page. Nothing breaks without the routes; with them, the
shared composer turns on. In hardware terms: the new board is already in the rack and wired; this is the power lead.

What changes for Daniel once mounted: **no pixel changes.** The bench checks every build against the legacy writer,
byte for byte, and ships the legacy text whenever they differ (`tests/vfx_codegen_parity.test.mjs` proves it over every
chunk, group, saved chain, saved graph and 600 graphs built by the page's own editing code). The one declared difference,
the mask-port fix (a mask wire feeds a blend's `m`, and every block with a colB declares a default `m` in the Graph
card and in blend tiles), is also pixel-identical with the shipped chunks; it is described in the header of
`scripts/vfx-codegen.js`.

## The change (two pieces)

### 1. A pure route function, at module level (beside `_vfx_chunks_read`, for example)

It mirrors `safe_file` in `arsenal/shaders/serve.py` (the shader lab's server, which already serves this folder at
`/glsl/` on 127.0.0.1:8797), so both servers refuse the same paths. It is a pure function so a pytest can pin it without
a socket.

```python
GLSL_ROOT = os.path.join(REPO, "arsenal", "web", "glsl")
GLSL_TYPES = {".js": "application/javascript", ".json": "application/json", ".glsl": "text/plain; charset=utf-8"}


def _glsl_route(path):
    """/glsl/<rel> -> (repo-relative path, mime) for a file under arsenal/web/glsl/, or None.

    Read-only (GET only, nothing here writes). Same refusals as arsenal/shaders/serve.py safe_file: the rest is
    percent-decoded once; any empty, "." or ".." segment, a backslash, a colon (a Windows drive or stream) or a NUL is
    refused; the resolved path (links followed) must still lie inside the folder; only .js, .json and .glsl are served
    (modlib.js, index.json, the modules), so a README or a stray file is a 404, not a download. A link that resolves
    onto another drive is a 404 too: os.path.commonpath raises ValueError for paths on two drives."""
    from urllib.parse import unquote
    if not path.startswith("/glsl/"):
        return None
    rel = unquote(path[len("/glsl/"):])
    if not rel or "\\" in rel or ":" in rel or "\x00" in rel or rel.startswith("/"):
        return None
    if any(p in ("", ".", "..") for p in rel.split("/")):
        return None
    mime = GLSL_TYPES.get(os.path.splitext(rel)[1].lower())
    if mime is None:
        return None
    base = os.path.realpath(GLSL_ROOT)
    full = os.path.realpath(os.path.join(base, *rel.split("/")))
    try:
        inside = os.path.commonpath([base, full]) == base
    except ValueError:           # the two paths are on different drives: outside, by definition
        return None
    if not inside or not os.path.isfile(full):
        return None
    return os.path.relpath(full, REPO).replace(os.sep, "/"), mime
```

### 2. Two routes in `Handler.do_GET`, beside the other static modules (after `/activity-line.js`, before `/vfx`)

```python
        if path == "/vfx-codegen.js":
            return self._static("scripts/vfx-codegen.js", "application/javascript")
        if path.startswith("/glsl/"):
            hit = _glsl_route(path)
            return self._static(*hit) if hit else self.send_error(404)
```

`_static` already sends the no-cache headers the console uses for live-edited assets, which matters here: a module
edit must reach the page on the next reload.

## Exposure

The console binds 127.0.0.1 by default (`--host`, `bifrost_ui.py:1629`), the same exposure as the shader lab's server,
which serves this folder today. Note for the future: the library may hold `legacy/` twins marked `"public": false`
(corpus ancestry, build-spec ruling 2). If the console is ever bound off loopback, this route should skip any module
whose header says `"public": false`, the way the lab keeps its study notes loopback-only.

## A pin to add with it (proposed: `tests/test_bifrost_glsl_route.py`)

```python
"""The console serves the shared shader composer read-only at /glsl/ (and the bench's codegen at /vfx-codegen.js).

Without these routes the VFX bench falls back to its legacy GLSL writers (and says so on its status line), so a
route that quietly 404s is a bench that quietly stopped using the shared composer."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import bifrost_ui as B


def test_serves_the_composer_and_its_index():
    assert B._glsl_route("/glsl/modlib.js") == ("arsenal/web/glsl/modlib.js", "application/javascript")
    assert B._glsl_route("/glsl/index.json") == ("arsenal/web/glsl/index.json", "application/json")


def test_refuses_traversal_odd_paths_and_unlisted_types():
    for p in ["/glsl/", "/glsl/../scripts/bifrost_ui.py", "/glsl/%2e%2e/scripts/bifrost_ui.py",
              "/glsl//modlib.js", "/glsl/./modlib.js", "/glsl/a\\b.js", "/glsl/C:modlib.js",
              "/glsl/modlib.js%00", "/glsl/README.md", "/glsl/no-such-module.glsl", "/lib/modlib.js"]:
        assert B._glsl_route(p) is None, p


def test_a_link_onto_another_drive_is_a_404_not_a_500(monkeypatch):
    # os.path.commonpath raises ValueError for two drives (a junction inside the folder pointing at D:\, say)
    def two_drives(paths):
        raise ValueError("Paths don't have the same drive")
    monkeypatch.setattr(os.path, "commonpath", two_drives)
    assert B._glsl_route("/glsl/modlib.js") is None


def test_the_codegen_module_exists_where_the_route_points():
    assert os.path.isfile(os.path.join(REPO, "scripts", "vfx-codegen.js"))
```

## How to see it worked (no GPU needed)

1. Restart the console the house way, then `curl -s http://127.0.0.1:8787/glsl/modlib.js | head -1` prints the
   modlib header line, and `curl -s -o NUL -w "%{http_code}" http://127.0.0.1:8787/glsl/../scripts/bifrost_ui.py`
   prints 404.
2. Daniel's open bench tab, after a reload: the status line under the subject note reads
   `codegen: modlib — the shared composer ... writes the GLSL; every build is checked byte for byte ...`.
   `?codegen=legacy` on the URL turns it back off without touching the server.
3. `node tests/vfx_codegen_parity.test.mjs` stays green (it does not need the server).
