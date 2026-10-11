// Piano: reorder a list by a drag handle (studio/reorder.js). One component for every list of presets on the page: the
// camera presets and the instrument cards (workbench.js) and the saved looks (studio.js). No dependencies and no CSS of its
// own beyond inline transforms; each page styles its handles (.rr-handle; studio.css holds the shared base).
//
//   const r = makeReorderable(listEl, { item: ".camera-row", onReorder: (ids, { id, from, to, via }) => save(ids) });
//   -> { dragging(), destroy() }
//
// Rows are the list's direct children matching `item`; a row's handle is the .rr-handle button inside it (handleHtml()
// draws one). The caller renders the rows and may re-render them whenever it likes between drags: every listener is
// delegated to the list and rows are found again by key (data-id) after a move, so a list rebuilt with innerHTML keeps
// working. Rows other than `item` (a starter look, a heading) never move and nothing moves past them.
//
// Pointer (mouse, pen, touch): press a handle and move 4 px to lift the row. It follows the pointer (up and down only, in a
// one-column list) while the others slide out of its way (transforms only: nothing in the DOM moves until the drop), and
// the list's scroll box scrolls when the pointer nears its edge. Releasing drops it; Escape, a cancelled pointer or the window losing focus puts it back. A
// one-column list makes room by the lifted row's own height, so rows of any height work; a grid (the two columns of look
// chips) makes room slot by slot.
// Keyboard: the handle is a button. Up / Down (Alt allowed) move the row one place, Home / End to the ends. Each move is
// spoken through one polite live region ("Free orbit, moved to position 1 of 5.") and focus stays on the moved row's
// handle, also when the caller re-renders the list in onReorder or after its promise settles.
// After a move: with moveDom (the default) the row is moved in the DOM, then onReorder(ids) gets every row's key in the
// new order; with moveDom: false the caller re-renders the rows from its own state inside onReorder (the saved looks do:
// their order lives in the looks store). Either way the rows then glide from where they were drawn to where they are
// (FLIP), unless the viewer asks for reduced motion. Persistence is the caller's; loadOrder / saveOrder are there for a
// list kept in localStorage.
// Choosing a row is the caller's business: the handle sits beside the row's own button or label, never inside it (a
// button can't hold a button), so a press on the grip never selects anything. House rule (studio.js): a pointer press
// leaves the handle unfocused, so letter keys go back to the note keyboard; a keyboard move keeps its focus.

export const GRIP = '<svg viewBox="0 0 8 14" width="8" height="14" aria-hidden="true" focusable="false"><g fill="currentColor">'
  + [2, 7, 12].map((y) => `<circle cx="1.6" cy="${y}" r="1.25"/><circle cx="6.4" cy="${y}" r="1.25"/>`).join("") + "</g></svg>";
export const HELP_ID = "rr-help";
export const LIVE_ID = "rr-live";
const HELP = "Drag it to a new place, or press the up and down arrow keys. Home and End move it to the first or last place.";
const LIFT_PX = 4;       // a press that moves less than this is a click on the grip, not a drag
const EDGE_PX = 48;      // the band at a scroll box's top and bottom that scrolls it while dragging
const MAX_SCROLL = 16;   // px per frame at the very edge
const SLIDE_MS = 170;
const EASE = "cubic-bezier(.2,.7,.3,1)";
const SR_ONLY = "position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0";

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;",
  '"': "&quot;", "'": "&#39;" })[c]);

// The grip button for a row named `label`. Its description (#rr-help, made by makeReorderable) says how to use it.
export function handleHtml(label, { disabled = false, title = "Drag to reorder, or use the arrow keys", className = "" } = {}) {
  return `<button type="button" class="rr-handle${className ? ` ${esc(className)}` : ""}" aria-label="Move ${esc(label)}"`
    + ` aria-describedby="${HELP_ID}" title="${esc(title)}"${disabled ? " disabled" : ""}>${GRIP}</button>`;
}

