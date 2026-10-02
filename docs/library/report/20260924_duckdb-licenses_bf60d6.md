---
akashic_id: art_20260924_duckdb-licenses_bf60d6
akashic_sha: 41b81f82d5e4
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-licenses
gist: "# DuckDB deep dive -- licenses, verified from the actual LICENSE files *2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Danii"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, conducting, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:00:23"
updated: "2026-09-24T21:00:23"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-licenses_bf60d6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-licenses

# DuckDB deep dive -- licenses, verified from the actual LICENSE files

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" Agent ac03edf4b7fdb15b6 ran 19:45-19:53 local and finished; full answer verbatim. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

## The question (verbatim brief)

Today is 2026-09-24. You are gathering EVIDENCE ONLY (no judgment, no recommendation). Use WebFetch/WebSearch heavily. Load them first with ToolSearch query "select:WebSearch,WebFetch".

TASK: Verify the ACTUAL license of each project below by fetching the RAW LICENSE file from its real repository (raw.githubusercontent.com/... /LICENSE or /LICENSE.txt or /COPYING). Do NOT trust a README badge, a PyPI classifier alone, or a blog post — fetch the actual license text and report the first ~5 lines plus which license it is (Apache-2.0 / MIT / BSD-3 / PSF / public domain / dual, etc.) and the copyright holder line. Also note if there is a separate license for extensions or a CLA.

