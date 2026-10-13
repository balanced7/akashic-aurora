// arsenal/web/lib/workbench/strip.js -- the STRIP along the bottom: the renders of whatever is on stage (pre-rendered
// stills and the contact sheet, all from SwiftShader), and the takes Daniel keeps from a live run, each with its receipt.
//
// WHY A STRIP. A single frame lies about motion; a row of frames at known times shows how a shader moves without
// running it, the way a contact sheet shows a roll of film. And a take is only worth keeping if it says what made it:
// the subject, the renderer, the scale, the time, the modules (architecture draft 5.3: "each with its receipt").
// Takes live in this page only (they are data URLs in memory); saving one is a right-click away.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, takes the document as an argument.
import { h, hint, imgFrom, panel, put } from './common.js';

const tLabel = (t) => (Number.isFinite(Number(t)) && t !== null ? `t = ${Number(t).toFixed(2)} s` : 'still');

export function mountStrip(doc, root, opts = {}) {
  const maxTakes = Number(opts.maxTakes) > 0 ? Number(opts.maxTakes) : 12;
  // Takes come from a live run; while live runs are off (the Stage's switch, stage.js) the Strip says why there are none.
  const live = opts.live !== false;
  const { side, body } = panel(doc, root, 'wb-strip', 'Strip', 'Renders and takes, each with its receipt');
  const renders = h(doc, 'div', 'wb-strip-renders');
  const takesBox = h(doc, 'div', 'wb-strip-takes');
  const row = put(h(doc, 'div', 'wb-strip-row'), renders, takesBox);
  body.replaceChildren(row);
  const takes = [];

  function idleRenders() {
    renders.replaceChildren(put(h(doc, 'div', 'wb-strip-idle'), h(doc, 'p', 'wb-kicker', 'Renders'),
      hint(doc, 'The frames of whatever is on stage appear here: stills rendered on SwiftShader at known times, and the contact sheet.')));
  }
  function idleTakes() {
    takesBox.replaceChildren(put(h(doc, 'div', 'wb-strip-idle'), h(doc, 'p', 'wb-kicker', 'Takes'),
      hint(doc, live ? 'Stills you take from a live run, each labelled with what ran.'
        : 'Stills taken from a live run land here. Live runs are off until their safety review clears.')));
  }

  function frameFigure(f, title) {
    const fig = h(doc, 'figure', 'wb-frame');
    fig.appendChild(imgFrom(doc, [f.url], { alt: `${title}, ${tLabel(f.t)}`, cls: 'wb-frame-img',
      onNone: (img) => { img.remove(); fig.appendChild(h(doc, 'div', 'wb-frame-none', 'not rendered')); } }));
    fig.appendChild(h(doc, 'figcaption', null, f.label || tLabel(f.t)));
    return fig;
  }

  /** {title, frames: [{t, url, label}], sheet: url, note} */
  function showRenders({ title = '', frames = [], sheet = null, note = '' } = {}) {
    if (!frames.length && !sheet) {
      renders.replaceChildren(put(h(doc, 'div', 'wb-strip-idle'), h(doc, 'p', 'wb-kicker', `Renders · ${title}`),
        hint(doc, note || 'No pre-rendered frames for this subject yet.')));
      return;
    }
    const head = put(h(doc, 'div', 'wb-strip-head'), h(doc, 'p', 'wb-kicker', `Renders · ${title}`), note && h(doc, 'p', 'wb-insp-sub', note));
    const reel = h(doc, 'div', 'wb-reel');
    for (const f of frames.slice(0, 24)) reel.appendChild(frameFigure(f, title));
    if (sheet) {
      const a = h(doc, 'a', 'wb-sheet-link', null, { href: sheet, target: '_blank', rel: 'noopener',
        title: 'The contact sheet: every frame on one picture' });
      a.appendChild(imgFrom(doc, [sheet], { alt: `${title}: contact sheet`, cls: 'wb-sheet-img',
        onNone: (img) => { img.remove(); a.appendChild(h(doc, 'span', 'wb-frame-none', 'no sheet')); } }));
      reel.appendChild(put(h(doc, 'figure', 'wb-frame wb-frame-sheet'), a, h(doc, 'figcaption', null, 'contact sheet')));
    }
    renders.replaceChildren(head, reel);
  }

  /** {url, receipt: {subject, renderer, scale, size, t, modules, sha}} */
  function addTake(take) {
    if (!take || !take.url) return;
    takes.unshift(take);
    if (takes.length > maxTakes) takes.length = maxTakes;
    const reel = h(doc, 'div', 'wb-reel');
    for (const tk of takes) {
      const r = tk.receipt || {};
      const fig = h(doc, 'figure', 'wb-frame wb-take');
      fig.appendChild(h(doc, 'img', 'wb-frame-img', null, { src: tk.url, alt: `${r.subject || 'take'}, ${tLabel(r.t)}` }));
      const cap = h(doc, 'figcaption');
      cap.appendChild(h(doc, 'span', 'wb-take-title', `${r.subject || 'take'} · ${tLabel(r.t)}`));
      cap.appendChild(h(doc, 'span', 'wb-take-line', [r.scale !== undefined ? `scale ${r.scale}` : '',
        Array.isArray(r.size) ? `${r.size[0]}×${r.size[1]}` : '', r.sha ? `sha ${String(r.sha).slice(0, 10)}` : ''].filter(Boolean).join(' · ')));
      cap.appendChild(h(doc, 'span', 'wb-take-line', r.renderer || 'renderer not reported'));
      fig.appendChild(cap);
      reel.appendChild(fig);
    }
    takesBox.replaceChildren(put(h(doc, 'div', 'wb-strip-head'), h(doc, 'p', 'wb-kicker', `Takes · ${takes.length}`)), reel);
    side.textContent = `${takes.length} take${takes.length === 1 ? '' : 's'} this session`;
  }

  idleRenders();
  idleTakes();
  return { el: root, showRenders, addTake, takes: () => takes.slice(), clear: idleRenders };
}