// A kept order laid over the ids that exist now: kept ids that still exist, in their kept order, then every id the kept
// order doesn't know yet, in its default place (a camera mode or an instrument added later is never lost).
export function mergeOrder(saved, known) {
  const exists = new Set(known), out = [];
  for (const id of Array.isArray(saved) ? saved : []) if (exists.has(id) && !out.includes(id)) out.push(id);
  for (const id of known) if (!out.includes(id)) out.push(id);
  return out;
}
export function moveItem(list, from, to) {
  const out = list.slice();
  const [x] = out.splice(from, 1);
  out.splice(to, 0, x);
  return out;
}
function browserStorage() {
  try { return globalThis.localStorage || null; } catch { return null; }
}
// An order kept in localStorage (a JSON list of ids) over `known`; an unreadable or blocked store gives the default order.
export function loadOrder(key, known, storage = browserStorage()) {
  let saved = null;
  try { saved = JSON.parse((storage && storage.getItem(key)) || "null"); } catch { saved = null; }
  return mergeOrder(saved, known);
}
export function saveOrder(key, ids, storage = browserStorage()) {
  try { if (!storage) return false; storage.setItem(key, JSON.stringify(ids)); return true; } catch { return false; }
}

// The one live region and the one handle description per document, made on first use.
function ensureAria(doc) {
  if (!doc.getElementById(LIVE_ID)) {
    const live = doc.createElement("div");
    live.id = LIVE_ID;
    live.setAttribute("aria-live", "polite");
    live.setAttribute("aria-atomic", "true");
    live.style.cssText = SR_ONLY;
    doc.body.append(live);
  }
  if (!doc.getElementById(HELP_ID)) {
    const help = doc.createElement("div");
    help.id = HELP_ID;
    help.hidden = true;
    help.textContent = HELP;
    doc.body.append(help);
  }
}

