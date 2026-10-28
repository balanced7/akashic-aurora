#!/usr/bin/env node
/**
 * Builds the changelog and activity data for the marketing site from the Aurora git history.
 *
 * Usage: node scripts/generate-aurora-history.mjs <path-to-aurora-repo>
 * Writes: src/modules/marketing/content/generated/aurora-history.json
 */
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import path from "node:path";

const repo = process.argv[2] ?? process.env.AURORA_REPO;
if (!repo) {
  console.error(
    "Pass the path to the Aurora repo: node scripts/generate-aurora-history.mjs <path>",
  );
  process.exit(1);
}

const SEP = "\u001f";
const raw = execFileSync(
  "git",
  [
    "-C",
    repo,
    "log",
    "--no-merges",
    `--format=%H${SEP}%ad${SEP}%s`,
    "--date=short",
  ],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
);

const CONVENTIONAL =
  /^(?<type>[a-z]+)(?:\((?<scope>[^)]+)\))?!?:\s*(?<subject>.+)$/;
const TYPES = [
  "feat",
  "fix",
  "docs",
  "test",
  "refactor",
  "chore",
  "perf",
  "ci",
  "style",
  "build",
];

const commits = raw
  .trim()
  .split("\n")
  .map((line) => {
    const [sha, date, subject] = line.split(SEP);
    const match = CONVENTIONAL.exec(subject ?? "");
    const type = match?.groups?.type ?? "other";
    return {
      sha: sha.slice(0, 7),
      date,
      type: TYPES.includes(type) ? type : "other",
      scope: match?.groups?.scope ?? null,
      subject: match?.groups?.subject ?? subject,
    };
  });

const months = new Map();
for (const commit of commits) {
  const key = commit.date.slice(0, 7);
  const month = months.get(key) ?? { month: key, total: 0, types: {} };
  month.total += 1;
  month.types[commit.type] = (month.types[commit.type] ?? 0) + 1;
  months.set(key, month);
}

// Counts only. Raw subjects carry internal names and shorthand, so curated highlights live in
// src/modules/marketing/content/changelog.ts instead.
const monthList = [...months.values()]
  .sort((a, b) => b.month.localeCompare(a.month))
  .map((month) => ({
    month: month.month,
    total: month.total,
    types: month.types,
  }));

const days = {};
for (const commit of commits) days[commit.date] = (days[commit.date] ?? 0) + 1;

const out = {
  generatedFrom: "git log --no-merges",
  generatedAt: commits[0]?.date ?? null,
  firstCommit: commits.at(-1)?.date ?? null,
  totalCommits: commits.length,
  typeTotals: Object.fromEntries(
    [...TYPES, "other"].map((type) => [
      type,
      commits.filter((commit) => commit.type === type).length,
    ]),
  ),
  months: monthList,
  days,
};

const target = path.join(
  import.meta.dirname,
  "../src/modules/marketing/content/generated/aurora-history.json",
);
writeFileSync(target, `${JSON.stringify(out)}\n`);
console.log(
  `wrote ${commits.length} commits across ${monthList.length} months to ${path.relative(process.cwd(), target)}`,
);
