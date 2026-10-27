import { useId } from "react";

import { cn } from "@akashic-labs/ui";

import { NavIconGlyph } from "~/modules/marketing/ui/brand";

import type { NavIcon } from "~/modules/marketing/content/site";

/**
 * A hextech crest for each pillar: rotating rings, a chamfered gold hex, a glowing core.
 * The HUD layer's signature piece, used where a pillar is introduced.
 */
export const PillarCrest = ({
  icon,
  index,
  tone = "cyan",
  size = 220,
  className,
}: {
  icon: NavIcon;
  index: number;
  tone?: "cyan" | "gold";
  size?: number;
  className?: string;
}) => {
  const id = useId();
  const core = tone === "cyan" ? "#0ac8b9" : "#c8aa6e";
  const coreBright = tone === "cyan" ? "#b8fff8" : "#f0e6d2";

  return (
    <div
      data-testid="pillar-crest"
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        viewBox="0 0 200 200"
        className="absolute inset-0 h-full w-full overflow-visible"
      >
        <defs>
          <linearGradient
            id={`${id}-gold`}
            x1="20"
            y1="10"
            x2="180"
            y2="190"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#f0e6d2" />
            <stop offset="0.4" stopColor="#c8aa6e" />
            <stop offset="1" stopColor="#785a28" />
          </linearGradient>
          <radialGradient id={`${id}-core`} cx="50%" cy="45%" r="55%">
            <stop offset="0" stopColor={coreBright} stopOpacity="0.95" />
            <stop offset="0.45" stopColor={core} stopOpacity="0.55" />
            <stop offset="1" stopColor="#010a13" stopOpacity="0" />
          </radialGradient>
          <filter
            id={`${id}-glow`}
            x="-50%"
            y="-50%"
            width="200%"
            height="200%"
          >
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        {/* Outer rings turn slowly in opposite directions */}
        <g className="origin-center animate-[spin_38s_linear_infinite] motion-reduce:animate-none">
          <circle
            cx="100"
            cy="100"
            r="94"
            fill="none"
            stroke={core}
            strokeOpacity="0.35"
            strokeDasharray="2 7"
          />
          {[0, 90, 180, 270].map((angle) => (
            <rect
              key={angle}
              x="98"
              y="2"
              width="4"
              height="9"
              fill={core}
              opacity="0.8"
              transform={`rotate(${angle} 100 100)`}
            />
          ))}
        </g>
        <g className="origin-center animate-[spin_26s_linear_infinite_reverse] motion-reduce:animate-none">
          <circle
            cx="100"
            cy="100"
            r="82"
            fill="none"
            stroke={`url(#${id}-gold)`}
            strokeOpacity="0.5"
            strokeDasharray="40 10 4 10"
          />
        </g>

        {/* Glow behind the frame */}
        <circle
          cx="100"
          cy="100"
          r="46"
          fill={core}
          opacity="0.35"
          filter={`url(#${id}-glow)`}
        />

        {/* Chamfered hex frame, double line */}
        <path
          d="M100 26 L162 62 L162 138 L100 174 L38 138 L38 62 Z"
          fill="#05090d"
          stroke={`url(#${id}-gold)`}
          strokeWidth="2.5"
        />
        <path
          d="M100 38 L152 68 L152 132 L100 162 L48 132 L48 68 Z"
          fill={`url(#${id}-core)`}
          stroke={`url(#${id}-gold)`}
          strokeOpacity="0.45"
          strokeWidth="1"
        />
        {/* Wing notches */}
        <path
          d="M30 100 L38 92 L38 108 Z M170 100 L162 92 L162 108 Z"
          fill={`url(#${id}-gold)`}
        />
        {/* Rank plate */}
        <path
          d="M78 166 L122 166 L116 184 L84 184 Z"
          fill="#05090d"
          stroke={`url(#${id}-gold)`}
          strokeWidth="1.5"
        />
        <text
          x="100"
          y="179.5"
          textAnchor="middle"
          fontSize="11"
          fontWeight="700"
          letterSpacing="2"
          fill="#f0e6d2"
          fontFamily="var(--font-hud)"
        >
          {String(index).padStart(2, "0")}
        </text>
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <NavIconGlyph
          icon={icon}
          className="size-[22%] text-white drop-shadow-[0_0_10px_rgba(184,255,248,0.8)]"
        />
      </div>
    </div>
  );
};
