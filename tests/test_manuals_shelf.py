"""Pins for the manuals shelf (2026-09-24), registered before the build.

WHY. Daniil's Spectrum contact described "feeding manuals and reference pdfs into duckdb" so
agents read a few relevant passages instead of a whole manual. The dive found no special
parsing inside DuckDB: its own agent docs are pre-chunked sections (title, section,
breadcrumb, url, version, text) searched with BM25. The house already has BM25 (SQLite FTS5,
core/eye). The shelf adds the missing half: turning documents into clean, labelled chunks.
research/reviewed/duckdb-deep-dive-synthesis-2026-09-24.md; his first manuals are Apple's
Human Interface Guidelines and Samsung's One UI docs, kept out of this public repo.

Every fixture here is invented text, never a vendor's.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.manuals import convert, chunk, shelf as shelf_mod  # noqa: E402


# ---- conversion ------------------------------------------------------------------

MD = """# Kettle Handbook

Intro line about the kettle.

## Filling

Pour water up to the MAX mark. Never fill above it.

### Cold water only

Hot tap water can carry scale.

## Descaling

Use a vinegar rinse every month.
"""


def test_markdown_sections_carry_breadcrumbs(tmp_path):
    p = tmp_path / "kettle.md"
    p.write_text(MD, encoding="utf-8")
    doc = convert.to_document(p)
    assert doc.title == "Kettle Handbook"
    paths = [s.path for s in doc.sections]
    assert ("Kettle Handbook", "Filling", "Cold water only") in paths
    cold = next(s for s in doc.sections if s.path[-1] == "Cold water only")
    assert "scale" in cold.text


DOCC = {
    "metadata": {"title": "Switches", "role": "article"},
    "abstract": [{"type": "text", "text": "A switch toggles one setting."}],
    "primaryContentSections": [{"kind": "content", "content": [
        {"type": "paragraph", "inlineContent": [{"type": "text", "text": "Opening words."}]},
        {"type": "heading", "level": 2, "text": "Best practices", "anchor": "Best-practices"},
        {"type": "paragraph", "inlineContent": [
            {"type": "text", "text": "Label it clearly. See "},
            {"type": "reference", "identifier": "doc://x/toggles", "isActive": True},
            {"type": "text", "text": "."}]},
        {"type": "unorderedList", "items": [
            {"content": [{"type": "paragraph", "inlineContent": [{"type": "text", "text": "Keep labels short."}]}]},
            {"content": [{"type": "paragraph", "inlineContent": [
                {"type": "emphasis", "inlineContent": [{"type": "text", "text": "Avoid"}]},
                {"type": "text", "text": " double negatives."}]}]}]},
        {"type": "aside", "style": "note", "name": "Note", "content": [
            {"type": "paragraph", "inlineContent": [{"type": "text", "text": "Switches act at once."}]}]},
        {"type": "heading", "level": 3, "text": "Sizing", "anchor": "Sizing"},
        {"type": "table", "header": "row", "rows": [
            [[{"type": "paragraph", "inlineContent": [{"type": "text", "text": "Platform"}]}],
             [{"type": "paragraph", "inlineContent": [{"type": "text", "text": "Height"}]}]],
            [[{"type": "paragraph", "inlineContent": [{"type": "text", "text": "Phone"}]}],
             [{"type": "paragraph", "inlineContent": [{"type": "text", "text": "31 pt"}]}]]]},
    ]}],
    "references": {"doc://x/toggles": {"title": "Toggles", "url": "/design/toggles"}},
}


def test_docc_json_becomes_sections(tmp_path):
    p = tmp_path / "switches.json"
    p.write_text(json.dumps(DOCC), encoding="utf-8")
    doc = convert.to_document(p, url="https://example.test/design/switches")
    assert doc.title == "Switches"
    best = next(s for s in doc.sections if s.path[-1] == "Best practices")
    assert "See Toggles." in best.text                       # references resolve to titles
    assert "- Keep labels short." in best.text               # lists survive as lists
    assert "Note: Switches act at once." in best.text        # asides keep their label
    assert best.anchor == "Best-practices"
    sizing = next(s for s in doc.sections if s.path[-1] == "Sizing")
    assert sizing.path == ("Switches", "Best practices", "Sizing")
    assert "Phone" in sizing.text and "31 pt" in sizing.text  # tables keep their cells


HTML = """<html><head><title>Lamp Guide | Site</title></head><body>
<nav>Home Products Support Cookie settings</nav>
<main><h1>Lamp Guide</h1><p>Welcome.</p>
<h2>Bulbs</h2><p>Use a warm bulb under 9 watts.</p>
<h2>Cleaning</h2><p>Unplug before wiping the shade.</p></main>
<footer>Copyright notice Terms Privacy</footer></body></html>"""


def test_html_keeps_the_content_and_drops_the_chrome(tmp_path):
    p = tmp_path / "lamp.html"
    p.write_text(HTML, encoding="utf-8")
    doc = convert.to_document(p)
    text = "\n".join(s.text for s in doc.sections)
    assert "warm bulb" in text and "Unplug" in text
    assert "Cookie settings" not in text and "Privacy" not in text
    assert ("Lamp Guide", "Bulbs") in [s.path for s in doc.sections]


# ---- chunking --------------------------------------------------------------------

def test_chunker_merges_tiny_sections_and_splits_long_ones():
    Section = convert.Section
    # Siblings (same parent), as the assertion below says. The first draft used a parent and
    # its child here, which contradicted test_search_puts_the_answering_section_first: a child
    # merged into its parent loses its own breadcrumb and #anchor. Siblings-only keeps both.
    doc = convert.Document(title="T", url=None, sections=[
        Section(path=("T", "A", "a1"), text="short one."),
        Section(path=("T", "A", "a2"), text="short two."),
        Section(path=("T", "B"), text="\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(12))),
    ])
    chunks = chunk.chunk_document(doc, max_chars=1200, min_chars=200)
    assert all(len(c.text) <= 1200 for c in chunks)
    long_parts = [c for c in chunks if c.breadcrumb.endswith("B")]
    assert len(long_parts) >= 2, "a long section must be split at paragraph boundaries"
    merged = [c for c in chunks if "short one." in c.text]
    assert len(merged) == 1 and "short two." in merged[0].text, "tiny siblings merge into one chunk"


# ---- the shelf -------------------------------------------------------------------

def _make_corpus(root: Path):
    (root / "kettle.md").write_text(MD, encoding="utf-8")
    (root / "lamp.html").write_text(HTML, encoding="utf-8")
    (root / "switches.json").write_text(json.dumps(DOCC), encoding="utf-8")


def test_ingest_is_idempotent_and_replaces_changed_documents(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _make_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    first = sh.ingest("home", corpus)
    again = sh.ingest("home", corpus)
    assert first.docs_added == 3 and again.docs_added == 0 and again.docs_unchanged == 3
    n = sh.stats()["chunks"]
    (corpus / "kettle.md").write_text(MD.replace("every month", "every week"), encoding="utf-8")
    changed = sh.ingest("home", corpus)
    assert changed.docs_replaced == 1
    assert sh.stats()["chunks"] == n, "a replaced document must not leave its old chunks behind"
    hit = sh.search("descaling vinegar", shelf="home").hits[0]
    assert "every week" in hit.text


def test_search_puts_the_answering_section_first(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _make_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("home", corpus)
    res = sh.search("how many watts should the bulb be?")
    assert res.hits and "Bulbs" in res.hits[0].breadcrumb
    res = sh.search("what height is a switch on a phone")
    assert "Sizing" in res.hits[0].breadcrumb
    assert res.hits[0].url and res.hits[0].url.endswith("#Sizing")


def test_questions_with_punctuation_never_break_the_query(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _make_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("home", corpus)
    for q in ['"unbalanced', "AND OR NOT", "near(bulb)", "44x44 pt?", "col:umn*", "' ; drop table chunks; --"]:
        sh.search(q)                                   # must not raise
    assert sh.stats()["chunks"] > 0


def test_zero_hits_say_what_was_searched(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _make_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("home", corpus)
    res = sh.search("quantum chromodynamics")
    assert res.hits == []
    note = res.render()
    assert "0 of" in note and "chunks" in note, f"a zero must name its denominator: {note}"


def test_mirrored_pages_with_the_same_file_name_keep_their_own_urls(tmp_path):
    """Found shelving Samsung's One UI site (2026-09-24): several pages are named intro.html in
    different folders, so a url map keyed by file name gave some passages another page's link."""
    mirror = tmp_path / "docs.example.com"
    for topic in ("layout", "motion"):
        d = mirror / "guide" / topic
        d.mkdir(parents=True)
        (d / "intro.html").write_text(
            f"<main><h1>{topic.title()}</h1><h2>Basics</h2><p>{topic} rules apply.</p></main>", encoding="utf-8")
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("mirror", mirror)
    urls = {h.title: h.url for h in sh.search("rules basics", limit=10).hits}
    assert urls["Layout"].startswith("https://docs.example.com/guide/layout/intro.html"), urls
    assert urls["Motion"].startswith("https://docs.example.com/guide/motion/intro.html"), urls


