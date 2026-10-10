#!/usr/bin/env node
// The docs verifier: Hemingway-style prose checks plus structure and link checks.
//
//   node scripts/check-docs.mjs            # report every page, exit 1 on any failure
//   node scripts/check-docs.mjs --verbose  # also print each flagged sentence
//
// Prose rules follow the Hemingway Editor: a sentence of 14+ words is "hard" at an ARI
// grade of 10 and "very hard" at 14; adverbs, passive voice and words with a simpler
// alternative are counted against a budget. Code, links' URLs, tables and JSX are not prose
// and are stripped first. Concept pages get the strictest budgets.

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const ROOT = new URL('../content/docs/', import.meta.url).pathname;
const VERBOSE = process.argv.includes('--verbose');

// ---------------------------------------------------------------- budgets

const BUDGETS = {
  concepts: { grade: 8, avgWords: 15, maxWords: 25, veryHard: 0, hardShare: 0.1, passiveShare: 0.1, adverbShare: 0.08 },
  default: { grade: 9, avgWords: 17, maxWords: 30, veryHard: 1, hardShare: 0.15, passiveShare: 0.15, adverbShare: 0.1 },
};

// Words a plainer word can replace (Hemingway's "simpler alternative" list, trimmed to
// what technical prose actually trips on).
const SIMPLER = {
  utilize: 'use', utilise: 'use', utilization: 'use', leverage: 'use', facilitate: 'help',
  'in order to': 'to', numerous: 'many', approximately: 'about', commence: 'start',
  terminate: 'end', additional: 'more', assist: 'help', demonstrate: 'show',
  sufficient: 'enough', subsequently: 'later', 'prior to': 'before', 'in the event that': 'if',
  'a number of': 'some', 'is able to': 'can', 'are able to': 'can', endeavor: 'try',
  ascertain: 'find out', necessitate: 'need', 'with regard to': 'about', 'in addition': 'also',
  obtain: 'get', modify: 'change', component: 'part', functionality: 'feature',
  methodology: 'method', paradigm: 'model', robust: 'strong', seamless: 'smooth',
  'due to the fact that': 'because', whereby: 'where', thereby: 'so', henceforth: 'from now on',
};

// Filler and hedges: they add length, never meaning.
const FILLER = ['very', 'really', 'just', 'quite', 'simply', 'basically', 'actually',
  'extremely', 'obviously', 'clearly', 'essentially', 'literally', 'totally'];

// -ly words that are not adverbs.
const NOT_ADVERBS = new Set(['only', 'early', 'family', 'reply', 'apply', 'supply', 'daily',
  'holy', 'likely', 'ugly', 'fly', 'rely', 'july', 'italy', 'ally', 'belly', 'jelly', 'friendly',
  'lonely', 'silly', 'imply', 'multiply', 'assembly', 'anomaly', 'butterfly', 'monopoly',
  'weekly', 'monthly', 'hourly', 'yearly', 'costly', 'orderly', 'timely', 'lively', 'holly',
  'unlikely', 'comply', 'emily', 'kelly', 'polly', 'rally', 'tally', 'bully', 'fully', 'reply',
  'nightly', 'elderly', 'deadly', 'lovely', 'oily', 'curly', 'hilly', 'chilly', 'gently']);

const BE = '(?:am|is|are|was|were|be|been|being|gets|got|get|getting)';
const PASSIVE = new RegExp(`\\b${BE}\\s+(?:\\w+ly\\s+)?(\\w+ed|${irregulars()})\\b`, 'gi');

