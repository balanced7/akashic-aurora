"""shelf -- labelled chunks in SQLite with an FTS5 index; incremental ingest; honest search.

One database file holds every shelf (a shelf is a named collection: "apple-hig", "one-ui").
SQLite in WAL mode is the house's durable engine (SqliteStore, the Eye), and it lets any
number of seats read while one ingests, which a shared DuckDB file would not.

Search is BM25 over three columns. The document title and the heading path are weighted
above the body, because a heading names what a passage is about. A question is reduced to its
content words, each quoted, and OR-ed together. Quoting makes FTS5 syntax inert, so no
question can break the query, and OR lets passages that match more of the words rank first.
Answers are capped by characters (the idea borrowed from DuckDB's query skill, which checks
size before it returns rows). A zero names what was searched, because an empty answer with no
denominator reads as "the manuals do not cover this" when it may only mean "wrong words".

HYBRID (mode="hybrid"). Keywords cannot cross a wording gap. The first real search missed
Apple's answer to "minimum size of a tappable button" because the guidelines say "hit
target". Hybrid mode also ranks passages by meaning, using the embedding model the house
already caches (all-MiniLM-L6-v2, core/primitives/embedder.py), and fuses the two rankings with
reciprocal rank fusion. A passage found by meaning alone must clear a similarity floor, so
hybrid still returns an honest zero when nothing is close. Passages are embedded once, at
ingest, and stored beside the text. With no model available, hybrid answers with keywords and
says so in the result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.manuals import chunk as chunk_mod
from core.manuals import convert

SCHEMA_VERSION = "manuals.shelf/1"
# Folded into every document's fingerprint: bump it when conversion or chunking changes, and
# the next ingest re-cuts every document instead of trusting passages cut by older code.
PIPELINE_VERSION = "2026-09-24.2"
BM25_WEIGHTS = (4.0, 2.0, 1.0)                # title, breadcrumb, text
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60                                    # reciprocal rank fusion constant (the usual 60)
CANDIDATES = 50                               # per ranking, before fusion
VECTOR_FLOOR = 0.25                           # cosine a meaning-only match must reach


DEFAULT_TAG = "all-MiniLM-L6-v2"
_DEFAULT_EMBEDDER: Dict[str, object] = {}


def load_default_embedder():
    """The house's cached MiniLM, loaded from local files only (a search never downloads), once
    per process: a long-lived door such as the MCP server must not reload it on every call.
    Returns a callable texts -> float32 unit vectors, or None when the model is unavailable."""
    if "fn" not in _DEFAULT_EMBEDDER:
        _DEFAULT_EMBEDDER["fn"] = _load_minilm()
    return _DEFAULT_EMBEDDER["fn"]


def _load_minilm():
    try:
        from sentence_transformers import SentenceTransformer
        try:
            model = SentenceTransformer(EMBED_MODEL, device="cpu", local_files_only=True)
        except TypeError:                     # older sentence-transformers: no local_files_only
            model = SentenceTransformer(EMBED_MODEL, device="cpu")
    except Exception:
        return None

    def embed(texts):
        return model.encode(list(texts), batch_size=64, normalize_embeddings=True,
                            convert_to_numpy=True, show_progress_bar=False).astype("float32")

    embed.model_name = DEFAULT_TAG
    return embed

_STOP = set("""a an and are as at be but by can could do does did for from had has have how i if in
into is it its me my not of on or our should so than that the their them then there these they this
those to us was we were what when where which while who whom why will with would you your
many much any some about use using used need""".split())


def default_db_path() -> Path:
    from core.paths import data_root
    return data_root() / "state" / "manuals" / "manuals.db"


@dataclass
class IngestReport:
    shelf: str
    docs_added: int = 0
    docs_replaced: int = 0
    docs_unchanged: int = 0
    docs_removed: int = 0
    chunks_written: int = 0
    embedded: int = 0
    vector_note: str = ""
    failed: List[str] = field(default_factory=list)

    def render(self) -> str:
        line = (f"manual ingest [{self.shelf}]: {self.docs_added} added, {self.docs_replaced} replaced, "
                f"{self.docs_unchanged} unchanged, {self.docs_removed} removed; "
                f"{self.chunks_written} chunks written, {self.embedded} embedded")
        if self.vector_note:
            line += f" ({self.vector_note})"
        if self.failed:
            line += f"\n  {len(self.failed)} FAILED:\n    " + "\n    ".join(self.failed[:20])
            if len(self.failed) > 20:
                line += f"\n    ... +{len(self.failed) - 20} more"
        return line


@dataclass
class Hit:
    shelf: str
    title: str
    breadcrumb: str
    url: Optional[str]
    page: Optional[int]
    score: float
    text: str


@dataclass
class SearchResult:
    query: str
    terms: List[str]
    hits: List[Hit]
    searched_chunks: int
    shelves: List[str]
    truncated: bool = False
    error: Optional[str] = None
    mode: str = "bm25"
    note: Optional[str] = None

    def render(self) -> str:
        text = self._render()
        return f"{text}\n({self.note})" if self.note else text

    def _render(self) -> str:
        where = ", ".join(self.shelves) or "no shelves"
        if self.error:
            return f"manual search: could not search ({self.error}); 0 of {self.searched_chunks} chunks in [{where}]"
        if not self.hits:
            return (f"manual search: 0 of {self.searched_chunks} chunks in [{where}] matched "
                    f"{self.terms or '(no searchable words)'} -- the shelf may use other words for this; "
                    f"try synonyms, or `manual list` to see what is shelved")
        out = [f"manual search: {len(self.hits)} passage(s) for {self.query!r} "
               f"(from {self.searched_chunks} chunks in [{where}])"]
        for i, h in enumerate(self.hits, 1):
            where_line = h.url or ""
            if h.page:
                where_line = f"{where_line} p.{h.page}".strip()
            out.append(f"\n[{i}] {h.breadcrumb}  ({h.shelf})\n    {where_line}")
            out.append("    " + h.text.replace("\n", "\n    "))
        if self.truncated:
            out.append("\n(answer capped by size; raise --max-chars or --limit for more)")
        return "\n".join(out)

    def to_json(self) -> str:
        return json.dumps({"query": self.query, "terms": self.terms, "searched_chunks": self.searched_chunks,
                           "shelves": self.shelves, "truncated": self.truncated, "error": self.error,
                           "mode": self.mode, "note": self.note,
                           "hits": [h.__dict__ for h in self.hits]}, ensure_ascii=False)


def terms_of(query: str) -> List[str]:
    words = [w.lower() for w in re.findall(r"\w+", query or "")]
    content = [w for w in words if w not in _STOP and (len(w) > 1 or w.isdigit())]
    chosen = content or [w for w in words if len(w) > 1]
    seen, out = set(), []
    for w in chosen:
        if w not in seen:
            seen.add(w); out.append(w)
    return out[:24]


class Shelf:
    """embedder: None or False -> keyword search only; "default" -> the house's cached MiniLM,
    loaded on first use; a callable texts -> unit vectors -> that (tests pass a stub)."""

    def __init__(self, db_path=None, embedder=None):
        self.path = Path(db_path) if db_path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder_opt = embedder
        self._embedder_fn = None
        self._embedder_tried = False
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
                CREATE TABLE IF NOT EXISTS docs(
                    doc_id INTEGER PRIMARY KEY, shelf TEXT NOT NULL, source TEXT NOT NULL UNIQUE,
                    title TEXT, url TEXT, sha256 TEXT, n_chunks INTEGER, ingested_at TEXT);
                CREATE TABLE IF NOT EXISTS chunks(
                    chunk_id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, shelf TEXT NOT NULL,
                    seq INTEGER, title TEXT, breadcrumb TEXT, url TEXT, page INTEGER, text TEXT);
                CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
                CREATE INDEX IF NOT EXISTS chunks_shelf ON chunks(shelf);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    title, breadcrumb, text, tokenize='porter unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS chunk_vecs(
                    chunk_id INTEGER PRIMARY KEY, model TEXT NOT NULL, vec BLOB NOT NULL);
            """)
            c.execute("INSERT OR IGNORE INTO meta(k, v) VALUES ('schema', ?)", (SCHEMA_VERSION,))

    def _embedder(self):
        """The embedding callable, or None. Loaded once, only when first needed."""
        if self._embedder_opt is None or self._embedder_opt is False:
            return None
        if callable(self._embedder_opt):
            return self._embedder_opt
        if not self._embedder_tried:
            self._embedder_tried = True
            self._embedder_fn = load_default_embedder()
        return self._embedder_fn

    def _model_tag(self, fn) -> str:
        return getattr(fn, "model_name", None) or type(fn).__name__

    def _embed_missing(self, c: sqlite3.Connection, fn, batch: int = 256) -> int:
        """Embed every passage that has no vector from this model yet. Returns how many."""
        import numpy as np
        tag = self._model_tag(fn)
        todo = c.execute("SELECT c.chunk_id, c.breadcrumb, c.text FROM chunks c "
                         "LEFT JOIN chunk_vecs v ON v.chunk_id = c.chunk_id AND v.model = ? "
                         "WHERE v.chunk_id IS NULL", (tag,)).fetchall()
        for i in range(0, len(todo), batch):
            part = todo[i:i + batch]
            vecs = np.asarray(fn([f"{crumb}\n{text}" for _, crumb, text in part]), dtype="float32")
            c.executemany("INSERT OR REPLACE INTO chunk_vecs(chunk_id, model, vec) VALUES (?,?,?)",
                          [(cid, tag, v.tobytes()) for (cid, _, _), v in zip(part, vecs)])
            c.commit()
        return len(todo)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.path), timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    # ---- ingest --------------------------------------------------------------------

    @staticmethod
    def _load_manifest(root: Path) -> Dict[str, str]:
        """file name -> source url, from a fetcher's _manifest.json when one is present.

        Only names that occur ONCE are kept: One UI has several intro.html pages in different
        folders, and a name shared by two pages cannot say which url is whose. Those pages get
        their url from the mirror layout instead (see _mirror_url)."""
        mf = root / "_manifest.json"
        if not mf.exists():
            return {}
        try:
            entries = json.loads(mf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(entries, dict):
            entries = entries.get("pages") or entries.get("files") or list(entries.values())
        pairs = []
        for e in entries if isinstance(entries, list) else []:
            if not isinstance(e, dict) or not e.get("url"):
                continue
            name = next((Path(str(e[k])).name for k in ("file", "filename", "local_path", "saved_as", "local_file")
                         if e.get(k)), None)
            if name is None and e.get("path"):
                raw_path = str(e["path"]).strip("/")
                name = (Path(raw_path).name if Path(raw_path).suffix.lower() in convert.SUPPORTED
                        else raw_path.replace("/", "__") + ".json")
            if name:
                pairs.append((name, e["url"]))
        counts: Dict[str, int] = {}
        for name, _ in pairs:
            counts[name] = counts.get(name, 0) + 1
        return {name: url for name, url in pairs if counts[name] == 1}

    @staticmethod
    def _mirror_url(root: Path, p: Path) -> Optional[str]:
        """A page saved under a host-named folder (docs.example.com/guide/x.html) gets that url."""
        parts = [root.name] + list(p.relative_to(root).parts)
        for i, part in enumerate(parts[:-1]):
            if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", part.lower()):
                return "https://" + "/".join(parts[i:])
        return None

    def ingest(self, shelf: str, root, html_selector: Optional[str] = None,
               max_chars: int = 1800, prune: bool = True) -> IngestReport:
        root = Path(root)
        rep = IngestReport(shelf=shelf)
        cfg_path = root / "_shelf.json"
        if html_selector is None and cfg_path.exists():
            try:
                html_selector = json.loads(cfg_path.read_text(encoding="utf-8")).get("html_selector")
            except (OSError, json.JSONDecodeError):
                pass
        urls = self._load_manifest(root)
        # "_manifest.json", "_index.json" and friends are a fetcher's metadata; an HTML page
        # that happens to start with "_" (One UI's _root.html) is content.
        files = sorted(p for p in root.rglob("*") if p.is_file()
                       and p.suffix.lower() in convert.SUPPORTED
                       and not (p.name.startswith("_") and p.suffix.lower() == ".json"))
        seen_sources = set()
        with self._conn() as c:
            for p in files:
                source = str(p.resolve())
                seen_sources.add(source)
                sha = hashlib.sha256(p.read_bytes() + f"|{PIPELINE_VERSION}|{max_chars}|{html_selector}".encode()).hexdigest()
                row = c.execute("SELECT doc_id, sha256 FROM docs WHERE source = ?", (source,)).fetchone()
                if row and row[1] == sha:
                    rep.docs_unchanged += 1
                    continue
                try:
                    doc = convert.to_document(p, url=self._mirror_url(root, p) or urls.get(p.name),
                                              html_selector=html_selector)
                    chunks = chunk_mod.chunk_document(doc, max_chars=max_chars, source_uri=p.resolve().as_uri())
                except Exception as e:                     # one bad file never sinks the shelf
                    rep.failed.append(f"{p.name}: {type(e).__name__}: {e}"[:300])
                    continue
                if row:
                    self._drop_doc(c, row[0])
                    rep.docs_replaced += 1
                else:
                    rep.docs_added += 1
                cur = c.execute(
                    "INSERT INTO docs(shelf, source, title, url, sha256, n_chunks, ingested_at) VALUES (?,?,?,?,?,?,?)",
                    (shelf, source, doc.title, doc.url, sha, len(chunks), time.strftime("%Y-%m-%dT%H:%M:%S")))
                doc_id = cur.lastrowid
                for ch in chunks:
                    cur = c.execute(
                        "INSERT INTO chunks(doc_id, shelf, seq, title, breadcrumb, url, page, text) VALUES (?,?,?,?,?,?,?,?)",
                        (doc_id, shelf, ch.seq, ch.title, ch.breadcrumb, ch.url, ch.page, ch.text))
                    c.execute("INSERT INTO chunks_fts(rowid, title, breadcrumb, text) VALUES (?,?,?,?)",
                              (cur.lastrowid, ch.title, ch.breadcrumb, ch.text))
                rep.chunks_written += len(chunks)
                c.commit()
            if prune:
                prefix = str(root.resolve())
                for doc_id, source in c.execute(
                        "SELECT doc_id, source FROM docs WHERE shelf = ?", (shelf,)).fetchall():
                    if source.startswith(prefix) and source not in seen_sources:
                        self._drop_doc(c, doc_id)
                        rep.docs_removed += 1
                c.commit()
            if not self._embedder_opt:
                rep.vector_note = "keyword search only"
                return rep
            # Count what is missing before loading anything: a re-ingest that changed nothing
            # must not pay the model's load time.
            tag = DEFAULT_TAG if self._embedder_opt == "default" else self._model_tag(self._embedder_opt)
            missing = c.execute("SELECT count(*) FROM chunks c LEFT JOIN chunk_vecs v "
                                "ON v.chunk_id = c.chunk_id AND v.model = ? WHERE v.chunk_id IS NULL",
                                (tag,)).fetchone()[0]
            if not missing:
                return rep
            fn = self._embedder()
            if fn is None:
                rep.vector_note = "keyword search only: no embedding model on this machine"
            else:
                try:
                    rep.embedded = self._embed_missing(c, fn)
                except Exception as e:                  # vectors are an upgrade, never a blocker
                    rep.vector_note = f"embedding failed, keyword search still works: {type(e).__name__}: {e}"[:200]
        return rep

    @staticmethod
    def _drop_doc(c: sqlite3.Connection, doc_id: int) -> None:
        ids = [r[0] for r in c.execute("SELECT chunk_id FROM chunks WHERE doc_id = ?", (doc_id,))]
        c.executemany("DELETE FROM chunks_fts WHERE rowid = ?", [(i,) for i in ids])
        c.executemany("DELETE FROM chunk_vecs WHERE chunk_id = ?", [(i,) for i in ids])
        c.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        c.execute("DELETE FROM docs WHERE doc_id = ?", (doc_id,))

    # ---- search --------------------------------------------------------------------

    def _bm25(self, c: sqlite3.Connection, terms: List[str], shelf: Optional[str], n: int):
        """[(chunk_id, bm25)] best first; raises sqlite3.Error for the caller to report."""
        if not terms:
            return []
        match = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
        sql = (f"SELECT c.chunk_id, bm25(chunks_fts, {BM25_WEIGHTS[0]}, {BM25_WEIGHTS[1]}, {BM25_WEIGHTS[2]}) AS s "
               f"FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.rowid "
               f"WHERE chunks_fts MATCH ?" + (" AND c.shelf = ?" if shelf else "") + " ORDER BY s LIMIT ?")
        return c.execute(sql, [match] + ([shelf] if shelf else []) + [n]).fetchall()

    def _by_meaning(self, c: sqlite3.Connection, fn, query: str, shelf: Optional[str], n: int):
        """[(chunk_id, cosine)] best first, above VECTOR_FLOOR only; [] when nothing is embedded."""
        import numpy as np
        tag = self._model_tag(fn)
        rows = c.execute("SELECT v.chunk_id, v.vec FROM chunk_vecs v JOIN chunks c ON c.chunk_id = v.chunk_id "
                         "WHERE v.model = ?" + (" AND c.shelf = ?" if shelf else ""),
                         [tag] + ([shelf] if shelf else [])).fetchall()
        if not rows:
            return []
        ids = np.array([r[0] for r in rows])
        mat = np.frombuffer(b"".join(r[1] for r in rows), dtype="float32").reshape(len(rows), -1)
        q = np.asarray(fn([query]), dtype="float32")[0]
        sims = mat @ q
        order = np.argsort(-sims)[:n]
        return [(int(ids[i]), float(sims[i])) for i in order if sims[i] >= VECTOR_FLOOR]

    def search(self, query: str, shelf: Optional[str] = None, limit: int = 8,
               max_chars: int = 6000, mode: str = "bm25") -> SearchResult:
        terms = terms_of(query)
        # Over-fetch so duplicates can be dropped without shortening the answer: sites repeat
        # passages (One UI's landing page repeats its overview word for word).
        want = max(1, int(limit)) * 3
        with self._conn() as c:
            if shelf:
                shelves = [shelf]
                searched = c.execute("SELECT count(*) FROM chunks WHERE shelf = ?", (shelf,)).fetchone()[0]
            else:
                shelves = [r[0] for r in c.execute("SELECT DISTINCT shelf FROM chunks ORDER BY shelf")]
                searched = c.execute("SELECT count(*) FROM chunks").fetchone()[0]
            res = SearchResult(query=query, terms=terms, hits=[], searched_chunks=searched,
                               shelves=shelves, mode="bm25")
            if not searched:
                return res
            fn = self._embedder() if mode == "hybrid" else None
            if mode == "hybrid" and fn is None:
                res.note = "hybrid unavailable (no embedding model on this machine): keyword search only"
            try:
                keyword = self._bm25(c, terms, shelf, max(want, CANDIDATES) if fn else want)
            except sqlite3.Error as e:
                res.error = f"{type(e).__name__}: {e}"
                return res
            if fn is not None:
                res.mode = "hybrid"
                meaning = self._by_meaning(c, fn, query, shelf, CANDIDATES)
                if not meaning:
                    res.note = "no passages are embedded yet (run manual ingest): keyword ranking only"
                fused: Dict[int, float] = {}
                for ranking in (keyword, meaning):
                    for rank, (cid, _) in enumerate(ranking, 1):
                        fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank)
                ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:want]
            else:
                ranked = keyword
            if not ranked:
                return res
            ids = [cid for cid, _ in ranked]
            info = {r[0]: r[1:] for r in c.execute(
                f"SELECT chunk_id, shelf, title, breadcrumb, url, page, text FROM chunks "
                f"WHERE chunk_id IN ({','.join('?' * len(ids))})", ids)}
            rows = [info[cid] + (score,) for cid, score in ranked if cid in info]
        # Fill the budget in rank order. A passage that does not fit whole is trimmed to the
        # room left, as long as that room can hold a useful few lines (200 chars); below that
        # the answer stops and says it was capped.
        budget = max(200, int(max_chars))
        used = 0
        seen = set()
        for s, title, crumb, url, page, text, score in rows:
            fingerprint = " ".join(text.split()).lower()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            if len(res.hits) >= max(1, int(limit)):
                res.truncated = True
                break
            room = budget - used
            if res.hits and room < 200:
                res.truncated = True
                break
            if len(text) > room:
                text = text[:max(0, room - 4)].rstrip() + " ..."
                res.truncated = True
            res.hits.append(Hit(shelf=s, title=title, breadcrumb=crumb, url=url, page=page,
                                score=round(float(score), 3), text=text))
            used += len(text)
        return res

    def stats(self) -> Dict[str, object]:
        with self._conn() as c:
            per = {s: {"docs": d, "chunks": n} for s, d, n in c.execute(
                "SELECT d.shelf, count(DISTINCT d.doc_id), count(c.chunk_id) FROM docs d "
                "LEFT JOIN chunks c ON c.doc_id = d.doc_id GROUP BY d.shelf ORDER BY d.shelf")}
            return {"docs": c.execute("SELECT count(*) FROM docs").fetchone()[0],
                    "chunks": c.execute("SELECT count(*) FROM chunks").fetchone()[0],
                    "embedded": c.execute("SELECT count(*) FROM chunk_vecs").fetchone()[0],
                    "shelves": per, "db": str(self.path)}
