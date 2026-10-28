import {
  BookOpen,
  Brain,
  Building2,
  Compass,
  Database,
  FlaskConical,
  Github,
  History,
  Layers,
  Library,
  MessageSquareText,
  Network,
  Plug,
  Radio,
  Scale,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Trees,
  Workflow,
  Wrench,
} from "lucide-react";
import { useId } from "react";

import { cn } from "@akashic-labs/ui";

import type { LucideIcon } from "lucide-react";
import type { NavIcon } from "~/modules/marketing/content/site";

/** Akashic Labs mark: a faceted gem, the record at the core. */
export const AkashicMark = ({ className }: { className?: string }) => {
  const id = useId();
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      className={cn("size-7", className)}
    >
      <defs>
        <linearGradient
          id={`${id}-g`}
          x1="4"
          y1="2"
          x2="28"
          y2="30"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#F0E6D2" />
          <stop offset="0.45" stopColor="#C8AA6E" />
          <stop offset="1" stopColor="#785A28" />
        </linearGradient>
        <linearGradient
          id={`${id}-c`}
          x1="16"
          y1="8"
          x2="16"
          y2="24"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#B8FFF8" />
          <stop offset="1" stopColor="#0AC8B9" />
        </linearGradient>
      </defs>
      <path
        d="M16 1.5 29 9v14L16 30.5 3 23V9L16 1.5Z"
        stroke={`url(#${id}-g)`}
        strokeWidth="1.6"
      />
      <path
        d="M16 7.5 23.5 12v8L16 24.5 8.5 20v-8L16 7.5Z"
        fill={`url(#${id}-c)`}
        opacity="0.95"
      />
      <path
        d="M16 7.5v17M8.5 12 23.5 20M23.5 12 8.5 20"
        stroke="#010A13"
        strokeOpacity="0.35"
        strokeWidth="0.8"
      />
    </svg>
  );
};

export const AkashicWordmark = ({ className }: { className?: string }) => (
  <span className={cn("inline-flex items-center gap-2.5", className)}>
    <AkashicMark />
    <span className="text-[17px] font-semibold tracking-[-0.03em] text-white">
      Akashic Labs
    </span>
  </span>
);

/** Aurora mark: three curtains of light over a horizon line. */
export const AuroraMark = ({ className }: { className?: string }) => {
  const id = useId();
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden
      className={cn("size-10", className)}
    >
      <defs>
        <linearGradient
          id={`${id}-a`}
          x1="0"
          y1="6"
          x2="40"
          y2="34"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#B8FFF8" />
          <stop offset="0.5" stopColor="#0AC8B9" />
          <stop offset="1" stopColor="#C8AA6E" />
        </linearGradient>
      </defs>
      <rect
        x="0.75"
        y="0.75"
        width="38.5"
        height="38.5"
        rx="10"
        fill="#05090D"
        stroke="white"
        strokeOpacity="0.1"
      />
      <path
        d="M8 27c3-9 6-14 8-14s3.5 6 6 6 4-9 10-9"
        stroke={`url(#${id}-a)`}
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M8 31c4-5 7-8 10-8s5 3 8 3 4-3 6-4"
        stroke={`url(#${id}-a)`}
        strokeOpacity="0.5"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
};

const navIcons: Record<NavIcon, LucideIcon> = {
  brain: Brain,
  radio: Radio,
  network: Network,
  scroll: ScrollText,
  database: Database,
  compass: Compass,
  wrench: Wrench,
  workflow: Workflow,
  layers: Layers,
  plug: Plug,
  scale: Scale,
  flask: FlaskConical,
  shield: ShieldCheck,
  book: BookOpen,
  history: History,
  message: MessageSquareText,
  building: Building2,
  github: Github,
  sparkles: Sparkles,
  library: Library,
  trees: Trees,
};

export const NavIconGlyph = ({
  icon,
  className,
}: {
  icon: NavIcon;
  className?: string;
}) => {
  const Icon = navIcons[icon];
  return <Icon className={cn("size-4", className)} strokeWidth={1.75} />;
};