function irregulars() {
  return ['written', 'known', 'built', 'done', 'given', 'kept', 'made', 'held', 'sent', 'shown',
    'seen', 'taken', 'told', 'found', 'left', 'lost', 'run', 'read', 'set', 'put', 'hit', 'won',
    'brought', 'bought', 'caught', 'thought', 'taught', 'sold', 'spent', 'stolen', 'broken',
    'chosen', 'driven', 'eaten', 'fallen', 'forgotten', 'frozen', 'hidden', 'ridden', 'risen',
    'shaken', 'spoken', 'sworn', 'torn', 'worn', 'woken', 'drawn', 'grown', 'thrown', 'blown',
    'begun', 'sung', 'swung', 'hung', 'struck', 'stuck', 'bound', 'ground', 'wound', 'fed',
    'led', 'met', 'paid', 'said', 'laid', 'meant', 'dealt', 'felt', 'heard', 'shut', 'split',
    'spread', 'cast', 'cut', 'let', 'quit', 'rewritten', 'overwritten', 'rebuilt', 'withheld']
    .join('|');
}

// ---------------------------------------------------------------- files

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith('.mdx') ? [p] : [];
  });
}

function parse(file) {
  const raw = readFileSync(file, 'utf8');
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  const front = {};
  if (m) {
    for (const line of m[1].split('\n')) {
      const kv = line.match(/^(\w+):\s*(.*)$/);
      if (kv) front[kv[1]] = kv[2].replace(/^['"]|['"]$/g, '').replace(/\\"/g, '"');
    }
  }
  const body = m ? raw.slice(m[0].length) : raw;
  const rel = relative(ROOT, file).split(sep).join('/');
  const slug = rel.replace(/\.mdx$/, '').replace(/(^|\/)index$/, '');
  return { file, rel, slug, url: `/docs${slug ? `/${slug}` : ''}`, front, body, raw, rawFront: m ? m[1] : '' };
}

// ---------------------------------------------------------------- prose extraction

function toProse(body) {
  return body
    .replace(/```[\s\S]*?```/g, '\n\n') // code blocks
    .replace(/^import .*$/gm, '')
    .replace(/^\s*<\/?[A-Z][^>]*>\s*$/gm, '\n\n') // JSX block tags on their own line
    .replace(/<[A-Z][^>]*\/>/g, '') // self-closing JSX
    .replace(/<\/?[A-Za-z][^>]*>/g, '') // remaining tags (keep inner text)
    .replace(/^\s*\|.*\|\s*$/gm, '\n\n') // tables are reference, not prose
    .replace(/^#+\s.*$/gm, '\n\n') // headings are labels, not sentences
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links keep their text
    .replace(/`[^`]+`/g, 'code') // inline code counts as one plain word
    .replace(/\*\*|__|\*|_(?=\w)|(?<=\w)_/g, '')
    .replace(/^\s*[-*+]\s+/gm, '\n') // each list item is its own unit
    .replace(/^\s*\d+\.\s+/gm, '\n')
    .replace(/^>\s?/gm, '');
}

function sentences(prose) {
  const out = [];
  for (const para of prose.split(/\n\s*\n/)) {
    const flat = para.replace(/\s+/g, ' ').trim();
    if (!flat) continue;
    // A list item or label with no terminal punctuation still counts as one unit.
    for (const s of flat.split(/(?<=[.!?:]["”')]?)\s+(?=[A-Z0-9"“(`])/)) {
      const t = s.trim();
      if (t && /[A-Za-z]/.test(t)) out.push(t);
    }
  }
  return out;
}