def test_underscore_html_pages_are_content_but_underscore_json_files_are_metadata(tmp_path):
    """Samsung's landing page was saved as _root.html and silently skipped."""
    corpus = tmp_path / "corpus"; corpus.mkdir(); _make_corpus(corpus)
    (corpus / "_root.html").write_text("<main><h1>Root</h1><p>Landing words zebra.</p></main>", encoding="utf-8")
    (corpus / "_manifest.json").write_text("[]", encoding="utf-8")
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    rep = sh.ingest("home", corpus)
    assert rep.docs_added == 4 and not rep.failed, rep.render()
    assert sh.search("zebra").hits, "the underscore-named HTML page must be shelved"


def test_a_tight_cap_trims_the_next_passage_instead_of_dropping_it(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir()
    for i in range(3):   # distinct texts: identical passages are (correctly) returned once
        (corpus / f"d{i}.md").write_text(f"# D{i}\n\n## Gears\n\n" + f"gear teeth mesh {i}. " * 50, encoding="utf-8")
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("g", corpus)
    res = sh.search("gear teeth", limit=3, max_chars=1300)
    assert len(res.hits) >= 2, "room for a trimmed second passage must be used"
    assert sum(len(h.text) for h in res.hits) <= 1300 + 8 and res.truncated


def test_the_same_passage_is_returned_once(tmp_path):
    """One UI's landing page repeats its overview, so one passage came back twice and spent
    half the answer budget on a copy."""
    corpus = tmp_path / "corpus"; corpus.mkdir()
    body = "# Overview\n\n## Reach\n\nPut primary actions low on the screen for thumbs.\n"
    (corpus / "index.md").write_text(body, encoding="utf-8")
    (corpus / "landing.md").write_text(body, encoding="utf-8")
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("dup", corpus)
    hits = sh.search("primary actions thumbs", limit=5).hits
    assert len(hits) == 1, [h.breadcrumb for h in hits]


# ---- hybrid (keywords + meaning) ---------------------------------------------------------

class _StubEmbedder:
    """Maps texts about touch sizing to one direction and everything else to another, so a
    question that shares NO words with its answer can still land on it. Counts its calls."""
    SIZING = ("tappable", "touch", "finger", "fingers", "hit")

    def __init__(self):
        self.calls = 0

    def __call__(self, texts):
        import numpy as np
        self.calls += 1
        out = []
        for t in texts:
            low = t.lower()
            v = np.array([1.0, 0.1, 0.0]) if any(w in low for w in self.SIZING) else np.array([0.0, 0.1, 1.0])
            out.append(v / np.linalg.norm(v))
        return np.array(out, dtype="float32")


def _sizing_corpus(root: Path):
    (root / "controls.md").write_text(
        "# Controls\n\n## Touch areas\n\nMake each control at least 44 points square so fingers land on it.\n\n"
        "## Colors\n\nUse the system palette for tint.\n", encoding="utf-8")
    (root / "sound.md").write_text("# Sound\n\n## Volume\n\nKeep alerts quiet at night.\n", encoding="utf-8")


def test_hybrid_finds_a_paraphrase_that_shares_no_words(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _sizing_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db", embedder=_StubEmbedder())
    sh.ingest("ui", corpus)
    question = "how big should tappable things be"
    assert sh.search(question, mode="bm25").hits == [], "keywords alone cannot bridge this wording gap"
    hits = sh.search(question, mode="hybrid").hits
    assert hits and "Touch areas" in hits[0].breadcrumb, [h.breadcrumb for h in hits]


def test_hybrid_without_an_embedder_falls_back_to_keywords_and_says_so(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _sizing_corpus(corpus)
    sh = shelf_mod.Shelf(tmp_path / "manuals.db", embedder=False)
    sh.ingest("ui", corpus)
    res = sh.search("system palette tint", mode="hybrid")
    assert res.hits and "Colors" in res.hits[0].breadcrumb
    assert "keyword" in res.render().lower(), "a silent downgrade reads as a hybrid answer"


def test_passages_are_embedded_once(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir(); _sizing_corpus(corpus)
    stub = _StubEmbedder()
    sh = shelf_mod.Shelf(tmp_path / "manuals.db", embedder=stub)
    sh.ingest("ui", corpus)
    after_first = stub.calls
    sh.ingest("ui", corpus)                       # nothing changed: nothing to embed
    assert stub.calls == after_first
    assert sh.stats()["embedded"] == sh.stats()["chunks"]


def test_results_are_capped_by_size(tmp_path):
    corpus = tmp_path / "corpus"; corpus.mkdir()
    for i in range(20):
        (corpus / f"doc{i}.md").write_text(f"# Doc {i}\n\n## Widgets\n\n" + "widget " * 300, encoding="utf-8")
    sh = shelf_mod.Shelf(tmp_path / "manuals.db")
    sh.ingest("bulk", corpus)
    res = sh.search("widget", limit=20, max_chars=3000)
    assert sum(len(h.text) for h in res.hits) <= 3000
    assert res.truncated, "a capped answer must say it was capped"
