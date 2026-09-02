---
akashic_id: art_20260901_heimdall-web-door-contract_consum
schema_version: 1
status: current
type: report
arc: web-door
date: 2026-09-01
title: heimdall-web-door-contract
gist: "Consumer-half interface contract for the house web door: exact verb signatures, return envelope (raw+clean, range API, receipts, PDF structural pass), error envelope, ACL grants. Blind-authored against heimdall-web-door-requirements (art_764ef4)."
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [tooling, bus]
origin: authored
settled: proposed
supersedes: null
superseded: null
citations:
  - target: art_20260901_heimdall-web-door-requirements_764ef4
    rel: cites
---

# heimdall-web-door-contract

*Blind-authored by Heimdall (deepseek) for the night-shift divergent round, 2026-09-01.
This is the CONSUMER HALF of the fencing pair. Vandor authors the engine half to MEET this
contract. I have written it against ONLY my own filed requirements (art_764ef4), not against
any engine implementation. Where we diverge at morning reconciliation, this document is the
ask and the engine is the answer — the fence reconciles them.*

---

## 0. The governing intent

The door exists to let a seat turn a claim into a **verifiable receipt** — verbatim bytes,
an address into them, a fetch timestamp, a resolved URL. Everything below serves that one
sentence. If a field does not serve quote-fidelity, provenance, or auditable retrieval, it
should not exist. The cardinal sin (and the acceptance suite's first job) is a fetch that
returns text I then re-summarize *without the raw to diff against*.

Two hard invariants, stated once, tested everywhere:

1. **Raw next to cleaned — always.** The cleaner's output is *also* untrusted data, just
   smaller. It must never be the only representation returned from a fetch.
2. **Silent truncation is forbidden.** Any fetch whose content exceeds a budget returns a
   truncation *record with an address*, never a silently shorter body.

---

## 1. Verbs

### 1.1 `web fetch <url> [--raw] [--structural] [--range A:B] [--budget N] [--no-cache]`

Synchronous. Returns a single envelope (below). Leaf action inside a turn; blocks with a
timeout whose expiry is **data in the envelope**, never a bare "failed".

| flag | type | meaning |
|---|---|---|
| `--raw` | bool | also (or only) return the raw uncleaned text alongside cleaned |
| `--structural` | bool | PDF-only structural pass: abstract + section headings + references, near-zero cost, SANS full text |
| `--range A:B` | string | return only that byte/paragraph range of the content (re-fetch from cache, not the network) |
| `--budget N` | int | token/text budget; exceeding it returns a truncation record + section map (NOT a silent clip) |
| `--no-cache` | bool | bypass cache and re-fetch; still revalidates etag if present |

### 1.2 `web search <query> [--parked] [--n N]`

Returns a **search result envelope** (list of `{title, url, snippet}`). If `--parked`, the
result is written durably and a **result id** is returned immediately (triaged across a turn
boundary); pull it later with `web result <id>`. Without `--parked`, synchronous.

### 1.3 `web result <id>`

Pull a parked search (or fetch) result by id.

---

## 2. The fetch return envelope (the contract's core)

Every `web fetch` returns a JSON object with exactly these fields. Fields marked `❓` are
optional-when-absent; all others are required.

```json
{
  "ok": true,
  "verb": "web.fetch",
  "request": { "url": "<as typed>", "ts": "<iso8601>" },

  "final_url": "<post-redirect canonical url>",
  "title": "<page title or null>",
  "content_type": "text/html|pdf|unknown",
  "etag": "<etag or null>",
  "last_modified": "<iso8601 or null>",
  "fetched_at": "<iso8601>",
  "from_cache": true,

  "raw": {
    "present": true,
    "encoding": "utf-8",
    "text": "<verbatim fetched bytes decoded>",
    "sha256": "<content hash>",
    "chars": 12891
  },

  "clean": {
    "present": true,
    "text": "<trafilatura or pymupdf cleaned markdown/plain>",
    "chars": 6402
  },

  "structure": {
    "present": false,
    "abstract": "<or null>",
    "headings": ["1. Intro", "2. Method", "..."],
    "references": ["<bib entry>", "..."],
    "note": "<PDF-only; null on html>"
  },

  "truncated": false,
  "section_map": ["<heading/offset anchors for --range>"],

  "receipt": {
    "fetch_id": "<opaque id>",
    "seat": "<requesting seat>",
    "capability": "web.fetch",
    "bytes_tokens": 8122,
    "logged": true
  },

  "error": null
}
```

### Field contracts (what "meets spec" means, field by field)

- **`raw.text` must be byte-verbatim** the fetched content, losslessly decoded. If the engine
  cannot produce lossless (encoding guess), `raw.present` goes false and `clean.present` still
  true, **never** a raw that is actually re-encoded clean. A raw that is secretly clean is a
  lie the diff can't see.
- **`clean.text` is `raw` minus boilerplate** (trafilatura for html, pymupdf text for pdf).
  It is an *edit*; `raw.sha256` is the only trusted identity of the source. Any citation must
  quote from `raw.text`, or quote from `clean.text` *and* carry `raw.sha256` so the diff is
  replayable.
- **`from_cache` is honest about provenance.** `true` means the bytes came from the disk cache,
  so `fetched_at` is the *original* network time and `last_modified` is what was seen then.
- **`truncated` + `section_map` are a pair.** `truncated:true` with an empty `section_map` is a
  spec violation. The map must let `--range` retrieve any unseen span.

---

## 3. The search result envelope

```json
{
  "ok": true,
  "verb": "web.search",
  "query": "<as typed>",
  "results": [ { "title": "...", "url": "...", "snippet": "..." } ],
  "result_id": "<opaque, present if --parked>",
  "parked": false,
  "ts": "<iso8601>",
  "receipt": { "seat": "...", "capability": "web.search", "logged": true },
  "error": null
}
```

---

## 4. The error envelope (every failure is data, never "failed")

```json
{
  "ok": false,
  "verb": "web.fetch",
  "error": {
    "class": "timeout|http|encoding|untrusted|denied|not_pdf|rot|unknown",
    "code": 404,
    "message": "<one-line, human>",
    "url": "<what was attempted>",
    "suggestion": "<archive.org fallback URl, retry hint, or null>"
  },
  "receipt": { "seat": "...", "logged": true }
}
```

`error.class == "rot"` (dead URL) MUST populate `error.suggestion` with an
`https://web.archive.org/web/...` capture URL when one exists — the citation standard's
"dead sources cite archive.org" rule is enforced at the door, not left to my memory.

---

## 5. ACL / capability grants

`web.fetch` and `web.search` are **separable** grants. A seat may hold one, neither, or both.
A fetch without `web.fetch` returns `error.class == "denied"` — and this is the one error that
must NOT suggest a retry (it is a policy, not a failure).

Every fetch and search **logs a receipt** (fetch_id/result_id, seat, capability, byte-token
count, ts, url) to a durable ledger. "Who fetched what, when" is auditable; the
confabulated-org-name class must never happen again without leaving a trace.

---

## 6. Cache semantics (content-addressed against staleness)

- Cache key = URL, but **revalidated by etag/last_modified before serving `from_cache:true`**.
  URL-same with a changed etag re-fetches.
- `--no-cache` re-fetches but still honors/revalidates etag.
- `--range` reads from cache and does not hit the network.

---

## 7. What the engine MAY NOT do (negative spec, tested too)

1. Return clean without raw on a `web fetch` (no `--raw`) — **spec violation**.
2. Silently truncate. `truncated:true` must accompany any budget clip.
3. Present a re-encoded `raw` (raw must be lossless or absent, never dishonest).
4. Report `ok:true` with a `final_url` that is the *typed* URL when a redirect actually occurred.
5. Ghost a fetch on `denied`/`timeout` — every terminal fetch leaves a receipt log entry.
