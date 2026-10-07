# DuckDB deep dive -- postmortems: custom engines built, then ripped out

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" Agent af810b435734000c0 ran 19:48-20:11 local and finished; full answer verbatim. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

## The question (verbatim brief)

EVIDENCE-ONLY research task. Today is 2026-09-24. You have WebSearch and WebFetch available (load them first with ToolSearch query "select:WebSearch,WebFetch"). Do NOT make recommendations — gather evidence with URLs, publication dates, and DIRECT QUOTES. Postmortems are the goal.

GOAL: Find first-hand accounts of teams who BUILT their own query engine / analytical storage layer / custom columnar store and later RIPPED IT OUT and replaced it with DuckDB, ClickHouse, Polars, or DataFusion — or the reverse (replaced a vendor engine with something they built). Engineering-blog postmortems, conference talks, HN threads with author participation.

Search angles to try (use many):
- "we replaced our custom query engine with DuckDB"
- "we built our own database and regretted it"
- "migrating from our in-house analytics engine to ClickHouse"
- "we rewrote our query layer" postmortem
- "why we stopped building our own" database engine
- "replaced pandas with DuckDB" / "replaced our custom aggregation engine"
- "lessons learned building a database" 2023 2024 2025 2026
- Hacker News: "Show HN" toy database / query engine posts where the author reports effort in the comments
- "we moved off DuckDB" / "why we left ClickHouse" (the reverse direction)
- Companies known for this: Sentry, Cloudflare, Grafana, PostHog, Motherduck, Fivetran, Hex, Rill Data, Turso, Evidence.dev, Ibis, SigNoz, Quesma, Tinybird

ALSO hunt for: any source that estimates HOW LONG it takes to build a hash-join + filter + aggregate engine over Parquet. Look for people stating person-months / person-years, or "it took me N weekends", or blog series where the author dates their posts so elapsed time can be inferred.

For each find, report: URL, author, date, and the load-bearing DIRECT QUOTE about effort, duration, team size, or what broke. Prioritize 2023-2026. Flag anything you could not verify or where the date is uncertain.

## The answer (verbatim)

Research complete. Here are the findings.

---

# Postmortems: custom engines ripped out, and what building one costs

## A. Built their own engine → ripped it out for a commodity engine

**1. Arroyo — custom codegen SQL engine → Apache DataFusion + Arrow** (best single match for your brief)
URL: https://www.arroyo.dev/blog/why-arrow-and-datafusion/ · Micah Wylde (creator) · **2024-03-12**

> "DataFusion operated only in the control plane of Arroyo, while the data plane (where data is processed) was our own engine, built from scratch. This meant implementing all of the SQL operators, expressions, and functions. And since our existing implementations rely on code generation and compilation, we were looking at redoing most of this work for the next version."

> "This was going to be a huge project, reworking many fundamental aspects of the engine. But after prototyping some possible approaches, we made the decision to move forward."

What broke, in his words:

> "code gen is still *hard*. Developers need to think on multiple levels at once, and understand how the generated code interacts with its environment."
> "You're also giving up one of the biggest benefits of Rust: the compiler is very good at catching mistakes. With code gen, compile-time errors are effectively made into run-time errors."
> "outside contributors really struggled to be productive with this style of development, and found understanding the system and debugging it very challenging."

Duration and payoff: *"The Arroyo 0.10 release has been the culmination of months of effort"*; *"This evolution reflects many lessons learned over the past two years of building Arroyo."* Results: 3x throughput, 20x faster pipeline startup, 11x smaller Docker image.

**2. InfluxData — InfluxDB 1.x/Flux engine → DataFusion + Arrow + Parquet**
URL: https://www.influxdata.com/blog/flight-datafusion-arrow-parquet-fdap-architecture-influxdb/ · Andrew Lamb · **2024-02-21**

This contains the single strongest effort quote I found anywhere (verified verbatim from the live page):

> "From my personal experience working on several other databases, the scope of features required for such an engine requires effort measured in 10s of person-years to fully understand, let alone to implement and maintain. InfluxData knew this too, after investing similar orders of magnitude implementing both InfluxDB 1.x and the Flux language."
> "Instead of building another engine by ourselves, we chose to build on Apache Arrow DataFusion…"

Also on the storage layer: *"By using Parquet you get the benefits of these features without needing a database PhD or years of study to rediscover and reimplement the required techniques."*

