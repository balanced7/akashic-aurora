// Put the KeyLab on the page you are on: arsenal/web/lib/keylab-mount.js. Importing it mounts once (idempotent) and
// leaves the handle on window.__keylab. It finds the page by what the page already exposes (lib/keylab-hosts.js):
// Play (window.__play + its macro rack), the VFX Bench (AgentAvatar + av), or any page of sliders (the Shader Lab's
// Inspector, a params-ui panel).
//
// Three ways in, none of which edits the page:
//   Play, the arsenal server     open http://127.0.0.1:8793/web/keylab-play.html (Play in a frame, the panel beside it)
//   any page on the arsenal server (8793), in the DevTools console:   import("/web/lib/keylab-mount.js")
//   the Shader Lab (8797), in the DevTools console:                    import("/webl/keylab-mount.js")
//   the VFX Bench (8787)          needs the two-line hook in arsenal/keylab/webmount.py (the Bifrost console does not
//                                 serve arsenal/web/lib/ yet; the hook is DeepSeek's to apply to scripts/bifrost_ui.py,
//                                 plus one <script> line in scripts/vfx.html)
//
// ?keylab=<events url> on the page overrides the engine address; ?keylab=midi reads the KeyLab over Web MIDI only.
import { mountKeyLab } from "./keylab-hosts.js";

// A page's own objects come up in its own time: the bench makes `av` in its init, Play installs __play once its rack
// is built. Wait for the page that is clearly coming (up to 10 s) rather than mounting on the wrong host.
async function pageReady() {
  if (document.readyState !== "complete") await new Promise((res) => window.addEventListener("load", res, { once: true }));
  for (let i = 0; i < 100; i++) {
    const bench = !!window.AgentAvatar, play = !!document.getElementById("macro-list");
    if (bench && window.av && window.av.prog) return;
    if (play && window.__play && document.querySelector("input.macro-range")) return;
    if (!bench && !play) return;
    await new Promise((res) => setTimeout(res, 100));
  }
}

if (!window.__keylab) {
  window.__keylab = { pending: true };
  try {
    await pageReady();
    window.__keylab = mountKeyLab();
    console.info(`[keylab] mounted on this page as "${window.__keylab.kind}"`);
  } catch (err) {
    window.__keylab = null;
    console.error("[keylab] could not mount:", err);
  }
}
export default window.__keylab;
