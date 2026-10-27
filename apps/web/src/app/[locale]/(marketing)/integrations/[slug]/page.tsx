import { Check } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getMetadata } from "~/lib/metadata";
import { install } from "~/modules/marketing/content/aurora";
import {
  getIntegration,
  integrations,
} from "~/modules/marketing/content/integrations";
import { links, routes } from "~/modules/marketing/content/site";
import { TranslationTable } from "~/modules/marketing/integrations/translation-table";
import { CopyButton } from "~/modules/marketing/ui/copy-button";
import { CtaBand } from "~/modules/marketing/ui/cta-band";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";
import { PageHero } from "~/modules/marketing/ui/page-hero";
import {
  ButtonLink,
  Container,
  Section,
  SectionIntro,
} from "~/modules/marketing/ui/primitives";
import { Terminal } from "~/modules/marketing/ui/terminal";

import type { Support } from "~/modules/marketing/content/integrations";

/** Every valid slug is known at build time; anything else is a real 404. */
export const dynamicParams = false;

export function generateStaticParams() {
  return integrations.map((integration) => ({ slug: integration.slug }));
}

export async function generateMetadata(props: {
  params: Promise<{ slug: string; locale: string }>;
}) {
  const params = await props.params;
  const integration = getIntegration(params.slug);
  if (!integration) return {};
  return getMetadata({
    title: `Aurora for ${integration.name}`,
    description: integration.tagline,
    canonical: `${routes.integrations}/${integration.slug}`,
  })({ params: Promise.resolve({ locale: params.locale }) });
}

const supportText: Record<Support, string> = {
  yes: "Documented",
  manual: "Manual habit",
  none: "Not documented yet",
};

export default async function IntegrationPage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;
  const integration = getIntegration(slug);
  if (!integration) notFound();

  const prompt = install.agentPrompt.join("\n");
  const launch = integration.launcher
    ? `${integration.launcher} '${prompt}'`
    : undefined;
  const capability = [
    { label: "One-paste setup", value: integration.setup },
    { label: "Recall hooks", value: integration.hooks },
    { label: "MCP tools", value: integration.mcp },
    { label: "Seat on the bus", value: integration.seat },
  ];

  return (
    <>
      <PageHero
        crumbs={[
          { label: "Integrations", href: routes.integrations },
          {
            label: integration.name,
            href: `${routes.integrations}/${integration.slug}`,
          },
        ]}
        eyebrow={`Aurora for ${integration.name}`}
        title={<>Shared memory for {integration.name}</>}
        description={integration.tagline}
        actions={
          <ButtonLink href={links.doc("quickstart")} size="lg" arrow>
            Quickstart
          </ButtonLink>
        }
        aside={
          <HudFrame className="w-full min-w-[280px] lg:w-[320px]">
            <div className="flex flex-col gap-3 p-6">
              <HudLabel>Support today</HudLabel>
              {capability.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between gap-6 text-[14px]"
                >
                  <span className="text-white/80">{item.label}</span>
                  <span
                    className={
                      item.value === "yes"
                        ? "text-hud-cyan"
                        : item.value === "manual"
                          ? "text-hud-gold"
                          : "text-white/50"
                    }
                  >
                    {supportText[item.value]}
                  </span>
                </div>
              ))}
            </div>
          </HudFrame>
        }
      />

      <Section className="pt-0 sm:pt-0 lg:pt-0">
        <Container className="grid gap-6 lg:grid-cols-2">
          {launch && (
            <div className="mk-card flex flex-col overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
                <span className="text-[14px] font-medium text-white">
                  Paste into {integration.name}
                </span>
                <CopyButton text={launch} />
              </div>
              <pre
                tabIndex={0}
                className="max-h-[340px] overflow-auto p-5 font-mono text-[12.5px] leading-6 text-white/85"
              >
                <code>{launch}</code>
              </pre>
            </div>
          )}
          <div className="flex flex-col gap-6">
            {integration.hookCommand ? (
              <Terminal
                title="turn on the push"
                lines={[
                  { kind: "cmd", text: integration.hookCommand },
                  {
                    kind: "dim",
                    text: "# lessons now arrive right before edits and commands",
                  },
                ]}
              />
            ) : (
              <Terminal
                title="manual habit"
                lines={[
                  {
                    kind: "cmd",
                    text: "aurora recall-at --path <file you are about to edit>",
                  },
                  {
                    kind: "dim",
                    text: "# no hook wiring documented yet; run this before you act",
                  },
                ]}
              />
            )}
            <div className="mk-card flex flex-col gap-4 p-6">
              <HudLabel tone="cyan">From the docs</HudLabel>
              <ul className="flex flex-col gap-3">
                {integration.notes.map((note) => (
                  <li
                    key={note}
                    className="flex gap-3 text-[14.5px] leading-relaxed text-white/85"
                  >
                    <Check className="text-hud-cyan mt-1 size-4 shrink-0" />
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Container>
      </Section>

      {integration.translationKey && (
        <Section id="translations">
          <Container>
            <SectionIntro
              eyebrow={`${integration.name} terms`}
              title={`If you know ${integration.name}, you already know half of Aurora`}
              description={`Each card maps an Aurora concept to the nearest ${integration.name} idea, and says where they differ.`}
              action={
                <Link
                  href={`${routes.integrations}?tool=${encodeURIComponent(integration.translationKey)}#translations`}
                  className="text-[15px] font-medium text-white hover:text-white/70"
                >
                  See all {integration.name} terms
                </Link>
              }
            />
            <div className="mt-12">
              <TranslationTable
                tool={integration.translationKey}
                basePath={`${routes.integrations}/${integration.slug}`}
                limit={6}
                showPicker={false}
              />
            </div>
          </Container>
        </Section>
      )}

      <CtaBand />
    </>
  );
}
