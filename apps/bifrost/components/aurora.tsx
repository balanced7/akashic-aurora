"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { useConsole } from "~/lib/store";

type Shader = { start(): void; destroy(): void; setState(s: 0 | 1 | 2): void; setMotionBlur?(b: number): void };
declare global {
  interface Window {
    AuroraGlass?: { AuroraShader: new (c: HTMLCanvasElement) => Shader; isSupported(): boolean };
  }
}

const FLAG = "bifrost.aurora";

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
  const on = useConsole((s) => s.aurora);
  const setAurora = useConsole((s) => s.setAurora);
  const paused = useConsole((s) => !!s.status?.paused);
  const halted = useConsole((s) => Object.keys(s.status?.halted ?? {}).length > 0);

  useEffect(() => {
    if (localStorage.getItem(FLAG) === "1") setAurora(true);
  }, [setAurora]);

  useEffect(() => {
    localStorage.setItem(FLAG, on ? "1" : "0");
    if (!on) return;
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
  }, [on, setAurora]);

  useEffect(() => {
    shader.current?.setState(halted ? 2 : paused ? 1 : 0);
  }, [paused, halted, on]);

  return <canvas ref={canvas} aria-hidden className="pointer-events-none fixed inset-0 -z-20 size-full" hidden={!on} />;
}
