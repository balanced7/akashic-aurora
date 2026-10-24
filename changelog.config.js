// Conventional Commit settings for git-cz (`npx git-cz`), and the single source of the
// type and scope lists that commitlint.config.ts enforces.
//
// Subject format: {emoji}{type}{scope}: {subject}  e.g. `🎸feat(core): add env_paths`
// The emoji is optional: commitlint accepts `feat(core): add env_paths` as well.

const types = {
  chore: { description: "Build process, config or auxiliary tooling", emoji: "🤖", value: "chore" },
  ci: { description: "CI related changes", emoji: "🎡", value: "ci" },
  docs: { description: "Documentation only changes", emoji: "✏️", value: "docs" },
  feat: { description: "A new feature", emoji: "🎸", value: "feat" },
  fix: { description: "A bug fix", emoji: "🐛", value: "fix" },
  perf: { description: "A code change that improves performance", emoji: "⚡️", value: "perf" },
  refactor: {
    description: "A code change that neither fixes a bug nor adds a feature",
    emoji: "💡",
    value: "refactor",
  },
  release: { description: "Create a release commit", emoji: "🏹", value: "release" },
  revert: { description: "Revert an earlier commit", emoji: "⏪", value: "revert" },
  style: { description: "Markup, white-space, formatting, missing semi-colons...", emoji: "💄", value: "style" },
  test: { description: "Adding or fixing tests", emoji: "💍", value: "test" },
};

// Scopes follow the repo's subsystems (see docs/ARCHITECTURE.md). Add one here when a new area
// needs its own; `global` is for changes that genuinely span the whole repo.
const scopes = [
  "",
  "agent",
  "arsenal",
  "bifrost",
  "cli",
  "config",
  "coord",
  "core",
  "deploy",
  "deps",
  "docs-site",
  "eye",
  "global",
  "hooks",
  "mcp",
  "ops",
  "portability",
  "recall",
  "research",
  "security",
  "store",
  "tools",
  "wake",
  "world",
];

module.exports = {
  disableEmoji: false,
  format: "{emoji}{type}{scope}: {subject}",
  list: Object.keys(types),
  maxMessageLength: 96,
  minMessageLength: 3,
  questions: ["type", "scope", "subject", "body", "breaking", "issues"],
  scopes,
  types,
};
