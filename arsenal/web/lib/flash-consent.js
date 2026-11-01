// arsenal/web/lib/flash-consent.js -- THE FLASH PROTECTION CHOICE for the show pages (the Stage, the VJ page).
// Tests: tests/stage_flash_consent.test.mjs.
//
// WHY. Daniel, 2026-10-28, on the Stage's flash limiter: "it freezes the render though, those blocks stall, can we remove
// or tweak the system?" and then "we can build it for the website version and have it be a toggle, as it should be, you
// get a siezure warning and its up to you what you do with it, default is on, on the warning you can uncheck it, problem
// solved and i get my full visuals". On the wording: "dont add reccomended, i did not ask for that, i will not insult
// our users intelligence". And: "no flash protection off nag screen".
//
// WHAT. Before the show starts, on a viewer's first visit, one screen: the warning, ONE checkbox "Flash protection"
// (checked), and Start. Nothing else: no "(recommended)", no second confirmation, no reminder afterwards. The choice is
// remembered in this browser (localStorage, one key for every show page; the page works the same without storage, it
// then asks again next visit). The pages offer a quiet "Flash protection" checkbox in their HUD (and the VJ page's
// Options panel) for a viewer who wants to change it later; nothing ever comes to the viewer on its own.
//
// THE ORDER OF THE CHOICE (resolveChoice):
//   ?flash=on | off     the URL decides, no screen, nothing stored (tests, kiosks)
//   ?flash=ask          the screen, always (its box as remembered, else checked)
//   automation          a browser driven by automation (navigator.webdriver: the house's headless lanes, every receipt)
//                       gets protection ON and no screen, so every existing lane runs exactly as before
//   remembered          the viewer's earlier choice in this browser, no screen
//   first visit         the screen, its box checked
//
// The page holds the show until the choice is made (ready); `on` is what the final-frame limiter obeys. When it is off,
// the limiter does not touch the frame at all.

export const FLASH_CONSENT_API = "arsenal.flash-consent/v1";
export const STORE_KEY = "arsenal.flashProtection";      // "on" | "off"

// The wording, in one place (the report quotes it from here).
export const WORDING = Object.freeze({
  title: "Photosensitivity warning",
  body: "This show contains flashing lights and patterns that may trigger seizures in people with photosensitive epilepsy.",
  box: "Flash protection",
  hint: "Limits the show to three flashes a second.",
  start: "Start",
});

// The pure decision. param: the ?flash= value (or null); stored: "on" | "off" | null; automated: navigator.webdriver.
export function resolveChoice({ param = null, stored = null, automated = false } = {}) {
  const p = typeof param === "string" ? param.trim().toLowerCase() : null;
  const remembered = stored === "on" ? true : stored === "off" ? false : null;
  if (p === "on" || p === "1") return { on: true, show: false, source: "url" };
  if (p === "off" || p === "0") return { on: false, show: false, source: "url" };
  if (p === "ask") return { on: remembered ?? true, show: true, source: "url" };
  if (automated) return { on: true, show: false, source: "automation" };
  if (remembered !== null) return { on: remembered, show: false, source: "stored" };
  return { on: true, show: true, source: "first-visit" };
}

function defaultStorage() {
  return {
    get() { try { return localStorage.getItem(STORE_KEY); } catch { return null; } },
    set(v) { try { localStorage.setItem(STORE_KEY, v); return true; } catch { return false; } },
  };
}

// The controller a page keeps. flashProtection({ page }) reads the URL, the storage and the browser, shows the screen
// when it must, and returns { on, source, ready, set(on), onChange(fn) }. ready resolves (to `on`) once the choice is
// made: at once, unless the screen is up.
export function flashProtection({ page = "show", search = (typeof location !== "undefined" ? location.search : ""),
                                  storage = defaultStorage(),
                                  automated = (typeof navigator !== "undefined" && navigator.webdriver === true),
                                  doc = (typeof document !== "undefined" ? document : null) } = {}) {
  let param = null;
  try { param = new URLSearchParams(search).get("flash"); } catch { param = null; }
  const first = resolveChoice({ param, stored: storage.get(), automated });
  const listeners = [];
  const ctl = {
    api: FLASH_CONSENT_API, page, on: first.on, source: first.source, shown: false, ready: null,
    // the quiet setting (the HUD's checkbox): the viewer's own change, remembered
    set(on, { remember = true } = {}) {
      const v = !!on;
      if (remember) storage.set(v ? "on" : "off");
      if (v === ctl.on) return v;
      ctl.on = v;
      ctl.source = "setting";
      for (const fn of listeners) { try { fn(v); } catch (e) { console.error(e); } }
      return v;
    },
    onChange(fn) { listeners.push(fn); return () => { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); }; },
  };
  if (!first.show || !doc) { ctl.ready = Promise.resolve(ctl.on); return ctl; }
  ctl.shown = true;
  ctl.ready = showWarning(doc, { checked: first.on, page }).then((on) => {
    storage.set(on ? "on" : "off");
    ctl.on = on;
    ctl.source = "screen";
    return on;
  });
  return ctl;
}

