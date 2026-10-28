import { appConfig } from "~/config/app";
import {
  differentiators,
  install,
  laws,
  pillars,
  positioning,
} from "~/modules/marketing/content/aurora";
import { integrations } from "~/modules/marketing/content/integrations";
import { links, routes } from "~/modules/marketing/content/site";
import { useCases } from "~/modules/marketing/content/use-cases";

/** llms.txt: the site in plain markdown, for agents that read it before they act. */
export const dynamic = "force-static";

export function GET() {
  const url = (path: string) => `${appConfig.url}${path}`;
  const body = [
    `# ${positioning.name}`,
    "",
    `> ${positioning.tagline}. ${positioning.subheadline}`,
    "",
    "Aurora is open source under Apache-2.0 and runs on your machine. Built by Akashic Labs.",
    "",
    "## Start",
    "",
    `- [Quickstart](${links.doc("quickstart")}): running in two minutes`,
    `- [Source on GitHub](${links.repo})`,
    `- [How it works](${url(routes.howItWorks)})`,
    "",
    "```bash",
    install.uvMac,
    ...install.mac,
    "```",
    "",
    "## Parts",
    "",
    ...pillars.map(
      (pillar) =>
        `- [${pillar.name}](${url(routes.pillar(pillar.slug))}): ${pillar.summary}`,
    ),
    "",
    "## What makes it different",
    "",
    ...differentiators.map((item) => `- ${item.title}: ${item.body}`),
    "",
    "## Laws learned the hard way",
    "",
    ...laws.map((law) => `- ${law.phrase} ${law.story}`),
    "",
    "## Integrations",
    "",
    ...integrations.map(
      (item) =>
        `- [${item.name}](${url(`${routes.integrations}/${item.slug}`)}): ${item.tagline}`,
    ),
    "",
    "## Use cases",
    "",
    ...useCases.map(
      (item) =>
        `- [${item.title}](${url(routes.useCase(item.slug))}): ${item.summary}`,
    ),
    "",
    "## Honesty",
    "",
    `- [Evidence](${url(routes.evidence)}): counts with the commands that print them, and the claims we do not make.`,
    `- [Security](${url(routes.security)}): a threat model for shared agent memory.`,
    `- [Compare](${url(routes.compare)}): Aurora vs memory APIs, rules files and chat history.`,
    "",
  ].join("\n");

  return new Response(body, {
    headers: { "Content-Type": "text/markdown; charset=utf-8" },
  });
}
