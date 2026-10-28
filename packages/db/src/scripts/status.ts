import { sql } from "drizzle-orm";
import fs from "fs";
import path from "path";

import { db } from "../server";

interface JournalEntry {
  idx: number;
  version: string;
  when: number;
  tag: string;
  breakpoints: boolean;
}

interface JournalFile {
  version: string;
  dialect: string;
  entries?: JournalEntry[];
}

const JOURNAL_PATH = path.resolve("migrations/meta/_journal.json");

function loadJournalEntries(): JournalEntry[] {
  if (!fs.existsSync(JOURNAL_PATH)) {
    throw new Error(`Migrations journal not found at ${JOURNAL_PATH}`);
  }

  const journalFile = fs.readFileSync(JOURNAL_PATH, "utf-8");
  const parsed = JSON.parse(journalFile) as JournalFile;

  return [...(parsed.entries ?? [])].sort((a, b) => a.idx - b.idx);
}

function toTimestamp(value: unknown): number | null {
  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  }

  if (typeof value === "bigint") {
    return Number(value);
  }

  if (value instanceof Date) {
    return value.getTime();
  }

  return null;
}

async function fetchAppliedMigrationTimestamps(): Promise<number[]> {
  const result = await db.execute(
    sql`SELECT created_at FROM "drizzle"."__drizzle_migrations" ORDER BY created_at`,
  );

  return Array.from(result)
    .map((row) => toTimestamp((row as { created_at?: unknown }).created_at))
    .filter((timestamp): timestamp is number => timestamp !== null);
}

async function main() {
  const journalEntries = loadJournalEntries();
  const appliedTimestamps = await fetchAppliedMigrationTimestamps();
  const appliedTimestampSet = new Set(appliedTimestamps);

  const appliedMigrations = journalEntries.filter((entry) =>
    appliedTimestampSet.has(entry.when),
  );
  const pendingMigrations = journalEntries.filter(
    (entry) => !appliedTimestampSet.has(entry.when),
  );

  console.log("\nApplied migrations:");
  if (appliedMigrations.length === 0) {
    console.log("(none)");
  } else {
    appliedMigrations.forEach((entry) => console.log(`- ${entry.tag}`));
  }

  console.log("\nPending migrations:");
  if (pendingMigrations.length === 0) {
    console.log("(none)");
  } else {
    pendingMigrations.forEach((entry) => console.log(`- ${entry.tag}`));
  }
}

void main()
  .catch((err) => {
    console.error(err);
    process.exit(1);
  })
  .then(() => {
    process.exit(0);
  });
