// activity-line.js -- the fleet's voice, rendered as a waveform (claude's lane)
//
// Adapted from a shader Daniil found and immediately read correctly: "This one is simple but can
// be used for voice indication." In this system the analogue of voice is TOKEN EMISSION, so the
// waveform is driven by generation rate, not by audio.
//
// WHY THIS EARNS ITS PLACE, and it is not that it is pretty. Daniil spent a long stretch of
// 2026-08-01 pushing on one distinction: an agent that is IDLE and an agent we have simply LOST
// SIGHT OF are not the same thing, and a console that renders them identically is lying. He put
// it as every state needing a unique signature. The console could not express that -- an idle
// row and an unreachable row both showed nothing. A waveform gives three distinguishable
// readings for free, from one cheap primitive:
//
//   LIVE     amplitude and frequency track the emission rate      -- generating
//   FLAT     a solid, steady, dim line                            -- measured, and the measure is zero
//   DOTTED   a broken baseline                                    -- NOT measured; we are blind here
//
// Solid-flat versus dotted is the whole point. Flat asserts "the sensor is reporting, and it
// reports nothing." Dotted asserts "there is no sensor." Those are different claims about the
// world and the operator has to be able to tell them apart at a glance, because the correct
// response to each is opposite: leave it alone, versus go find out why.
//
// COST. Five sine evaluations and two smoothsteps per fragment, no raymarching, no loops beyond
// the five lines. At a 320x28 strip rendered at half scale that is ~4.5k fragments -- roughly a
// two-hundredth of the aurora behind it. This is the cheapest thing on the page by a wide margin,
// which is deliberate: a status indicator that costs real frames would be self-defeating.
//
// INTERFACE CONTRACT (mirrors AgentAvatar deliberately -- one house pattern, one seam):
//   if (ActivityLine.isSupported()) { const l = new ActivityLine(canvasEl); l.start(); }
//   l.setRate(0..1)        // emission rate, normalised
//   l.setSensed(bool)      // false => dotted baseline; the sensor itself is absent
//   l.setTint([r,g,b])     // 0..1 floats; defaults to the console's OS blue
// The status layer owns WHAT the numbers mean; the shader owns the visual. Neither reaches across.
(function (global) {
  'use strict';

  var VERT = '#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}';

  var FRAG = [
'#version 300 es',
'precision highp float;',
'out vec4 outColor;',
'uniform vec2  u_res;',
'uniform float u_time;',
'uniform float u_amp;      // waveform amplitude: 0 = flat, driven by emission rate',
'uniform float u_speed;    // travel rate: also driven by emission rate',
'uniform float u_sensed;   // 1 = the sensor reports; 0 = there is no sensor (dotted)',
'uniform vec3  u_tint;',
'uniform float u_dim;',
'',
'#define S smoothstep',
'',
// The original enveloped amplitude by S(1,0,|x|) so the wave tapers to nothing at both edges,
// and enveloped THICKNESS by S(.2,.9,|x|) so the line thins as it goes. Both are kept -- the
// taper is what makes a strip read as a signal rather than as a decorative border. The two
// CONSTANTS could not be: see the aspect note in main(), and the thickness note below.
'vec4 line(vec2 uv, float speed, float height, vec3 col, float amp){',
'  uv.y += S(1., 0., abs(uv.x)) * sin(u_time * speed + uv.x * height) * amp;',
// THICKNESS IN PIXELS, NOT IN UV. The original .004 was implicitly ~4px because it divided by a
// full-screen R.y of ~1080. Against an 11px-tall backing store the same constant is 0.04px --
// mathematically drawn and optically absent. Deriving it from u_res.y keeps the line ~2 CSS px
// whatever height the strip ends up.
'  float th = 1.0 / u_res.y;',
// Never let the soft edge reach zero: smoothstep(0., 0., x) is degenerate, and the original hit
// exactly that case for |x| < .2, hard-edging the middle of the line by accident.
'  float soft = th * (0.8 + 3.0 * S(.2, .9, abs(uv.x)));',
'  float core = S(soft, 0., abs(uv.y) - th * .5);',
'  return vec4(core * col, core) * S(1., .3, abs(uv.x));',
'}',
'',
'void main(){',
// ASPECT-NORMALISED X, and this is the whole difference between a strip and a screen. The
// original divides BOTH axes by resolution.y, which is fine at 16:9 (uv.x lands in +/-0.89, so
// the S(1,0,|x|) envelope spans the frame). This strip is ~52:1, where the same maths sends
// uv.x to +/-26 and crushes every envelope in the shader into the middle 1/26th of the width.
// Mapping x to +/-1 across the FULL width restores the intent at any aspect ratio.
'  vec2 uv;',
'  uv.x = (gl_FragCoord.x - .5*u_res.x) / (.5*u_res.x);',
'  uv.y = (gl_FragCoord.y - .5*u_res.y) / u_res.y;',
'  vec4 acc = vec4(0.);',
'  for (float i = 0.; i <= 5.; i += 1.){',
'    float t = i / 5.;',
// House palette rather than the original's warm ramp: the console is OS blue on black, and a
// voice indicator that introduced a second accent would read as a different system's widget.
'    vec3 col = mix(u_tint, vec3(.30,.64,1.), t) * (.55 + .45*t);',
'    acc += line(uv, u_speed * (1. + t), 4. + t, col, u_amp);',
'  }',
// THE UNSENSED SIGNATURE. Breaking the line along x is a claim of ABSENCE, and it has to be
// visually unlike a quiet line rather than a dimmer one -- dimming is a matter of degree and
// reads as "less activity", which is the exact confusion this exists to prevent.
'  float dash = mix(step(.42, fract(uv.x * 20.)), 1., u_sensed);',
'  acc *= dash;',
'  outColor = vec4(acc.rgb * u_dim, clamp(acc.a, 0., 1.));',
'}'
  ].join('\n');

  function compile(gl, type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error('activity-line: ' + gl.getShaderInfoLog(s));
    }
    return s;
  }

  function ActivityLine(canvas) {
    // low-power is not a micro-optimisation on this host. It has a documented AMD display-driver
    // TDR history, and every additional context that asks for the discrete GPU is another chance
    // to trip the watchdog. See memory: gpu-driver-crashes-desktop-app.
    var gl = canvas.getContext('webgl2', {
      alpha: true, antialias: false, depth: false, stencil: false,
      premultipliedAlpha: false, powerPreference: 'low-power'
    });
    if (!gl) throw new Error('activity-line: no webgl2');

    this.canvas = canvas; this.gl = gl;
    var p = gl.createProgram();
    gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, VERT));
    gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      throw new Error('activity-line link: ' + gl.getProgramInfoLog(p));
    }
    gl.useProgram(p);
    this.prog = p;
    this.u = {};
    var self = this;
    ['u_res','u_time','u_amp','u_speed','u_sensed','u_tint','u_dim'].forEach(function (n) {
      self.u[n] = gl.getUniformLocation(p, n);
    });
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    this.vao = gl.createVertexArray();
    this._t0 = 0; this._raf = 0; this._running = false;
    this._rate = 0; this._sensed = true;
    this.tint = [0.01, 0.51, 1.0];        // #0381fe, the timeline's --tl-1
    this.dim = 1;
    // Targets and current values are separate so rate changes EASE rather than jump. A status
    // indicator that snaps reads as a glitch; the eye trusts a needle that moves.
    this._amp = 0; this._spd = 1; this._sen = 1;
    this._resize();
  }

  ActivityLine.isSupported = function () {
    try {
      var c = document.createElement('canvas');
      return !!c.getContext('webgl2');
    } catch (e) { return false; }
  };

  ActivityLine.prototype._resize = function (cssW, cssH) {
    // Same explicit-size contract as the avatar, and for the same reason: measuring clientWidth
    // is a bet that layout has settled since the box was set. Losing it bakes a wrong-sized
    // render target into the backing store, which is only re-cut on resize.
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    var scale = parseFloat(global.AKASHIC_AVATAR_SCALE);
    if (!(scale > 0 && scale <= 1)) scale = 0.5;
    var eff = Math.max(0.35, dpr * scale);
    if (cssW > 0) this.cssW = cssW;
    if (cssH > 0) this.cssH = cssH;
    var w = Math.max(1, Math.floor((this.cssW || this.canvas.clientWidth || 320) * eff));
    var h = Math.max(1, Math.floor((this.cssH || this.canvas.clientHeight || 28) * eff));
    this.canvas.width = w; this.canvas.height = h;
    this.gl.viewport(0, 0, w, h);
  };

  // rate: 0..1 normalised emission. Amplitude is deliberately NOT linear in rate -- sqrt gives
  // the low end visible travel, because the difference between "barely emitting" and "silent" is
  // the reading an operator most needs and is exactly what a linear ramp flattens away.
  ActivityLine.prototype.setRate = function (r) {
    this._rate = Math.max(0, Math.min(1, r || 0));
  };
  ActivityLine.prototype.setSensed = function (b) { this._sensed = !!b; };
  ActivityLine.prototype.setTint = function (rgb) { if (rgb && rgb.length === 3) this.tint = rgb; };

  ActivityLine.prototype.start = function () {
    if (this._running) return;
    this._running = true;
    var self = this, gl = this.gl, slow = 0;
    var last = 0;
    function frame(ts) {
      if (!self._running) return;
      if (!self._t0) self._t0 = ts;
      var dt = last ? Math.min(0.1, (ts - last) / 1000) : 0.016;
      last = ts;

      // fps watchdog, same policy as the avatar: if this cannot hold a usable frame rate it
      // stops rather than degrading the whole console. An indicator is not worth a stutter.
      if (dt > 0.055) { slow++; } else { slow = Math.max(0, slow - 1); }
      if (slow > 90) { self.stop(); return; }

      var k = 1 - Math.pow(0.001, dt);            // frame-rate independent easing
      var tgtAmp = self._sensed ? 0.02 + 0.30 * Math.sqrt(self._rate) : 0.0;
      var tgtSpd = 1.0 + 3.0 * self._rate;
      self._amp += (tgtAmp - self._amp) * k;
      self._spd += (tgtSpd - self._spd) * k;
      self._sen += ((self._sensed ? 1 : 0) - self._sen) * k;

      gl.useProgram(self.prog);
      gl.bindVertexArray(self.vao);
      gl.uniform2f(self.u.u_res, self.canvas.width, self.canvas.height);
      gl.uniform1f(self.u.u_time, (ts - self._t0) / 1000);
      gl.uniform1f(self.u.u_amp, self._amp);
      gl.uniform1f(self.u.u_speed, self._spd);
      gl.uniform1f(self.u.u_sensed, self._sen);
      gl.uniform3f(self.u.u_tint, self.tint[0], self.tint[1], self.tint[2]);
      gl.uniform1f(self.u.u_dim, self.dim);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      self._raf = global.requestAnimationFrame(frame);
    }
    this._raf = global.requestAnimationFrame(frame);
  };

  ActivityLine.prototype.stop = function () {
    this._running = false;
    if (this._raf) global.cancelAnimationFrame(this._raf);
    this._raf = 0;
  };

  // A hidden tab must not burn frames. The avatar does the same; both are chrome, and chrome
  // nobody is looking at is pure waste.
  document.addEventListener('visibilitychange', function () {
    if (!global._activityLines) return;
    global._activityLines.forEach(function (l) {
      if (document.hidden) l.stop(); else l.start();
    });
  });

  global.ActivityLine = ActivityLine;
})(window);
