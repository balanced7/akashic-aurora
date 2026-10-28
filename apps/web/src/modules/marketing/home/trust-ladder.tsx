import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { trustLadder, trustNotes } from "~/modules/marketing/content/aurora";
import { routes } from "~/modules/marketing/content/site";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import {
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Reveal } from "~/modules/marketing/ui/reveal";

/** The trust ladder from security/acl.json and core/trust/capabilities.py. */
export const TrustLadder = () => (
  <Section>
    <Container>
      <SectionIntro
        eyebrow="Trust"
        title={
          <>
            Trust, granted step by step.
            <br />
            <span className="text-mk-muted">Quarantine by default.</span>
          </>
        }
        description="Aurora is a high-trust house, but it does not assume trust. Any id it does not know starts quarantined. Every step up records the sentence that authorized it, and a grant can lapse."
        action={
          <Link
            href={routes.pillar("trust")}
            className="inline-flex items-center gap-1.5 text-[15px] font-medium text-white hover:text-white/70"
          >
            How trust works <ArrowRight className="size-4" />
          </Link>
        }
      />

      <div className="mt-14 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-10">
        <Reveal>
          <HudFrame className="[--hud-cut:18px]">
            <ol className="divide-y divide-white/[0.06]">
              {trustLadder.map((role, index) => (
                <li
                  key={role.role}
                  className={cn(
                    "grid gap-3 p-5 sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-6 sm:p-6",
                    role.default && "bg-hud-gold/[0.04]",
                  )}
                >
                  <div className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-1.5">
                    <span className="font-hud text-hud-gold/60 text-[10px] font-semibold tracking-[0.16em]">
                      0{trustLadder.length - index}
                    </span>
                    <span className="font-mono text-[13px] font-medium text-white">
                      {role.role}
                    </span>
                    {role.default && (
                      <span className="hud-label text-hud-gold text-[9px]">
                        default
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[15px] text-white/90">
                      {role.capabilities}
                    </span>
                    <span className="text-mk-faint text-[13.5px] leading-relaxed">
                      {role.note}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </HudFrame>
        </Reveal>

        <Reveal delay={0.08} className="h-full">
          <div className="mk-card flex h-full flex-col gap-6 p-7 sm:p-8">
            <div className="flex items-center gap-3">
              <LockKeyhole className="text-hud-cyan size-5" strokeWidth={1.6} />
              <HudLabel tone="cyan">How it grows</HudLabel>
            </div>
            <ul className="flex flex-col gap-4">
              {trustNotes.map((note) => (
                <li
                  key={note}
                  className="text-mk-muted flex gap-3 text-[14.5px] leading-relaxed"
                >
                  <ShieldCheck
                    className="text-hud-cyan/70 mt-0.5 size-4 shrink-0"
                    strokeWidth={1.7}
                  />
                  {note}
                </li>
              ))}
            </ul>
            <p className="text-mk-faint mt-auto border-t border-white/[0.06] pt-5 text-[13px] leading-relaxed">
              The Gate is the human root of trust. Your words authorize grants
              and ratify names. A peer-relayed operator word is not a receipt.
            </p>
          </div>
        </Reveal>
      </div>
    </Container>
  </Section>
);