const words = (s) => s.match(/[A-Za-z0-9][A-Za-z0-9'’-]*/g) ?? [];
const letters = (ws) => ws.reduce((n, w) => n + w.replace(/[^A-Za-z0-9]/g, '').length, 0);

function ari(ws, sentenceCount) {
  if (!ws.length) return 0;
  return 4.71 * (letters(ws) / ws.length) + 0.5 * (ws.length / sentenceCount) - 21.43;
}

// ---------------------------------------------------------------- checks

function prose(page) {
  const ss = sentences(toProse(page.body));
  const all = ss.flatMap(words);
  const stats = { sentences: ss.length, words: all.length, hard: [], veryHard: [], passive: [],
    adverbs: [], simpler: [], filler: [], long: [] };
  for (const s of ss) {
    const ws = words(s);
    if (ws.length >= 14) {
      const level = ari(ws, 1);
      if (level >= 14) stats.veryHard.push(s);
      else if (level >= 10) stats.hard.push(s);
    }
    for (const m of s.matchAll(PASSIVE)) stats.passive.push(`${m[0]}  ←  ${s}`);
    for (const w of ws) {
      const lw = w.toLowerCase();
      const tail = lw.split('-').pop(); // judge "append-only" by "only"
      if (tail.length > 4 && tail.endsWith('ly') && !NOT_ADVERBS.has(tail)) stats.adverbs.push(w);
      if (FILLER.includes(lw)) stats.filler.push(`${w}  ←  ${s}`);
    }
    for (const [hard, easy] of Object.entries(SIMPLER)) {
      if (new RegExp(`\\b${hard}\\b`, 'i').test(s)) stats.simpler.push(`${hard} → ${easy}  ←  ${s}`);
    }
  }
  stats.grade = ari(all, Math.max(ss.length, 1));
  stats.avg = all.length / Math.max(ss.length, 1);
  return { ss, stats };
}

function kind(page) {
  return page.rel.startsWith('concepts/') ? 'concepts' : 'default';
}

// <SectionCard section="x"> links /docs/concepts/x (components/core-parts.tsx).
function links(page) {
  return [
    ...page.body.matchAll(
      /\]\((\/docs[^)#\s]*)(#[^)\s]*)?\)|href="(\/docs[^"#]*)|<SectionCard section="([a-z-]+)"/g,
    ),
  ].map((m) => (m[4] ? `/docs/concepts/${m[4]}` : (m[1] ?? m[3]).replace(/\/$/, '')));
}

// ---------------------------------------------------------------- main

const pages = walk(ROOT).map(parse);
const byUrl = new Map(pages.map((p) => [p.url, p]));
const failures = [];
const fail = (page, msg) => failures.push(`${page.rel}: ${msg}`);
const rows = [];

for (const page of pages) {
  for (const line of (page.body === page.raw ? '' : page.rawFront).split('\n')) {
    const kv = line.match(/^(\w+):\s*(.*)$/);
    if (kv && !/^["']/.test(kv[2]) && /: | #|^[[{&*!|>%@`]/.test(kv[2])) fail(page, `frontmatter ${kv[1]} needs quotes (YAML): ${kv[2]}`);
  }
  if (!page.front.title) fail(page, 'frontmatter has no title');
  if (!page.front.description) fail(page, 'frontmatter has no description');
  for (const l of links(page)) if (!byUrl.has(l)) fail(page, `broken link ${l}`);

  if (page.rel.startsWith('reference/glossary')) continue; // the glossary has its own rules
  const b = BUDGETS[kind(page)];
  const { stats } = prose(page);
  const n = Math.max(stats.sentences, 1);
  const tooLong = sentences(toProse(page.body)).filter((s) => words(s).length > b.maxWords);
  rows.push([page.rel, stats.sentences, stats.avg.toFixed(1), stats.grade.toFixed(1),
    stats.hard.length, stats.veryHard.length, stats.passive.length, stats.adverbs.length]);

  if (stats.grade > b.grade) fail(page, `reading grade ${stats.grade.toFixed(1)} > ${b.grade}`);
  if (stats.avg > b.avgWords) fail(page, `average sentence ${stats.avg.toFixed(1)} words > ${b.avgWords}`);
  if (stats.veryHard.length > b.veryHard) fail(page, `${stats.veryHard.length} very hard sentence(s) > ${b.veryHard}`);
  if (stats.hard.length > Math.max(1, Math.floor(n * b.hardShare))) fail(page, `${stats.hard.length} hard sentences > ${Math.max(1, Math.floor(n * b.hardShare))}`);
  if (stats.passive.length > Math.max(1, Math.round(n * b.passiveShare))) fail(page, `${stats.passive.length} passive > ${Math.max(1, Math.round(n * b.passiveShare))}`);
  if (stats.adverbs.length > Math.max(1, Math.round(n * b.adverbShare))) fail(page, `${stats.adverbs.length} adverbs > ${Math.max(1, Math.round(n * b.adverbShare))} (${stats.adverbs.join(', ')})`);
  if (stats.simpler.length) fail(page, `simpler word available:\n    ${stats.simpler.join('\n    ')}`);
  if (stats.filler.length) fail(page, `filler words:\n    ${stats.filler.join('\n    ')}`);
  for (const s of tooLong) fail(page, `sentence over ${b.maxWords} words: ${s}`);

  if (VERBOSE) {
    for (const s of stats.veryHard) console.log(`  VERY HARD  ${page.rel}: ${s}`);
    for (const s of stats.hard) console.log(`  HARD       ${page.rel}: ${s}`);
    for (const s of stats.passive) console.log(`  PASSIVE    ${page.rel}: ${s}`);
  }

  if (kind(page) === 'concepts' && !page.rel.endsWith('index.mdx')) {
    const d = page.front.description ?? '';
    if (words(d).length > 25) fail(page, `description is ${words(d).length} words; the one-sentence essence must be <= 25`);
    if ((d.match(/[.!?](\s|$)/g) ?? []).length > 1) fail(page, 'description must be one sentence');
    if (!/^## How it connects$/m.test(page.body)) fail(page, 'missing "## How it connects"');
    const connects = page.body.split(/^## How it connects$/m)[1]?.split(/^## /m)[0] ?? '';
    if (!/\]\(\/docs\/concepts\//.test(connects)) fail(page, '"How it connects" links no other concept');
  }
}

// Glossary: every concept page has an entry, and every entry links a real page.
const glossary = byUrl.get('/docs/reference/glossary');
const concepts = pages.filter((p) => kind(p) === 'concepts' && !p.rel.endsWith('index.mdx'));
if (glossary) {
  const linked = new Set(links(glossary));
  for (const c of concepts) if (!linked.has(c.url)) fail(glossary, `no entry links ${c.url}`);
  for (const entry of glossary.body.split(/\n\s*\n/).filter((e) => /^\*\*[^*]+\*\*:/.test(e))) {
    const def = entry.split('\n').filter((l) => l && !l.startsWith('**') && !l.startsWith('_Avoid_')).join(' ');
    const text = toProse(def).trim();
    const n = (text.match(/[.!?](\s|$)/g) ?? []).length;
    if (n > 1) fail(glossary, `entry is ${n} sentences: ${entry.split('\n')[0]}`);
    if (words(text).length > 30) fail(glossary, `entry over 30 words: ${entry.split('\n')[0]}`);
  }
} else {
  failures.push('reference/glossary.mdx is missing');
}

// Orphans: every page must be linked from some other page (the home page is the root).
const inbound = new Set(pages.flatMap((p) => links(p).filter((l) => l !== p.url)));
for (const p of pages) if (p.url !== '/docs' && !inbound.has(p.url)) fail(p, 'orphan: no other page links here');

// ---------------------------------------------------------------- report

const head = ['page', 'sent', 'avg', 'grade', 'hard', 'v.hard', 'passive', 'adverbs'];
const widths = head.map((h, i) => Math.max(h.length, ...rows.map((r) => String(r[i]).length)));
const fmt = (r) => r.map((c, i) => String(c).padEnd(widths[i])).join('  ');
console.log(fmt(head));
for (const r of rows.sort()) console.log(fmt(r));
console.log();
if (failures.length) {
  console.log(`FAIL: ${failures.length} finding(s)`);
  for (const f of failures) console.log(`- ${f}`);
  process.exit(1);
}
console.log(`PASS: ${pages.length} pages`);