**3. Mode — in-house "Helix" in-memory engine (VoltDB-backed) → DuckDB**
URL: https://mode.com/blog/how-we-switched-in-memory-data-engine-to-duck-db-to-boost-visual-data-exploration-speed/ · Michael Albers · **2023-04-05**
> "we had reached the limit of what VoltDB could provide"
> "if no one notices we did this, it's a success"
> "Data ordering was the biggest obstacle to overcome"

Eight engineers are named in the acknowledgements — the closest thing to a team-size signal. No duration stated.

**4. Hex — pandas as the interchange format → DuckDB over Arrow in S3**
URL: https://hex.tech/blog/lazy-dataframes/ · Dylan Scott · **2024-09-26**
> "Until recently, we relied on Pandas dataframes as the common interchange format for data."
> "streaming and dataframe creation time was responsible for upwards of 90% of the total project runtime"
> "we've seen on the order of 5-10x speedups in execution times"

**5. Arcesium — Athena → Trino → DuckDB, with hard numbers on the migration tax**
URL: https://medium.com/arcesium-engineering-blog/query-faster-query-smarter-our-move-to-duckdb-and-what-we-learned-c935128e80bc · Simran Batra · **2026-06-30** (WebFetch 403s; text retrieved via browser)
> "Over the past 18 months we migrated thousands of SQL queries across three different engines — Athena to Trino to DuckDB — and cut our query costs in half along the way. This post covers what broke, what worked, and what we wish we'd known on day one."
> "roughly 40% of incidents traced back to Athena"

This is the richest "what broke" inventory in the whole corpus — schema evolution against Parquet globs (`union_by_name`, STRUCT mismatch errors), glob-vs-explicit-file-list S3 listing costs, CTEs not materialized, nested-loop join fallbacks, memory peaks of 144GB → 20GB after `PER_THREAD_OUTPUT`, and: *"Decimal division is not supported in DuckDB… we developed a custom DuckDB extension for decimal division."*

**6. PostHog — multitenant ClickHouse warehouse → single-tenant DuckDB per org**
URL: https://posthog.com/blog/why-we-rebuilt-our-data-warehouse · Eric Duong · **2026-06-29**
> "It's not atypical for a modeling query to kick off on a schedule and run for hours or even days. This is just not something we can do on our multi-tenant CH cluster"
> "ClickHouse struggles as a general-purpose warehouse, where users need many connected sources, modeling flexibility, schema changes, and mutations"
> "We simply could not expose direct connections to the Clickhouse cluster without deepening the challenges of multitenancy"

No effort/duration/team numbers.

**7. Cloudflare — homegrown Postgres + Citus + bash/SQL/Go pipeline → ClickHouse**
URL: https://blog.cloudflare.com/http-analytics-for-6m-requests-per-second-using-clickhouse/ · **2018-03-06** (older than your window but the "what our custom thing cost us" quotes are unusually blunt)
> "thousands of lines of bash and SQL for aggregations, and thousands of lines of Go for API and Kafka consumers made the pipeline difficult to maintain and debug"
> "Zone Analytics API was struggling to serve more than 15 queries per second, so we had to introduce temporary hard rate limits for largest users"
> "Data team at Cloudflare is a small team"

**8. Sentry — custom Search/Tagstore/TSDB on Postgres + Redis → Snuba on ClickHouse**
URL: https://blog.sentry.io/2019/05/16/introducing-snuba-sentrys-new-search-infrastructure/ · **2019-05-16**. Reported outcome: the data behind Tagstore went "from terabytes to gigabytes on disk." Flagging that I sourced this via search summary, not a verbatim page read.

**9. SigNoz — Kafka + Druid → ClickHouse**
URL: https://signoz.io/blog/genesis-of-signoz/ — the founders say they were ~4–5 months into the project (mid-2020) when they abandoned Druid as too complex; ClickHouse used ~8.5x less memory for a getting-started deployment. **Date uncertain** — I did not open the page; treat the 4–5 month figure as unverified.

---

## B. The reverse direction

**1. Bauplan — forked DuckDB → DataFusion** (the cleanest "we maintained our own fork and it became a tax" account)
URL: https://bauplanlabs.com/post/duck-hunt-moving-bauplan-from-duckdb-to-datafusion · Jacopo Tagliabue · **2025-11-05** (verified verbatim via browser)

> "the major problem is that DuckDB expected to control I/O (as any normal database would), so we forked it and added a new API, EXPLAIN SCANS"
> "some other issues were more DuckDB specific though ('It's definitely you' kind of thing), e.g. weird memory spikes when dealing with Arrow objects and **the growing cost of keeping our fork up to date**."
> "we slowly came to realize that DuckDB is more of an open-source *product* than an open-source *project*"
> "it was time to look elsewhere for a more stable solution; not a product we could modify 'in the margins', but a *project* that we could mold"

