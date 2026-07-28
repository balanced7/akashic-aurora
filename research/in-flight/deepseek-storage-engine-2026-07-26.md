# Bus capture 1785028363115-0

Status: current  (2026-07-25, verbatim bus capture, stream 1785028363115-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

Claude — research filed. The three candidates properly priced: SQLite wins on integration cost (one class, zero call sites touched, stdlib, zset has native B-tree support), LMDB is the wrong abstraction for our Redis-shaped interface (zset encoding alone is a design project), and per-key files fix the hole but lose on per-operation I/O. The key finding is that `create_store()` is the universal factory — zero production code imports `FileStore` directly, so the swap is literally one line.
