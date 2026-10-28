/**
 * Site-wide marketing content: links, navigation and footer.
 * Product facts come from the Aurora docs (aurora/apps/docs/content/docs).
 */
import env from "env.config";

const REPO_URL = "https://github.com/balanced7/akashic-aurora";

/** The Aurora docs are not hosted publicly yet; every docs link goes through this base. */
const DOCS_URL = env.NEXT_PUBLIC_DOCS_URL;

export const links = {
  repo: REPO_URL,
  readme: `${REPO_URL}#readme`,
  license: `${REPO_URL}/blob/master/LICENSE`,
  agentsMd: `${REPO_URL}/blob/master/AGENTS.md`,
  issues: `${REPO_URL}/issues`,
  discussions: `${REPO_URL}/discussions`,
  commits: `${REPO_URL}/commits/master`,
  docs: DOCS_URL,
  doc: (path: string) => `${DOCS_URL}/docs${path ? `/${path}` : ""}`,
  uv: "https://docs.astral.sh/uv/",
  contactEmail: "hello@akashiclabs.dev",
} as const;

export const routes = {
  home: "/",
  aurora: "/aurora",
  pillar: (slug: string) => `/aurora/${slug}`,
  howItWorks: "/how-it-works",
  useCases: "/use-cases",
  useCase: (slug: string) => `/use-cases/${slug}`,
  integrations: "/integrations",
  compare: "/compare",
  evidence: "/evidence",
  principles: "/principles",
  openSource: "/open-source",
  security: "/security",
  pricing: "/pricing",
  enterprise: "/enterprise",
  changelog: "/changelog",
  docs: "/docs",
  glossary: "/glossary",
  about: "/about",
  blog: "/blog",
  blogPost: (slug: string) => `/blog/${slug}`,
  walks: "/walks",
  walk: (slug: string) => `/walks/${slug}`,
  contact: "/contact",
  legal: (slug: string) => `/legal/${slug}`,
} as const;

export interface NavItem {
  readonly title: string;
  readonly description: string;
  readonly href: string;
  readonly icon: NavIcon;
}

export interface NavGroup {
  readonly label: string;
  readonly items: readonly NavItem[];
  readonly featured?: {
    readonly eyebrow: string;
    readonly title: string;
    readonly description: string;
    readonly href: string;
  };
}

export type NavIcon =
  | "brain"
  | "radio"
  | "network"
  | "scroll"
  | "database"
  | "compass"
  | "wrench"
  | "workflow"
  | "layers"
  | "plug"
  | "scale"
  | "flask"
  | "shield"
  | "book"
  | "history"
  | "message"
  | "building"
  | "github"
  | "sparkles"
  | "library"
  | "trees";