export function makeReorderable(list, { item, handle = ".rr-handle", key = (row) => row.dataset.id,
  label = (row) => row.dataset.label || row.textContent.trim(), onReorder = () => {}, moveDom = true,
  disabled = () => false } = {}) {
  if (!list || !item) throw new Error("makeReorderable needs a list element and an item selector");
  const doc = list.ownerDocument, win = doc.defaultView;
  ensureAria(doc);
  const rows = () => [...list.children].filter((el) => el.matches(item));
  const rowOf = (el) => { const r = el && el.closest ? el.closest(item) : null; return r && r.parentElement === list ? r : null; };
  const reduced = () => { try { return win.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };
  const isOff = () => { try { return !!disabled(); } catch { return false; } };
  let press = null;   // a press on a handle: { h, row, id, x0, y0, x, y }
  let drag = null;    // the lifted row: { rows, from, to, slots, scroller, scroll0, oneColumn, step, raf }

  function say(text) {
    const live = doc.getElementById(LIVE_ID);
    if (!live) return;
    // the same words twice in a row (two moves to the end) are spoken again: a trailing no-break space flips each time
    live.textContent = live.textContent === text ? `${text}\u00a0` : text;
  }
  function raise(el, on) {
    if (!el) return;
    el.classList.toggle("rr-lifted", on);
    el.style.zIndex = on ? "5" : "";
    if (on && win.getComputedStyle(el).position === "static") { el.style.position = "relative"; el.dataset.rrPosition = "1"; }
    if (!on && el.dataset.rrPosition) { el.style.position = ""; delete el.dataset.rrPosition; }
  }
  function rectsByKey(all) {
    const m = new Map();
    for (const r of all) m.set(key(r), r.getBoundingClientRect());
    return m;
  }
  // FLIP: every row starts where it was drawn (before) and slides to where it now is.
  function glide(before, liftedKey) {
    const now = rows();
    const lifted = liftedKey == null ? null : now.find((r) => key(r) === liftedKey) || null;
    const moving = [];
    if (!reduced()) {
      for (const r of now) {
        const b = before.get(key(r));
        if (!b) continue;
        const a = r.getBoundingClientRect();
        const dx = b.left - a.left, dy = b.top - a.top;
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) continue;
        r.style.transition = "none";
        r.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
        moving.push(r);
      }
    }
    for (const r of now) if (!moving.includes(r)) r.style.transition = "";  // the row's own CSS transitions (hover) come back
    if (!moving.length) { raise(lifted, false); return; }
    raise(lifted, true);
    void list.offsetWidth;  // the inverted places are laid out before the slide starts
    for (const r of moving) { r.style.transition = `transform ${SLIDE_MS}ms ${EASE}`; r.style.transform = ""; }
    win.setTimeout(() => {
      if (drag) return;  // a new drag began during the glide: it owns the rows' styles now
      for (const r of moving) if (!r.style.transform) r.style.transition = "";
      raise(lifted, false);
    }, SLIDE_MS + 40);
  }
  function focusHandle(id) {
    const row = rows().find((r) => key(r) === id);
    const h = row && row.querySelector(handle);
    if (!h || h.disabled) return;
    if (doc.activeElement !== h) h.focus({ preventScroll: true });
    if (typeof h.scrollIntoView === "function") h.scrollIntoView({ block: "nearest" });
  }
  function commit(all, from, to, via, before, liftedKey) {
    const row = all[from], id = key(row), name = label(row);
    if (moveDom) { if (to > from) all[to].after(row); else all[to].before(row); }
    const ids = moveDom ? rows().map(key) : moveItem(all.map(key), from, to);
    let out;
    try { out = onReorder(ids, { id, from, to, via }); } catch (e) { console.error("[reorder] onReorder failed:", e); }
    glide(before, liftedKey);
    say(`${name}, moved to position ${to + 1} of ${all.length}.`);
    if (via === "keyboard") {
      focusHandle(id);
      // a caller that re-renders when its store answers drops the focused handle (focus falls to the body); give it back,
      // but never take it from wherever he has moved on to
      const back = () => { const a = doc.activeElement; if (!a || a === doc.body) focusHandle(id); };
      if (out && typeof out.then === "function") out.then(back, back);
    }
  }

  // ------------------------------------------------------------------------------------------ pointer --
  function scrollerOf(el) {
    for (let n = el; n && n !== doc.body && n !== doc.documentElement; n = n.parentElement) {
      const oy = win.getComputedStyle(n).overflowY;
      if ((oy === "auto" || oy === "scroll" || oy === "overlay") && n.scrollHeight > n.clientHeight + 1) return n;
    }
    const se = doc.scrollingElement;
    return se && se.scrollHeight > se.clientHeight + 1 ? se : null;
  }
  const scrollTopOf = (sc) => (sc ? sc.scrollTop : 0);
  const scrollEvents = (sc) => (!sc ? null : sc === doc.scrollingElement ? win : sc);
  function onDown(e) {
    if (press || e.button !== 0 || e.isPrimary === false) return;
    const h = e.target && e.target.closest ? e.target.closest(handle) : null;
    const row = h && list.contains(h) ? rowOf(h) : null;
    if (!row || h.disabled || isOff()) return;
    e.preventDefault();  // no text selection, no native drag image
    press = { h, row, id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
    try { h.setPointerCapture(e.pointerId); } catch { /* a synthetic pointer: the window listeners still see it */ }
    // on the window, not the handle: a caller that re-renders mid-press would take the handle and its listeners away
    win.addEventListener("pointermove", onMove, true);
    win.addEventListener("pointerup", onUp, true);
    win.addEventListener("pointercancel", onCancel, true);
    win.addEventListener("blur", onCancel);
    doc.documentElement.classList.add("rr-dragging");
  }
  function lift() {
    const all = rows(), from = all.indexOf(press.row);
    if (from < 0) return false;
    for (const r of all) { r.style.transition = "none"; r.style.transform = ""; }  // a glide still running is cut short
    const slots = all.map((r) => r.getBoundingClientRect());
    const scroller = scrollerOf(list);
    const next = slots[from + 1], prev = slots[from - 1];
    const gap = next ? next.top - slots[from].bottom : prev ? slots[from].top - prev.bottom : 0;
    drag = { rows: all, from, to: from, slots, scroller, scroll0: scrollTopOf(scroller), raf: 0,
             oneColumn: slots.every((s) => Math.abs(s.left - slots[0].left) < 2), step: slots[from].height + Math.max(0, gap) };
    const slide = reduced() ? "none" : `transform ${SLIDE_MS}ms ${EASE}`;
    all.forEach((r, i) => { r.style.transition = i === from ? "none" : slide; });
    raise(press.row, true);
    list.classList.add("rr-sorting");
    doc.addEventListener("keydown", onDragKey, true);
    const se = scrollEvents(scroller);
    if (se) se.addEventListener("scroll", place, { passive: true });
    drag.raf = win.requestAnimationFrame(autoScroll);
    return true;
  }
  // The lifted row under the pointer, the place it would drop into, and every other row slid to make room for it. All in
  // the frame of the drag's start: a scroll since then is added back, so the row stays under the pointer while it scrolls.
  // A one-column list rides on its own rail: only the height decides where the row drops, so the row moves up and down
  // only. Following the pointer sideways too slid a wide instrument card off the inspector, cut off by its edge (the
  // inspector scrolls, so it clips), and for that moment it was horizontal overflow. A grid (the look chips) needs both.
  function place() {
    if (!drag || !press) return;
    const { rows: all, from, slots } = drag;
    const dx = drag.oneColumn ? 0 : press.x - press.x0, dy = press.y - press.y0 + (scrollTopOf(drag.scroller) - drag.scroll0);
    all[from].style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
    const cx = slots[from].left + slots[from].width / 2 + dx, cy = slots[from].top + slots[from].height / 2 + dy;
    let to = 0;
    if (drag.oneColumn) {
      for (let i = 0; i < all.length; i++) if (i !== from && slots[i].top + slots[i].height / 2 < cy) to++;
    } else {
      let best = Infinity;
      slots.forEach((s, i) => {
        const d = Math.hypot(s.left + s.width / 2 - cx, s.top + s.height / 2 - cy);
        if (d < best) { best = d; to = i; }
      });
    }
    drag.to = to;
    all.forEach((r, i) => {
      if (i === from) return;
      const j = from < to && i > from && i <= to ? i - 1 : to < from && i >= to && i < from ? i + 1 : i;
      let tx = 0, ty = 0;
      if (j !== i) {
        if (drag.oneColumn) ty = (j < i ? -1 : 1) * drag.step;
        else { tx = slots[j].left - slots[i].left; ty = slots[j].top - slots[i].top; }
      }
      r.style.transform = tx || ty ? `translate3d(${tx}px, ${ty}px, 0)` : "";
    });
  }
  function autoScroll() {
    if (!drag) return;
    const sc = drag.scroller;
    if (sc && press) {
      const r = sc === doc.scrollingElement ? { top: 0, bottom: win.innerHeight } : sc.getBoundingClientRect();
      const edge = Math.min(EDGE_PX, (r.bottom - r.top) / 4);
      const over = press.y < r.top + edge ? press.y - (r.top + edge) : press.y > r.bottom - edge ? press.y - (r.bottom - edge) : 0;
      if (over) {
        const was = sc.scrollTop;
        sc.scrollTop = was + Math.sign(over) * Math.ceil(Math.min(1, Math.abs(over) / edge) * MAX_SCROLL);
        if (sc.scrollTop !== was) place();
      }
    }
    drag.raf = win.requestAnimationFrame(autoScroll);
  }
  function onMove(e) {
    if (!press || e.pointerId !== press.id) return;
    press.x = e.clientX;
    press.y = e.clientY;
    if (!drag) {
      if (Math.hypot(press.x - press.x0, press.y - press.y0) < LIFT_PX) return;
      if (!press.row.isConnected || isOff() || !lift()) { endPress(); return; }
    }
    e.preventDefault();
    place();
  }
  // Put the lifted row down: in its new place (commit) or back where it was.
  function drop(keep) {
    const d = drag;
    drag = null;
    win.cancelAnimationFrame(d.raf);
    doc.removeEventListener("keydown", onDragKey, true);
    const se = scrollEvents(d.scroller);
    if (se) se.removeEventListener("scroll", place);
    list.classList.remove("rr-sorting");
    const row = d.rows[d.from], liftedKey = key(row);
    const before = rectsByKey(d.rows);  // where each row is drawn now, mid-slide
    for (const r of d.rows) { r.style.transition = "none"; r.style.transform = ""; }
    raise(row, false);
    if (keep && d.to !== d.from && row.isConnected && !isOff()) { commit(d.rows, d.from, d.to, "pointer", before, liftedKey); return; }
    glide(before, liftedKey);
    if (!keep) say(`Move cancelled. ${label(row)} stays at position ${d.from + 1} of ${d.rows.length}.`);
  }
  function endPress() {
    if (!press) return;
    const { h, id } = press;
    press = null;
    win.removeEventListener("pointermove", onMove, true);
    win.removeEventListener("pointerup", onUp, true);
    win.removeEventListener("pointercancel", onCancel, true);
    win.removeEventListener("blur", onCancel);
    doc.documentElement.classList.remove("rr-dragging");
    try { if (h.hasPointerCapture && h.hasPointerCapture(id)) h.releasePointerCapture(id); } catch { /* already released */ }
    if (doc.activeElement === h) h.blur();  // the house rule: after a pointer press, letter keys are the note keyboard again
  }
  // The press ends before the drop: a caller that redraws its rows in onReorder (and skips redrawing while dragging()) must
  // already see the drag over, or the dropped row would show in its old place until the caller's next redraw.
  function onUp(e) {
    if (!press || e.pointerId !== press.id) return;
    const lifted = !!drag;
    if (lifted) e.preventDefault();
    endPress();
    if (lifted) drop(true);
  }
  function onCancel(e) {
    if (!press || (e && e.pointerId !== undefined && e.pointerId !== press.id)) return;
    endPress();
    if (drag) drop(false);
  }
  function onDragKey(e) {
    if (e.key !== "Escape") return;
    e.preventDefault();
    e.stopPropagation();  // Escape also closes the inspector and hushes Claude: this one only puts the row back
    onCancel();
  }

  // ------------------------------------------------------------------------------------------ keyboard --
  function onKey(e) {
    if (press) return;
    const h = e.target && e.target.closest ? e.target.closest(handle) : null;
    const row = h && list.contains(h) ? rowOf(h) : null;
    if (!row || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.altKey && e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    const all = rows(), from = all.indexOf(row), last = all.length - 1;
    const to = e.key === "ArrowUp" ? from - 1 : e.key === "ArrowDown" ? from + 1 : e.key === "Home" ? 0 : e.key === "End" ? last : null;
    if (to === null) return;
    // the page's own keys must not see these: Home and End play and stop an exercise, the arrows belong to the cards
    e.preventDefault();
    e.stopPropagation();
    if (h.disabled || isOff() || from < 0) return;
    if (to < 0 || to > last || to === from) {
      say(`${label(row)} is already ${from === 0 ? "first" : "last"}, position ${from + 1} of ${all.length}.`);
      return;
    }
    commit(all, from, to, "keyboard", rectsByKey(all), null);
  }

  list.addEventListener("pointerdown", onDown);
  list.addEventListener("keydown", onKey);
  return {
    dragging: () => !!press,
    destroy() {
      endPress();
      if (drag) drop(false);
      list.removeEventListener("pointerdown", onDown);
      list.removeEventListener("keydown", onKey);
    },
  };
}
