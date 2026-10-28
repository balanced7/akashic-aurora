"use client";

import { motion, useScroll, useSpring, useTransform } from "motion/react";

/** A thin HUD line under the header that fills as you read, with a gem at its leading edge. */
export const ReadingProgress = () => {
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, {
    stiffness: 140,
    damping: 26,
    mass: 0.3,
  });
  const gemLeft = useTransform(
    progress,
    (value) => `calc(${value * 100}% - 4px)`,
  );

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-x-0 top-16 z-40 h-px bg-white/[0.04]"
    >
      <motion.div
        data-testid="reading-progress"
        className="from-hud-gold via-hud-gold-bright to-hud-cyan h-full origin-left bg-gradient-to-r shadow-[0_0_12px_rgb(10_200_185/0.7)]"
        style={{ scaleX: progress }}
      />
      <motion.span
        className="hud-gem absolute -top-[3.5px]"
        style={{ left: gemLeft }}
      />
    </div>
  );
};
