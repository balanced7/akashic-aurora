"""The manuals shelf: reference documents, cut into labelled chunks an agent can search.

Born 2026-09-24. Daniil's Spectrum contact described "feeding manuals and reference pdfs into
duckdb" so agents read a few relevant passages instead of a whole manual. The DuckDB dive
(research/reviewed/duckdb-deep-dive-synthesis-2026-09-24.md) found no special parsing inside
DuckDB: its own agent docs are sections chunked ahead of time (title, section, breadcrumb, url,
version, text), searched with BM25. The house already had BM25 in SQLite FTS5 (core/eye), so
this package supplies the missing half, clean labelled chunks, and keeps SQLite as the engine.

    convert  -- a document (Markdown, DocC JSON, HTML, PDF) becomes titled Sections
    chunk    -- Sections become bounded Chunks, each carrying its breadcrumb and source url
    shelf    -- chunks live in SQLite with an FTS5 index; ingest is incremental, search is
                BM25 with the heading path weighted above the body, answers are size-capped,
                and a zero names what was searched

Vendor manuals are copyrighted: the corpus and the index live under data_root()/state/manuals
(git-ignored), never in this public repo.
"""