On the new engine being *hackable* "even for a company of our size" — and the cost didn't vanish, it moved: *"We are maintaining a fork of iceberg-rust while fixes for these issues make it upstream."* Payoff: ~2x faster p50. Context: "a year of production workloads at scale" on DuckDB; "our small and mighty team"; "hundreds of thousands of data pipelines."

**2. Datadog Husky — built their own third-generation event store, and published the clock**
URL: https://www.datadoghq.com/blog/engineering/introducing-husky/ · Richard Artoul & Cecilia Watt · **2022-05-17**
> "We needed to own the storage engine from the ground up to control our destiny and deliver the functionality that our product teams were asking for."
> **"it still took us over a year and a half between writing our first line of code to fully migrating a product to Husky."**

Gen-1 was Elasticsearch; Gen-2 was stateless nodes, shard routers, and *custom query engines*. They dual-wrote and shadow-queried 100% of production load for months before cutting over.

The arc closes: the 2025 follow-up (https://www.datadoghq.com/blog/engineering/husky-query-architecture/ · Sami Tabet · **2025-10-01**) says they are *"looking at adopting standards like Apache Arrow, Apache Parquet, Substrait, and Apache DataFusion to decouple components strategically."*

**3. Honeycomb — Retriever, their own distributed column store**
https://www.honeycomb.io/resources/why-we-built-our-own-distributed-column-store (Sam Stokes, Strange Loop 2017). I found **no** public Honeycomb retrospective expressing regret or quantifying Retriever's maintenance cost — I looked specifically and came up empty. Flagging as a gap, not an absence.

**4. Quesma — the money postmortem** (adjacent: built a translation layer, not an engine, but it's a real first-hand failure account)
URL: https://quesma.com/blog/database-gateway-postmortem/ · Jacek Migdal · **2025-11-04**
> "Our Elasticsearch-to-ClickHouse MVP took 9 months instead of 5."
> "Raising our initial $2.5 million proved to be more than doable."
> "we were never their top 5 priority. Usually we ranked around 12th priority"
> "Around 20 companies use us regularly, mostly for free"
> "We ended up selling our IP as an asset sale to Hydrolix"

---

## C. How long it takes to build a hash-join + filter + aggregate engine over Parquet

This was the hardest thing to source. **No one publishes a clean person-month figure** — and the SIGMOD paper explicitly names that as an open question (see below). Here is everything I found that bears on it, strongest first.

| Source | Figure | Quote |
|---|---|---|
| **Andrew Lamb, InfluxData, 2024-02-21** ([link](https://www.influxdata.com/blog/flight-datafusion-arrow-parquet-fdap-architecture-influxdb/)) | **10s of person-years** | "the scope of features required for such an engine requires effort measured in 10s of person-years to fully understand, let alone to implement and maintain" |
| **Amey Chaugule, Denormalized, podcast 2024-09-12** ([transcript](https://techontherocks.show/3/transcript)) | **2.5 months on DataFusion vs ~1 year from scratch** | "it would have taken, it took us like… two and a half months of really coding to get our first prototype out, you know, that where we could compare things, it would have taken us like a year to build the same thing without DuckDB. That just goes without saying." |
| **Nitay Joffe, same episode** | **millions of dollars, ~5 years** | "historically it would take millions of dollars and probably five years before you saw a result. And now… in a couple of months, you can get a full data system up and running" |
| **Datadog, 2022-05-17** | **18 months** (well-resourced team, first line of code → first product migrated) | "it still took us over a year and a half between writing our first line of code to fully migrating a product to Husky." |
| **DuckDB's own timeline** ([duckdb.org/history](https://duckdb.org/history/)) | **6 years, 2 people at the start** | "Mark Raasveldt and Hannes Mühleisen began developing DuckDB in 2018"; v0.1 announced at SIGMOD 2019; v1.0.0 on 2024-06-03 — "Six years after the first code was written, DuckDB had moved from a research project into production systems" |
| **Andy Grove (DataFusion's original author), 2018-11-04** ([link](https://andygrove.io/2018/11/datafusion-2019/)) | solo, side-project, burnout | "all out-of-hours work in addition to my day job" · "This was a period of intense activity in the first six months of 2018" · **"Trying to build a distributed compute platform alone in my spare time is not a good idea"** · "It had become like a second job in many ways" · "I have pretty much stopped working on this project for the past five months" |
| **Denormalized blog, 2024-11-19** ([link](https://www.denormalized.io/blog/building-databases)) — titled "Building Databases over a Weekend", Amey Chaugule | qualitative | "Databases are some of the most complex pieces of software conceived since the advent of the computing age" · **"the bar for writing a functional query engine with table stakes features remains strikingly high"** · "you need to nail *all that* before you can get around to writing your use-case specific features" |

**The academic position, and an explicit admission that the number does not exist.** *Apache Arrow DataFusion: a Fast, Embeddable, Modular Analytic Query Engine*, Lamb et al., SIGMOD-Companion '24, 2024-06-09 (https://andrew.nerdnetworks.org/pdf/SIGMOD-2024-lamb.pdf, DOI 10.1145/3626246.3653368). Verbatim from the extracted text:

> "building such a system is expensive and requires substantial commercial and/or research funding, given the extensive software engineering required." (§1)

> "**Evaluating additional lines of code or engineering hours required to build a system from scratch without DataFusion**, a study of how DataFusion's extensibility APIs are used in practice, and a systematic evaluation of end to end performance of DataFusion based applications would all help explore the trade offs encountered building systems using modular query engines." (§9.1 Future Research)

That last one is load-bearing for your question: the authors of the field's reference paper list the quantification of build-from-scratch effort as **unsolved future work**. If you want a number, you will be inferring it, not citing it.

**First-hand HN accounts (older, 2018, but direct and quantified)** — https://news.ycombinator.com/item?id=16995612 ("Never Write Your Own Database"):
- `lmilcin`: "The project took 2 years to complete. I spent maybe a month designing, implementing and perfecting the database." (<1k LOC of ANSI C inside a ~70k LOC app)
- `rdtsc`: "I have written my own database. In 3 months. Shipped it and installed in customers' sites"
- `hyc_symas` (LMDB author): ~2 years evaluating BerkeleyDB before concluding a custom engine was warranted

And from https://news.ycombinator.com/item?id=37718566, `mjb` (Marc Brooker, AWS) — the organizational-cost framing:
> "a team that depends on a custom database tends to become a database team rather than an anything else team."
> "Going from demo to running something in production is vastly harder and more expensive and requires a completely different mind set."

**Vendor estimate, flagged as marketing:** Querri (https://querri.com/build-vs-buy/engineering-burden/, undated, references 2024 data) puts in-house customer-facing analytics at "6 to 12 months" with "1.5 to 2 engineers" and "$470K to $740K over three years." Salary basis cited is the Stack Overflow 2024 survey. Directionally consistent with the others but it is a buy-side sales page.

---

## Caveats and things I could not verify

- **Transcript artifact.** In the Denormalized quote, the speaker says "without DuckDB" where the entire surrounding context is about **DataFusion**. It is an auto-generated transcript; treat "DuckDB" there as a transcription slip. The timing numbers (2.5 months / 1 year) are unambiguous.
- **Unverified quote — do not use.** Search surfaced an attributed Hannes Mühleisen line, "Mark and I basically did nothing else—evenings, weekends—just hacking on DuckDB for a couple of years." I could **not** find it on any page I fetched (the MotherDuck interview page is a video embed; BigDATAwire 403s). Treat as unsourced.
- **Dates I did not confirm by opening the page:** Sentry Snuba (2019-05-16), SigNoz genesis (4–5 months figure).
- **`tamnd/rudb`** (https://github.com/tamnd/rudb) surfaced as "an embedded analytical database written in Rust, compatible with DuckDB… The bar is 10x DuckDB on ClickBench." GitHub API says the repo was **created 2026-09-10**, has 2 stars, and was pushed minutes before I checked. A two-week-old repo claiming 10x DuckDB across ClickBench, TPC-H SF100, TPC-DS, JOB and CEB is not corroborated evidence of anything; I'd treat it as an artifact rather than a datapoint.
- **The gap in the literature.** I found no team that published a person-month accounting of building their own hash-join/filter/aggregate-over-Parquet engine *and* then ripping it out. Arroyo and Mode are the closest, and neither gives numbers for the original build. The two hard elapsed-time anchors that exist are Datadog's 18 months (big team, storage engine) and DuckDB's 6 years to 1.0 (2 people, full engine).
- One asymmetry worth naming: I searched the "we moved off DuckDB / why we left ClickHouse" direction from four different angles and Bauplan is the **only** substantive first-hand account I found. Cloudflare's TimescaleDB-over-ClickHouse post is a per-project choice, not a migration away. The corpus is heavily skewed toward adoption stories, which is itself a selection effect worth discounting for.
