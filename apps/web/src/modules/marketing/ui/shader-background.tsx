"use client";

import { useEffect, useId, useRef } from "react";

import { cn } from "@akashic-labs/ui";

import { shaderPresets } from "~/modules/marketing/ui/shader/presets";
import { getRenderer } from "~/modules/marketing/ui/shader/renderer";

import type { CSSProperties } from "react";
import type { ShaderPresetName } from "~/modules/marketing/ui/shader/presets";

/** Soft top and bottom edges, so a section's field melts into the black page around it. */
const fades = {
  both: "linear-gradient(transparent, #000 18%, #000 82%, transparent)",
  bottom: "linear-gradient(#000 60%, transparent)",
  none: undefined,
} as const;

/** A stable 0..1 seed from React's id, so two sections with one preset do not look alike. */
const seedOf = (id: string) => {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return (hash % 1000) / 1000;
};

interface ShaderBackgroundProps {
  readonly preset: ShaderPresetName;
  /** Brightness multiplier. Content sections stay at 1 or below so text keeps its contrast. */
  readonly intensity?: number;
  readonly fade?: keyof typeof fades;
  readonly className?: string;
}

/**
 * A moving shader field behind a section. Its parent must be `relative isolate`: the field sits at
 * z-index -10 inside that stacking context, under the section's content. The preset's CSS gradient
 * shows until the first frame, and again whenever WebGL is missing or its context is lost.
 */
export const ShaderBackground = ({
  preset,
  intensity = 1,
  fade = "both",
  className,
}: ShaderBackgroundProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const seed = seedOf(useId());
  const { fallback } = shaderPresets[preset];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    return getRenderer().attach(canvas, {
      preset: shaderPresets[preset],
      intensity,
      seed,
    });
  }, [preset, intensity, seed]);

  const mask = fades[fade];
  const style: CSSProperties = {
    background: fallback,
    maskImage: mask,
    WebkitMaskImage: mask,
  };

  return (
    <div
      aria-hidden
      data-testid="shader-background"
      data-preset={preset}
      className={cn(
        "pointer-events-none absolute inset-0 -z-10 overflow-hidden",
        className,
      )}
      style={style}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 size-full opacity-0 transition-opacity duration-700 data-[state=live]:opacity-100"
      />
    </div>
  );
};
