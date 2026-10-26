"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { usePrefs } from "~/lib/prefs";
import { useConsole } from "~/lib/store";

type Shader = {
  start(): void;
  destroy(): void;
  setState(s: 0 | 1 | 2): void;
  setMotionBlur?(b: number): void;
  setSpeed?(v: number): void;
  setIntensity?(v: number): void;
};
declare global {
  interface Window {
    AuroraGlass?: { AuroraShader: new (c: HTMLCanvasElement) => Shader; isSupported(): boolean };
  }
}

/** Load scripts/aurora-shader.js once, through the backend proxy (one source for both consoles). */
let loading: Promise<void> | null = null;
function loadShader(): Promise<void> {
  if (window.AuroraGlass) return Promise.resolve();
  loading ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "/aurora-shader.js";
    s.onload = () => resolve();
    s.onerror = () => {
      loading = null;
      reject(new Error("aurora-shader.js failed to load"));
    };
    document.head.appendChild(s);
  });
  return loading;
}

/**
 * The animated light bed. Opt-in and persisted, as on the Python console: WebGL2 is not free,
 * and reduced-motion users keep the static gradient (isSupported() refuses for them).
 */
export function AuroraBackground() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const shader = useRef<Shader | null>(null);
  const on = usePrefs((s) => s.aurora);
  const speed = usePrefs((s) => s.auroraSpeed);
  const intensity = usePrefs((s) => s.auroraIntensity);
  const paused = useConsole((s) => !!s.status?.paused);
  const halted = useConsole((s) => Object.keys(s.status?.halted ?? {}).length > 0);

  useEffect(() => {
    if (!on) return;
    const setAurora = (aurora: boolean) => usePrefs.getState().set({ aurora });
    let cancelled = false;
    loadShader()
      .then(() => {
        if (cancelled || !canvas.current) return;
        if (!window.AuroraGlass?.isSupported()) {
          toast.warning("Aurora needs WebGL2 and no reduced-motion preference.");
          setAurora(false);
          return;
        }
        const s = new window.AuroraGlass.AuroraShader(canvas.current);
        s.setMotionBlur?.(0.22);
        const p = usePrefs.getState();
        s.setSpeed?.(p.auroraSpeed);
        s.setIntensity?.(p.auroraIntensity);
        s.start();
        shader.current = s;
      })
      .catch(() => {
        toast.error("Could not load the aurora shader from the console backend.");
        setAurora(false);
      });
    return () => {
      cancelled = true;
      shader.current?.destroy();
      shader.current = null;
    };
  }, [on]);

  useEffect(() => {
    shader.current?.setState(halted ? 2 : paused ? 1 : 0);
  }, [paused, halted, on]);

  useEffect(() => {
    shader.current?.setSpeed?.(speed);
    shader.current?.setIntensity?.(intensity);
  }, [speed, intensity]);

  return <canvas ref={canvas} aria-hidden className="pointer-events-none fixed inset-0 -z-20 size-full" hidden={!on} />;
}