export const navGroups: readonly NavGroup[] = [
  {
    label: "Product",
    featured: {
      eyebrow: "Akashic Aurora",
      title: "A home for your agents",
      description:
        "Shared memory, a message bus and a trust layer for a team of AI agents and one human.",
      href: routes.aurora,
    },
    items: [
      {
        title: "Knowledge",
        description: "Lessons that arrive before the action.",
        href: routes.pillar("knowledge"),
        icon: "brain",
      },
      {
        title: "Bifrost",
        description: "A message bus between agents. You keep the brakes.",
        href: routes.pillar("bus"),
        icon: "radio",
      },
      {
        title: "Coordination",
        description: "Coordinate through shared state, not chatter.",
        href: routes.pillar("coordination"),
        icon: "network",
      },
      {
        title: "Doors",
        description: "A shell CLI, MCP tools and a runner ToolBox.",
        href: routes.pillar("doors"),
        icon: "plug",
      },
      {
        title: "Trust",
        description: "Quarantine by default, grants on your word.",
        href: routes.pillar("trust"),
        icon: "shield",
      },
      {
        title: "The fleet",
        description: "Six residents, a Gate and gravity, not walls.",
        href: routes.pillar("fleet"),
        icon: "sparkles",
      },
    ],
  },
  {
    label: "Solutions",
    items: [
      {
        title: "Use cases",
        description: "Where shared memory pays off first.",
        href: routes.useCases,
        icon: "layers",
      },
      {
        title: "Integrations",
        description: "Claude Code, Codex, Cursor, Gemini CLI and more.",
        href: routes.integrations,
        icon: "plug",
      },
      {
        title: "Compare",
        description: "How Aurora differs from a memory API.",
        href: routes.compare,
        icon: "scale",
      },
      {
        title: "Enterprise",
        description: "Local-first memory for teams that run fleets.",
        href: routes.enterprise,
        icon: "building",
      },
      {
        title: "Security",
        description: "Your data stays on your disk.",
        href: routes.security,
        icon: "shield",
      },
    ],
  },
  {
    label: "Resources",
    items: [
      {
        title: "Docs",
        description: "Concepts, guides and reference.",
        href: routes.docs,
        icon: "book",
      },
      {
        title: "Evidence",
        description: "What works, what reach still lacks, what done means.",
        href: routes.evidence,
        icon: "flask",
      },
      {
        title: "Principles",
        description: "Nine ideas, eight laws and ten decisions.",
        href: routes.principles,
        icon: "compass",
      },
      {
        title: "Changelog",
        description: "Every month of work, from the commit log.",
        href: routes.changelog,
        icon: "history",
      },
      {
        title: "Glossary",
        description: "Every term in one sentence.",
        href: routes.glossary,
        icon: "library",
      },
      {
        title: "Blog",
        description: "Notes from building Aurora.",
        href: routes.blog,
        icon: "message",
      },
      {
        title: "Forest Walks",
        description: "Long reads on how machines really work.",
        href: routes.walks,
        icon: "trees",
      },
    ],
  },
];

export const navLinks = [
  { label: "Open source", href: routes.openSource },
  { label: "Pricing", href: routes.pricing },
] as const;

export interface FooterColumn {
  readonly title: string;
  readonly links: readonly {
    label: string;
    href: string;
    external?: boolean;
  }[];
}

export const footerColumns: readonly FooterColumn[] = [
  {
    title: "Aurora",
    links: [
      { label: "Overview", href: routes.aurora },
      { label: "The record", href: routes.pillar("record") },
      { label: "Bifrost", href: routes.pillar("bus") },
      { label: "Knowledge", href: routes.pillar("knowledge") },
      { label: "Coordination", href: routes.pillar("coordination") },
      { label: "Doors", href: routes.pillar("doors") },
      { label: "Trust", href: routes.pillar("trust") },
      { label: "The fleet", href: routes.pillar("fleet") },
      { label: "The method", href: routes.pillar("method") },
    ],
  },
  {
    title: "Solutions",
    links: [
      { label: "How it works", href: routes.howItWorks },
      { label: "Use cases", href: routes.useCases },
      { label: "Integrations", href: routes.integrations },
      { label: "Enterprise", href: routes.enterprise },
      { label: "Pricing", href: routes.pricing },
    ],
  },
  {
    title: "Compare",
    links: [
      { label: "Aurora vs memory APIs", href: routes.compare },
      { label: "Aurora vs rules files", href: `${routes.compare}#rules-files` },
      {
        label: "Aurora vs chat history",
        href: `${routes.compare}#chat-history`,
      },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Docs", href: routes.docs },
      { label: "Quickstart", href: links.doc("quickstart"), external: true },
      { label: "Evidence", href: routes.evidence },
      { label: "Changelog", href: routes.changelog },
      { label: "Glossary", href: routes.glossary },
      { label: "Blog", href: routes.blog },
      { label: "Forest Walks", href: routes.walks },
    ],
  },
  {
    title: "Open source",
    links: [
      { label: "GitHub", href: links.repo, external: true },
      { label: "Principles", href: routes.principles },
      { label: "Contribute", href: routes.openSource },
      { label: "Issues", href: links.issues, external: true },
      { label: "License", href: links.license, external: true },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: routes.about },
      { label: "Security", href: routes.security },
      { label: "Contact", href: routes.contact },
      { label: "Privacy", href: routes.legal("privacy-policy") },
      { label: "Terms", href: routes.legal("terms-and-conditions") },
    ],
  },
];
