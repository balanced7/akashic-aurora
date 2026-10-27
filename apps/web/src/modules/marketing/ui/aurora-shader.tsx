"use client";

import { useEffect, useRef } from "react";

import { cn } from "@akashic-labs/ui";

/**
 * A living aurora: curtains of light drawn by a fragment shader.
 * Renders at reduced resolution, pauses offscreen, draws one still frame under reduced motion,
 * and leaves the CSS backdrop underneath as the fallback when WebGL is unavailable.
 */

const VERTEX = `
attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

const FRAGMENT = `
precision mediump float;
uniform vec2 uResolution;
uniform float uTime;
uniform vec2 uPointer;
uniform float uIntensity;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float value = 0.0;
  float amplitude = 0.5;
  for (int i = 0; i < 4; i++) {
    value += amplitude * noise(p);
    p *= 2.03;
    amplitude *= 0.5;
  }
  return value;
}

// One curtain: a wavy ribbon with vertical rays hanging below its edge.
float curtain(vec2 uv, float seed, float height, float speed) {
  float t = uTime * speed;
  float wave = fbm(vec2(uv.x * 1.6 + seed, t * 0.35)) - 0.5;
  float edge = height + wave * 0.32 + sin(uv.x * 2.3 + seed + t) * 0.04;
  float d = uv.y - edge;
  float ribbon = exp(-abs(d) * 16.0);
  float rays = pow(fbm(vec2(uv.x * 34.0 + seed * 3.0, t * 0.6)), 3.4) * 2.2;
  float hang = smoothstep(0.0, -0.08, d) * smoothstep(-0.42, -0.04, d);
  return ribbon * 1.1 + rays * hang;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  float aspect = uResolution.x / uResolution.y;
  vec2 p = vec2(uv.x * aspect, uv.y);
  p.x += (uPointer.x - 0.5) * 0.12;
  p.y += (uPointer.y - 0.5) * 0.04;

  vec3 cyan = vec3(0.04, 0.78, 0.73);
  vec3 teal = vec3(0.01, 0.42, 0.50);
  vec3 gold = vec3(0.78, 0.66, 0.43);
  vec3 violet = vec3(0.40, 0.30, 0.86);

  float a = curtain(p, 1.7, 0.86, 0.22);
  float b = curtain(p + vec2(0.35, 0.0), 6.1, 0.78, 0.17);
  float c = curtain(p - vec2(0.6, 0.0), 11.3, 0.94, 0.13);

  vec3 color = cyan * a + teal * b * 0.9 + mix(violet, gold, uv.x) * c * 0.55;
  color += gold * pow(a * b, 1.5) * 0.6;

  // Fade into the black page: strongest at the top, gone near the fold.
  float fade = smoothstep(0.25, 0.95, uv.y);
  // Keep the copy column calm: the light leans toward the empty right side.
  float side = mix(0.22, 1.0, smoothstep(0.2, 0.8, uv.x));
  float vignette = smoothstep(1.25, 0.25, length((uv - vec2(0.5, 0.75)) * vec2(1.0, 1.4)));
  color = color / (1.0 + color) * 1.6;
  color *= fade * vignette * side * uIntensity;

  // Gentle film grain keeps gradients from banding.
  color += (hash(gl_FragCoord.xy + uTime) - 0.5) * 0.018;
  gl_FragColor = vec4(color, 1.0);
}
`;

const RESOLUTION_SCALE = 0.5;
const LOW_RESOLUTION_SCALE = 0.28;
const SLOW_FRAME_MS = 22;

const compile = (gl: WebGLRenderingContext, type: number, source: string) => {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
};

export const AuroraShader = ({
  className,
  intensity = 0.7,
}: {
  className?: string;
  intensity?: number;
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", {
      antialias: false,
      premultipliedAlpha: false,
      alpha: false,
    });
    if (!gl || gl.isContextLost()) return;

    const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX);
    const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
    const program = gl.createProgram();
    if (!vertex || !fragment) return;
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
    gl.useProgram(program);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW,
    );
    const position = gl.getAttribLocation(program, "position");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    const uResolution = gl.getUniformLocation(program, "uResolution");
    const uTime = gl.getUniformLocation(program, "uTime");
    const uPointer = gl.getUniformLocation(program, "uPointer");
    const uIntensity = gl.getUniformLocation(program, "uIntensity");

    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const pointer = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
    let frame = 0;
    let visible = true;
    let scaleFactor = RESOLUTION_SCALE;
    let skip = false;
    let frameCount = 0;
    let slowFrames = 0;
    let lastFrame = 0;
    let tick = 0;
    const start = performance.now();

    const resize = () => {
      const scale = Math.min(window.devicePixelRatio, 1.5) * scaleFactor;
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * scale));
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * scale));
      gl.viewport(0, 0, canvas.width, canvas.height);
    };

    const draw = (now: number) => {
      pointer.x += (pointer.tx - pointer.x) * 0.04;
      pointer.y += (pointer.ty - pointer.y) * 0.04;
      gl.uniform2f(uResolution, canvas.width, canvas.height);
      gl.uniform1f(uTime, reduced ? 12 : (now - start) / 1000);
      gl.uniform2f(uPointer, pointer.x, pointer.y);
      gl.uniform1f(uIntensity, intensity);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    // Adaptive quality: if the device cannot keep up, drop resolution and render every other frame.
    const loop = (now: number) => {
      if (visible) {
        if (lastFrame && frameCount < 90) {
          frameCount += 1;
          if (now - lastFrame > SLOW_FRAME_MS) slowFrames += 1;
          if (
            frameCount === 90 &&
            slowFrames > 45 &&
            scaleFactor !== LOW_RESOLUTION_SCALE
          ) {
            scaleFactor = LOW_RESOLUTION_SCALE;
            skip = true;
            resize();
          }
        }
        lastFrame = now;
        tick += 1;
        if (!skip || tick % 2 === 0) draw(now);
      }
      frame = requestAnimationFrame(loop);
    };

    const onPointer = (event: PointerEvent) => {
      pointer.tx = event.clientX / window.innerWidth;
      pointer.ty = 1 - event.clientY / window.innerHeight;
    };

    const observer = new IntersectionObserver(([entry]) => {
      visible = Boolean(entry?.isIntersecting);
    });
    observer.observe(canvas);

    resize();
    window.addEventListener("resize", resize);
    if (reduced) {
      draw(start);
    } else {
      window.addEventListener("pointermove", onPointer, { passive: true });
      frame = requestAnimationFrame(loop);
    }
    canvas.dataset.ready = "true";

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointer);
      // Release our resources but keep the context alive: React may remount and reuse this canvas.
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertex);
      gl.deleteShader(fragment);
    };
  }, [intensity]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      data-testid="aurora-shader"
      className={cn(
        "pointer-events-none absolute inset-0 h-full w-full opacity-90 mix-blend-screen",
        className,
      )}
    />
  );
};
