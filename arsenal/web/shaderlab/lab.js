// arsenal/web/shaderlab/lab.js -- mounts the Workbench (arsenal/web/lib/workbench/) as the Shader Lab page.
//
// WHY SO SMALL. Everything the lab does lives in the shared panels, so the bench, the Studio and First Light can mount
// the same Workbench by passing their own routes; this file only says where the lab server keeps things (the default
// route table already is the lab's: `py -m arsenal shader serve`, 127.0.0.1:8797) and reports the page's state on
// window.__lab for a headless screenshot.
//
// The Workbench is imported dynamically, not statically, so a missing /webl/ route becomes a sentence on the page
// (window.__labBootFail, defined in index.html) rather than a blank screen.
//
// On load this reads data only. Live runs are off until their safety review clears: the lab is view only (SwiftShader
// stills and filmstrips, no Run button) unless the one switch is set by hand, in this browser, on purpose: ?live=1 in
// the address AND localStorage 'arsenal.shaderlab.live' = 'on' (README.md, "Live runs: off until a deliberate local
// setting"). Only then is the shader runtime (toy-runtime.js) imported, by the Stage, when "Run live on this GPU" is
// pressed (build-spec-reconciled.md ruling 5). window.__lab.live says which it is, for the screenshot driver.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13).
const R = window.__lab || (window.__lab = { ready: false, error: null, stage: 'boot' });
R.stage = 'mounting';

const WORKBENCH = '/webl/workbench/workbench.js';

(async () => {
  let mod;
  try {
    mod = await import(WORKBENCH);
  } catch (e) {
    window.__labBootFail(`${WORKBENCH} could not be loaded (${(e && e.message) || e})`);
    return;
  }
  try {
    const root = document.getElementById('lab');
    const wb = await mod.mountWorkbench(document, root, {});
    R.live = wb.stage.live === true;   // the switch as the Stage read it: false means view only
    R.stage = 'loading data';
    const facts = await wb.ready;
    Object.assign(R, { ready: true, stage: 'ready', facts });
    window.__wb = wb;   // for a person poking at the page from the console; nothing else reads it
  } catch (e) {
    R.stage = 'failed';
    window.__labBootFail(`the Workbench failed while mounting (${(e && e.message) || e})`);
  }
})();
