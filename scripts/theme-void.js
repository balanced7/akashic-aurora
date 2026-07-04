// theme-void.js — OLED "Void" theme (claude's lane, Aurora Glass)
//
// A true-black theme for OLED panels: --bg is pure #000000 so black pixels are physically OFF
// (infinite contrast, the aurora + neon float on an actual void). Saturated neon accents pop hard
// against the black; the chrome (borders/panels) stays dim so only the meaningful things glow.
//
// Self-registering, standalone (the aurora-shader.js pattern): loaded AFTER bifrost_ui.py's inline
// script, it appends a 'void' entry to the global THEME_CSS map and registers it as a theme variant.
// The only bifrost_ui.py change needed is a one-line <script src="/theme-void.js"> include + its
// static route — everything else lives here, so the palette is iterable without touching that file.
//
// OLED burn-in note: burn-in comes from STATIC max-luminance pixels held for hours. This theme keeps
// large areas near-black and confines brightness to small neon accents + text (which scrolls), and
// the aurora light bed is always in motion — so there's no static bright plate to burn in.

(function (global) {
  'use strict';

  // The full var set the other themes (ember/abyss/frost) define, retuned for a pure-black OLED bed.
  var VOID_CSS =
    ' :root{' +
    '--bg:#000000;' +            // true OLED black — pixels off
    '--bg2:#040407;' +          // barely-there lift for recessed fields
    '--panel:#0a0a11;' +        // glass panels: very dark, slight elevation
    '--panel2:#0f0f18;' +
    '--border:#1b1b28;' +       // dim chrome — seen, not glowing
    '--text:#eaf0ff;' +         // cool bright white
    '--muted:#8090b4;' +
    '--faint:#7581a3;' +       // WCAG: 5.1:1 over glass-on-black (was #4a5270 = 2.6:1, failed)
    '--claude:#ff9d5c;' +       // neon amber (boosted sat vs default)
    '--deepseek:#7ab8ff;' +     // neon blue
    '--user:#48e6bf;' +         // signature aurora-neon aqua
    '--system:#8a94b8;' +
    '--accent:#48e6bf;' +       // signature neon — the "earned" accent
    '--accent2:#9d7cf7;' +      // neon violet
    '--amber:#ffc247;' +
    '--danger:#ff5c6a;' +       // neon red
    '--shadow:0 8px 34px rgba(0,0,0,.75);' +   // deeper shadow reads on pure black
    '}';

  function ready() {
    return typeof global.THEME_CSS === 'object' &&
           typeof global.registerVariant === 'function' &&
           typeof global._mountTheme === 'function';
  }

  function install() {
    if (!ready()) return false;
    global.THEME_CSS.void = VOID_CSS;
    global.registerVariant(
      'theme', 'void', 'Void', 'true-black OLED + neon',
      function () { global._mountTheme('void'); },
      global._unmountTheme
    );
    // If the user had 'void' saved as their theme pref, apply it now that it exists.
    try {
      if (typeof global.getPref === 'function' && global.getPref('theme') === 'void' &&
          typeof global.mountSlot === 'function') {
        global.mountSlot('theme', 'void');
      }
    } catch (e) {}
    return true;
  }

  // The inline script defines the registry synchronously before this file loads, so install() should
  // succeed immediately; retry a few frames only as a defensive measure against load-order surprises.
  if (!install()) {
    var tries = 0;
    var iv = global.setInterval(function () {
      if (install() || ++tries > 20) global.clearInterval(iv);
    }, 50);
  }
})(typeof window !== 'undefined' ? window : globalThis);