Projects and repos:
1. DuckDB — github.com/duckdb/duckdb (LICENSE) — AND separately the DuckDB `vss` extension (github.com/duckdb/duckdb-vss) and `fts` extension, and duckdb-python bindings repo (github.com/duckdb/duckdb-python) if it exists as a separate repo in 2026.
2. chDB — github.com/chdb-io/chdb (LICENSE) — and note that it embeds ClickHouse: fetch github.com/ClickHouse/ClickHouse LICENSE too. Report BOTH. ClickHouse is Apache-2.0 but confirm from the file.
3. Polars — github.com/pola-rs/polars (LICENSE)
4. Apache DataFusion — github.com/apache/datafusion (LICENSE) and its Python bindings github.com/apache/datafusion-python (LICENSE)
5. Apache Arrow — github.com/apache/arrow (LICENSE.txt) and arrow-rs if relevant
6. SQLite — sqlite.org copyright page (https://www.sqlite.org/copyright.html) — public domain; confirm exact wording
7. sqlite-vec — github.com/asg017/sqlite-vec (LICENSE) — note it may be dual Apache-2.0/MIT
8. sqlite-vss (the older one) — github.com/asg017/sqlite-vss (LICENSE) and its status (deprecated?)
9. Apache Iceberg / pyiceberg if you have time — github.com/apache/iceberg-python
10. LanceDB / Lance — github.com/lancedb/lancedb and github.com/lancedb/lance (LICENSE)
11. sqlite3 in CPython stdlib — note the module is PSF-licensed wrapper over public-domain SQLite; check what SQLite version ships with CPython 3.11 on Windows (search for it).
12. Any "DuckDB license change" or "relicensing" news in 2025-2026 — search explicitly for whether DuckDB changed license or introduced a commercial/BSL component (DuckDB Labs, MotherDuck). Report facts only.

Report as a compact table: project | repo URL of LICENSE fetched | license identified | copyright holder | notes. Flag anything you could NOT fetch. Include exact URLs.

## The answer (verbatim)

Evidence gathering complete. All licenses below were read from the actual raw license file (or sqlite.org's own page), not from badges or classifiers.

## Main table

| Project | LICENSE URL fetched | License identified | Copyright holder line | Notes |
|---|---|---|---|---|
| DuckDB core | `raw.githubusercontent.com/duckdb/duckdb/main/LICENSE` | **MIT** | `Copyright 2018-2026 Stichting DuckDB Foundation` | No SPDX header, bare MIT body |
| DuckDB `vss` ext | `raw.githubusercontent.com/duckdb/duckdb-vss/main/LICENSE` | **MIT** | `Copyright 2018-2025 Stichting DuckDB Foundation` | Separate repo, active (pushed 2026-09-23). README: "This is an experimental extension" |
| DuckDB `fts` ext | `raw.githubusercontent.com/duckdb/duckdb-fts/main/LICENSE` | **MIT** | `Copyright 2018-2025 Stichting DuckDB Foundation` | Separate repo since 2024-11-13, active |
| duckdb-python | `raw.githubusercontent.com/duckdb/duckdb-python/main/LICENSE` | **MIT** | `Copyright 2018-2026 Stichting DuckDB Foundation` | Repo **does** exist (created 2025-07-04). Default branch is `v2.0-cyanoptera`, not `main` |
| chDB | `raw.githubusercontent.com/chdb-io/chdb/main/LICENSE.txt` | **Apache-2.0** | `Copyright 2023 chDB, Inc.` | Holder line prepended above the Apache text |
| ClickHouse | `raw.githubusercontent.com/ClickHouse/ClickHouse/master/LICENSE` | **Apache-2.0** | `Copyright 2016-2026 ClickHouse, Inc.` | Confirmed from file, not from badge |
| Polars | `raw.githubusercontent.com/pola-rs/polars/main/LICENSE` | **MIT** | `Copyright (c) 2025 Ritchie Vink` + `Copyright (c) 2024 (Some portions) NVIDIA CORPORATION & AFFILIATES` | Two-holder MIT |
| Apache DataFusion | `raw.githubusercontent.com/apache/datafusion/main/LICENSE.txt` | **Apache-2.0** | NOTICE.txt: `Copyright 2019-2026 The Apache Software Foundation` | LICENSE.txt is near-stock Apache text (one ASF Aurora attribution note); holder is in NOTICE.txt |
| datafusion-python | `raw.githubusercontent.com/apache/datafusion-python/main/LICENSE.txt` | **Apache-2.0** | ASF (per ASF convention) | Active, not archived |
| Apache Arrow | `raw.githubusercontent.com/apache/arrow/main/LICENSE.txt` | **Apache-2.0** + ~40-50 bundled third-party sections | NOTICE.txt: `Copyright 2016-2026 The Apache Software Foundation` | Bundled: Chromium BSD-3, NumPy BSD-3, Boost BSL-1.0, LLVM Apache-2.0-with-exceptions, zstd/lz4/Brotli, Snappy, RapidJSON |
| arrow-rs | `raw.githubusercontent.com/apache/arrow-rs/main/LICENSE.txt` | **Apache-2.0** | ASF | One file carved out as MIT: `arrow-array/src/delta.rs` |
| SQLite | `https://www.sqlite.org/copyright.html` | **Public domain** (no license) | none — dedicated to public domain | See exact wording below |
| sqlite-vec | `.../sqlite-vec/main/LICENSE-APACHE` and `.../LICENSE-MIT` | **Dual: MIT OR Apache-2.0** | `Copyright (c) 2024 Alex Garcia` (MIT file); `Copyright 2024 Alex Garcia` (Apache boilerplate) | Plain `/LICENSE` is **404** — split files. `sqlite-dist.toml` states `"MIT OR Apache-2.0"` |
| sqlite-vss | `raw.githubusercontent.com/asg017/sqlite-vss/main/LICENSE` | **MIT** (single, not dual) | `Copyright 2023 Alexander Garcia <https://github.com/asg017/sqlite-vss>` | **Effectively deprecated** — see below |
| pyiceberg | `raw.githubusercontent.com/apache/iceberg-python/main/LICENSE` | **Apache-2.0** | NOTICE: `Copyright 2017-2026 The Apache Software Foundation` | |
| Lance | `raw.githubusercontent.com/lancedb/lance/main/LICENSE` | **Apache-2.0** | LICENSE has **no** holder line (stock template). Source files carry `SPDX-FileCopyrightText: Copyright The Lance Authors` | No NOTICE file (404) |
| LanceDB | `raw.githubusercontent.com/lancedb/lancedb/main/LICENSE` | **Apache-2.0** | LICENSE has no holder line; `Cargo.toml` authors = `LanceDB Devs <dev@lancedb.com>`, `license = "Apache-2.0"` | |
| CPython `sqlite3` | `raw.githubusercontent.com/python/cpython/3.11/Modules/_sqlite/module.c` | **zlib-style pysqlite license** inside a PSF-2.0 distribution | `Copyright (C) 2004-2010 Gerhard Häring <gh@ghaering.de>` | See below |

## Key details

**SQLite exact wording** (sqlite.org/copyright.html, page last updated 2026-01-12): "All of the code and documentation in SQLite has been dedicated to the public domain by the authors." Contributors sign **affidavits** dedicating contributions to the public domain — originals stored in a firesafe at Hwaci. SQLite is explicitly "open-source, not open-contribution": patches are not accepted from people without an affidavit. Hwaci sells a **Warranty of Title** for organizations needing legal proof. Note: the famous "here is a blessing" dedication is **not** on the copyright page — it lives in source file headers.

**CPython 3.11 / SQLite version.** Confirmed two independent ways: `PCbuild/get_externals.bat` on the CPython `3.11` branch pins `sqlite-3.45.1.0`; locally, Python 3.11.9 on this machine reports `sqlite3.sqlite_version = 3.45.1` (module `version` 2.6.0). The wrapper's license is a zlib-style grant from Gerhard Häring inside the PSF-licensed CPython distribution — the underlying SQLite stays public domain.

**sqlite-vss status.** GitHub `archived` is **false**, but last push was **2024-05-05** and the README states: "`sqlite-vss` is not in active development. Instead, my effort is now going towards `sqlite-vec`". Treat as abandoned in practice, not formally archived.

**DuckDB relicensing (item 12) — no relicense occurred.** duckdb.org/faq: "DuckDB is fully open-source under the MIT license"; "The DuckDB Foundation's statutes also ensure DuckDB remains open-source under the MIT license in perpetuity"; "All components of DuckDB are available in the free version under this license: there is no 'enterprise version' of DuckDB." No BSL component found. The real 2026 news is corporate, not licensing: `duckdb.org/2026/08/26/ducklabs-to-join-aws` (2026-08-26, by Mark Raasveldt and Hannes Mühleisen) announces DuckLabs joining AWS in early September 2026, stating "there are no changes for our projects' roadmap, licensing, and governance model" and that DuckDB, DuckLake, Quack and all extensions "will remain free and open source software under the MIT license" "under the stewardship of the non-profit DuckDB Foundation." IP sits in the Foundation, deliberately disconnected from the commercial company.

**CLAs.** ClickHouse **requires** one: CONTRIBUTING.md — "When you open your first pull request in the ClickHouse repository, a bot will ask to accept the ClickHouse Individual CLA"; corporate CLA via legal@clickhouse.com. This flows to chDB as an upstream constraint. DuckDB's CONTRIBUTING.md mentions **no** CLA or copyright assignment. chDB's CONTRIBUTING.md mentions **no** CLA. Apache projects follow the standard ASF ICLA for committers — I did not verify that from a primary ASF document this session.

**duckdb-vss dependency chain.** vss vendors `usearch` (unum-cloud), whose LICENSE is Apache-2.0 — so the MIT extension carries an Apache-2.0 component.

## Could NOT fetch / corrections to the task's assumed URLs

- `chdb-io/chdb/main/LICENSE` — **404**. Real path is `LICENSE.txt`.
- `asg017/sqlite-vec/main/LICENSE` — **404**. Real paths are `LICENSE-APACHE` + `LICENSE-MIT`.
- `lancedb/lance/main/NOTICE` — 404, no NOTICE file exists.
- `asg017/sqlite-vec/main/Cargo.toml` — 404 (no root Cargo.toml; SPDX came from `sqlite-dist.toml`).
- `duckdb.org/2026/08/26/ducklabs-aws` — 404; correct slug is `ducklabs-to-join-aws`.
- GitHub code-search API returned **401** (needs auth) — worked around via repo contents API.
- usearch's LICENSE contains only the `[yyyy] [name of copyright owner]` placeholder, so no concrete holder could be read from it.
- `duckdb.org/community_extensions/` contains **no** statement about per-extension licensing — community extension licenses would need checking individually.
- GitHub's own license detector reports sqlite-vec as **Apache-2.0 only** (it picks `LICENSE-APACHE`); the dual grant is only visible from the two files plus `sqlite-dist.toml`. Anything relying on GitHub/PyPI metadata alone would miss the MIT option.
