import { ArrowRight, Fingerprint, LockKeyhole, Users } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { residents } from "~/modules/marketing/content/aurora";
import { routes } from "~/modules/marketing/content/site";
import { HudLabel } from "~/modules/marketing/ui/hud";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

const gravity = [
  {
    icon: Users,
    title: "No seat owns a file",
    body: "A charter sets a lean, not a territory. Any agent can take any task and touch any file.",
  },
  {
    icon: LockKeyhole,
    title: "A lock is a moment",
    body: "A 15-minute claim on a path while one agent edits. It expires, and the hook refuses a file a peer holds.",
  },
  {
    icon: Fingerprint,
    title: "A name is earned",
    body: "A callsign is peer-proposed and human-confirmed. The Gate ratifies it, and the seat keeps its own lessons.",
  },
] as const;

/** The fleet as residents with callsigns, plus the house law: gravity, not walls. */
export const FleetSection = () => (
  <Section>
    <Container>
      <SectionIntro
        eyebrow="The residents"
        title={
          <>
            Six residents
            <br />
            <span className="text-mk-muted">and a Gate.</span>
          </>
        }
        description="A resident is a seat that earned a callsign and keeps its own lessons. Each has a written charter: what it is for, how it works, and what it tends to get wrong. None of them owns a file or a task."
        action={
          <Link
            href={routes.pillar("fleet")}
            className="inline-flex items-center gap-1.5 text-[15px] font-medium text-white hover:text-white/70"
          >
            Meet the fleet <ArrowRight className="size-4" />
          </Link>
        }
      />

      <div className="mt-14 grid gap-px overflow-hidden rounded-[22px] border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-3">
        {residents.map((resident, index) => (
          <Reveal key={resident.id} delay={index * 0.04} className="h-full">
            <article className="group flex h-full flex-col gap-4 bg-[#060607] p-6 transition-colors hover:bg-[#0a0a0c] sm:p-7">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-1">
                  <HudLabel
                    tone="muted"
                    className="text-[9.5px] tracking-[0.18em]"
                  >
                    {resident.model}
                  </HudLabel>
                  <h3
                    className={cn(
                      "mk-title text-[1.55rem] leading-none",
                      resident.tone === "gold"
                        ? "text-hud-gold-bright"
                        : "text-white",
                    )}
                  >
                    {resident.callsign}
                  </h3>
                </div>
                <span className="text-mk-faint font-mono text-[10.5px]">
                  {resident.id}
                </span>
              </div>
              <p className="text-mk-muted text-[14.5px] leading-relaxed">
                {resident.role}
              </p>
              <p className="text-mk-faint mt-auto border-l border-white/10 pl-3 text-[13px] leading-relaxed italic">
                {resident.lean}
              </p>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal className="mt-6">
        <div className="mk-card grid gap-8 p-7 sm:p-9 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:items-center">
          <div className="flex flex-col gap-3">
            <HudLabel tone="cyan">The house law</HudLabel>
            <h3 className="mk-title text-3xl sm:text-4xl">
              Gravity,
              <br />
              <span className="text-mk-muted">not walls.</span>
            </h3>
            <p className="text-mk-muted max-w-md text-[15px] leading-relaxed">
              The fleet is held together by shared work and trust, not by
              ownership boundaries. Territory rots. A short lock keeps two hands
              off one file while they work.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {gravity.map((item) => (
              <div key={item.title} className="flex flex-col gap-2">
                <item.icon className="text-hud-cyan size-4" strokeWidth={1.7} />
                <span className="text-[14.5px] font-medium text-white">
                  {item.title}
                </span>
                <span className="text-mk-faint text-[13px] leading-relaxed">
                  {item.body}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Reveal>

      <Reveal className="mt-4">
        <div className="mk-card border-hud-gold/20 flex flex-col gap-2 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="hud-frame flex size-9 items-center justify-center [--hud-cut:8px]">
              <Fingerprint className="text-hud-gold size-4" />
            </span>
            <div className="flex flex-col">
              <span className="text-[15px] font-medium text-white">
                The Gate is a seat too.
              </span>
              <span className="text-mk-faint text-[13.5px]">
                The human root of trust. Your words authorize grants and ratify
                names. You also keep the brakes.
              </span>
            </div>
          </div>
          <span className="hud-label text-hud-gold text-[10px]">you</span>
        </div>
      </Reveal>
    </Container>
  </Section>
);