// ------------------------------------------------------------------------------------------------- the screen --
const CSS = `
.fc-veil { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center;
  padding: max(16px, env(safe-area-inset-top, 0px)) max(16px, env(safe-area-inset-right, 0px))
           max(16px, env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px));
  background: #050608; color: #e8ecf4; overflow-y: auto; -webkit-overflow-scrolling: touch;
  font: 15px/1.5 "Archivo", system-ui, "Segoe UI", sans-serif; }
.fc-card { width: min(34rem, 100%); max-height: 100%; margin: auto; padding: 22px 24px 20px;
  border: 1px solid rgba(160, 175, 210, 0.22); border-radius: 12px; background: #0b0d14; }
.fc-card h1 { margin: 0 0 8px; font-size: 19px; font-weight: 800; font-stretch: 108%; letter-spacing: 0.01em; }
.fc-card p { margin: 0 0 14px; color: #c9d0dd; }
.fc-check { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 4px 0; cursor: pointer;
  font-weight: 700; font-size: 16px; -webkit-tap-highlight-color: transparent; }
.fc-check input { width: 22px; height: 22px; margin: 0; flex: none; accent-color: #9a7cff; cursor: pointer; }
.fc-hint { margin: 0 0 16px 34px !important; font-size: 13px; color: #8f98ab !important; }
.fc-start { display: block; min-width: 132px; min-height: 46px; padding: 0 22px; border-radius: 10px; cursor: pointer;
  border: 1px solid #9a7cff; background: #9a7cff; color: #0b0614; font: 800 16px/1 "Archivo", system-ui, sans-serif;
  letter-spacing: 0.02em; -webkit-tap-highlight-color: transparent; }
.fc-start:focus-visible, .fc-check input:focus-visible { outline: 2px solid #e8ecf4; outline-offset: 3px; }
@media (max-height: 420px) {
  .fc-card { padding: 14px 18px 14px; }
  .fc-card h1 { margin-bottom: 4px; font-size: 17px; }
  .fc-card p { margin-bottom: 8px; }
  .fc-hint { margin-bottom: 10px !important; }
}
`;

// The warning screen. Resolves to the box's state when Start is pressed. While it is up, the page's own keys and the pad
// bar's keys do not reach the show (the screen's own controls still take Tab, Space and Enter).
export function showWarning(doc, { checked = true, page = "show" } = {}) {
  return new Promise((resolve) => {
    const mount = () => {
      const style = doc.createElement("style");
      style.textContent = CSS;
      doc.head.appendChild(style);
      const veil = doc.createElement("div");
      veil.className = "fc-veil";
      veil.id = "flash-consent";
      veil.dataset.page = page;
      veil.setAttribute("role", "dialog");
      veil.setAttribute("aria-modal", "true");
      veil.setAttribute("aria-labelledby", "fc-title");
      veil.setAttribute("aria-describedby", "fc-body");
      const card = doc.createElement("div");
      card.className = "fc-card";
      const h = doc.createElement("h1"); h.id = "fc-title"; h.textContent = WORDING.title;
      const p = doc.createElement("p"); p.id = "fc-body"; p.textContent = WORDING.body;
      const label = doc.createElement("label"); label.className = "fc-check";
      const box = doc.createElement("input"); box.type = "checkbox"; box.id = "fc-protect"; box.checked = !!checked;
      label.append(box, doc.createTextNode(WORDING.box));
      const hint = doc.createElement("p"); hint.className = "fc-hint"; hint.textContent = WORDING.hint;
      const start = doc.createElement("button"); start.type = "button"; start.className = "fc-start"; start.id = "fc-start";
      start.textContent = WORDING.start;
      card.append(h, p, label, hint, start);
      veil.appendChild(card);
      // the show's keys wait (window listeners, the pad bar's synthetic keys): stopped in the capture phase, so the
      // screen's own defaults (Tab, Space on the box, Enter on Start) still happen
      const win = doc.defaultView;
      const hold = (e) => { e.stopImmediatePropagation(); };
      for (const t of ["keydown", "keyup", "keypress"]) win.addEventListener(t, hold, true);
      start.addEventListener("click", () => {
        for (const t of ["keydown", "keyup", "keypress"]) win.removeEventListener(t, hold, true);
        const on = box.checked;
        veil.remove();
        style.remove();
        resolve(on);
      });
      doc.body.appendChild(veil);
      try { start.focus({ preventScroll: true }); } catch { /* no focus: a click still starts */ }
    };
    if (doc.body) mount(); else doc.addEventListener("DOMContentLoaded", mount, { once: true });
  });
}

// The quiet setting: a "Flash protection" checkbox for a page's HUD or panel, kept in step with the controller.
export function protectionCheckbox(doc, ctl, { id = "opt-flash", className = "" } = {}) {
  const label = doc.createElement("label");
  if (className) label.className = className;
  const box = doc.createElement("input");
  box.type = "checkbox"; box.id = id; box.checked = ctl.on;
  box.addEventListener("change", () => ctl.set(box.checked));
  ctl.onChange((on) => { box.checked = on; });
  label.append(box, doc.createTextNode(` ${WORDING.box}`));
  return label;
}
