import {
  degrade,
  isDue,
  needsLoop,
  PROBE_MS,
  qualityFor,
  renderSize,
  SLOW_FRAME_MS,
} from "./schedule";

import type { ShaderPreset } from "./presets";
import type { Conditions, Quality } from "./schedule";

/**
 * One WebGL context for every shader background on the page. Browsers cap live contexts (about
 * 16), so instead of a context per section, this renders each visible background into one
 * offscreen canvas and copies the frame into that background's 2D canvas. One context, one
 * requestAnimationFrame loop, and the loop stops when nothing visible needs a frame: off screen,
 * in a hidden tab, or after the still frame under reduced motion.
 */

const VERTEX = `
attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

type State = "live" | "fallback";

interface Background {
  readonly canvas: HTMLCanvasElement;
  readonly context: CanvasRenderingContext2D;
  readonly preset: ShaderPreset;
  readonly intensity: number;
  readonly seed: number;
  readonly fps: number;
  visible: boolean;
  drawn: boolean;
  last: number;
}

interface Program {
  readonly program: WebGLProgram;
  readonly resolution: WebGLUniformLocation | null;
  readonly time: WebGLUniformLocation | null;
  readonly pointer: WebGLUniformLocation | null;
  readonly intensity: WebGLUniformLocation | null;
  readonly seed: WebGLUniformLocation | null;
}

export interface BackgroundOptions {
  readonly preset: ShaderPreset;
  readonly intensity: number;
  readonly seed: number;
}

const setState = (canvas: HTMLCanvasElement, state: State) => {
  if (canvas.dataset.state !== state) canvas.dataset.state = state;
};

class Renderer {
  private readonly canvas = document.createElement("canvas");
  private readonly gl: WebGLRenderingContext | null;
  private readonly programs = new Map<ShaderPreset, Program | null>();
  private readonly backgrounds = new Map<Element, Background>();
  private readonly reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  );
  private readonly start = performance.now();
  private readonly pointer = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
  private quality: Quality;
  private frame = 0;
  private lost = false;
  private probe = { frames: 0, slow: 0, start: 0, last: 0, done: false };
  private intersection: IntersectionObserver;
  private resize: ResizeObserver;

  constructor() {
    this.quality = qualityFor({
      coarse: window.matchMedia("(pointer: coarse)").matches,
      width: window.innerWidth,
    });
    this.gl = this.canvas.getContext("webgl", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: "low-power",
    });
    if (this.gl) this.setup(this.gl);

    this.canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      this.lost = true;
      this.programs.clear();
      cancelAnimationFrame(this.frame);
      this.frame = 0;
      for (const background of this.backgrounds.values()) {
        background.drawn = false;
        setState(background.canvas, "fallback");
      }
    });
    this.canvas.addEventListener("webglcontextrestored", () => {
      if (!this.gl) return;
      this.lost = false;
      this.setup(this.gl);
      this.wake();
    });

    // A margin so a background has its first frame before it scrolls in.
    this.intersection = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const background = this.backgrounds.get(entry.target);
          if (background) background.visible = entry.isIntersecting;
        }
        this.wake();
      },
      { rootMargin: "120px 0px" },
    );
    this.resize = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const background = this.backgrounds.get(entry.target);
        if (background) this.fit(background);
      }
      this.wake();
    });

    document.addEventListener("visibilitychange", () => {
      this.probe.last = 0;
      this.wake();
    });
    this.reducedMotion.addEventListener("change", () => {
      for (const background of this.backgrounds.values())
        background.drawn = false;
      this.wake();
    });
    window.addEventListener(
      "pointermove",
      (event) => {
        this.pointer.tx = event.clientX / window.innerWidth;
        this.pointer.ty = 1 - event.clientY / window.innerHeight;
      },
      { passive: true },
    );
  }

  attach(canvas: HTMLCanvasElement, options: BackgroundOptions) {
    const context = canvas.getContext("2d", { alpha: false });
    if (!this.gl || !context) {
      setState(canvas, "fallback");
      return () => undefined;
    }
    const background: Background = {
      canvas,
      context,
      ...options,
      fps: options.preset.fps,
      visible: false,
      drawn: false,
      last: 0,
    };
    this.backgrounds.set(canvas, background);
    this.fit(background);
    this.intersection.observe(canvas);
    this.resize.observe(canvas);
    return () => {
      this.backgrounds.delete(canvas);
      this.intersection.unobserve(canvas);
      this.resize.unobserve(canvas);
    };
  }

  private setup(gl: WebGLRenderingContext) {
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW,
    );
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  }

  private compile(gl: WebGLRenderingContext, type: number, source: string) {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
    gl.deleteShader(shader);
    return null;
  }

  /** Compiled once per preset and shared by every background that uses it; null if it will not compile. */
  private program(gl: WebGLRenderingContext, preset: ShaderPreset) {
    if (this.programs.has(preset)) return this.programs.get(preset) ?? null;
    const vertex = this.compile(gl, gl.VERTEX_SHADER, VERTEX);
    const fragment = this.compile(gl, gl.FRAGMENT_SHADER, preset.fragment);
    const program = gl.createProgram();
    let result: Program | null = null;
    if (vertex && fragment) {
      gl.attachShader(program, vertex);
      gl.attachShader(program, fragment);
      gl.bindAttribLocation(program, 0, "position");
      gl.linkProgram(program);
      if (gl.getProgramParameter(program, gl.LINK_STATUS)) {
        const uniform = (name: string) => gl.getUniformLocation(program, name);
        result = {
          program,
          resolution: uniform("uResolution"),
          time: uniform("uTime"),
          pointer: uniform("uPointer"),
          intensity: uniform("uIntensity"),
          seed: uniform("uSeed"),
        };
      }
    }
    if (vertex) gl.deleteShader(vertex);
    if (fragment) gl.deleteShader(fragment);
    if (!result) gl.deleteProgram(program);
    this.programs.set(preset, result);
    return result;
  }

  private fit(background: Background) {
    const { width, height } = renderSize(
      background.canvas.clientWidth,
      background.canvas.clientHeight,
      Math.min(window.devicePixelRatio || 1, this.quality.dpr),
      background.preset.scale * this.quality.scale,
    );
    if (
      background.canvas.width === width &&
      background.canvas.height === height
    )
      return;
    // Resizing clears the canvas, so it needs a frame again, even a still one.
    background.canvas.width = width;
    background.canvas.height = height;
    background.drawn = false;
  }

  private conditions(): Conditions {
    return {
      reduced: this.reducedMotion.matches,
      hidden: document.hidden,
      quality: this.quality,
    };
  }

  private draw(
    gl: WebGLRenderingContext,
    background: Background,
    now: number,
    reduced: boolean,
  ) {
    const program = this.program(gl, background.preset);
    if (!program) {
      setState(background.canvas, "fallback");
      return;
    }
    const { width, height } = background.canvas;
    if (this.canvas.width < width || this.canvas.height < height) {
      this.canvas.width = Math.max(this.canvas.width, width);
      this.canvas.height = Math.max(this.canvas.height, height);
    }
    gl.viewport(0, 0, width, height);
    gl.useProgram(program.program);
    gl.uniform2f(program.resolution, width, height);
    gl.uniform1f(
      program.time,
      reduced ? background.preset.still : (now - this.start) / 1000,
    );
    gl.uniform2f(program.pointer, this.pointer.x, this.pointer.y);
    gl.uniform1f(program.intensity, background.intensity);
    gl.uniform1f(program.seed, background.seed);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    // The viewport sits at the bottom-left of the drawing buffer.
    background.context.drawImage(
      this.canvas,
      0,
      this.canvas.height - height,
      width,
      height,
      0,
      0,
      width,
      height,
    );
    background.drawn = true;
    background.last = now;
    setState(background.canvas, "live");
  }

  /**
   * Judge the device over a window of frames. If it cannot keep up, render fewer pixels and frames
   * and judge again, down to a still frame; once it keeps up, stop judging.
   */
  private measure(now: number) {
    const probe = this.probe;
    if (probe.done) return;
    if (probe.last) {
      probe.frames += 1;
      if (now - probe.last > SLOW_FRAME_MS) probe.slow += 1;
      if (now - probe.start >= PROBE_MS) {
        const quality = degrade(this.quality, probe.frames, probe.slow);
        if (quality === this.quality || quality.fps === 0) probe.done = true;
        if (quality !== this.quality) {
          this.quality = quality;
          for (const background of this.backgrounds.values()) {
            background.drawn = false;
            this.fit(background);
          }
        }
        probe.frames = 0;
        probe.slow = 0;
        probe.start = now;
      }
    } else {
      probe.frames = 0;
      probe.slow = 0;
      probe.start = now;
    }
    probe.last = now;
  }

  private tick = (now: number) => {
    this.frame = 0;
    const gl = this.gl;
    if (!gl || this.lost) return;
    const conditions = this.conditions();
    if (!conditions.reduced) this.measure(now);
    const still = conditions.reduced || conditions.quality.fps === 0;
    this.pointer.x += (this.pointer.tx - this.pointer.x) * 0.04;
    this.pointer.y += (this.pointer.ty - this.pointer.y) * 0.04;
    for (const background of this.backgrounds.values()) {
      if (isDue(background, now, conditions))
        this.draw(gl, background, now, still);
    }
    this.wake();
  };

  private wake() {
    if (this.frame || this.lost || !this.gl) return;
    if (!needsLoop(this.backgrounds.values(), this.conditions())) {
      // A gap while idle is not a slow frame.
      this.probe.last = 0;
      return;
    }
    this.frame = requestAnimationFrame(this.tick);
  }
}

let renderer: Renderer | undefined;

/** The page's one renderer, created on first use in the browser. */
export const getRenderer = () => {
  renderer ??= new Renderer();
  return renderer;
};
