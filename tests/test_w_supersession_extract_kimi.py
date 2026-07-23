"""Second census pass: extract title + first content lines per CURRENT-stamped file
so the megaread classifies from evidence, not filenames. Output is the megaread corpus."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_RE = re.compile(r"^Status:\s*(\w+)", re.M)
SWEEP_DIRS = ["docs", os.path.join("research", "reviewed"), os.path.join("research", "drafts")]
SKIP_DIRS = {os.path.join("research", "briefs"), "chronicles"}
GENERATED = {"SHELVES.md", "LIBRARY.md", "INDEX.md"}


def _iter_md():
    for base in SWEEP_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            for fn in sorted(filenames):
                if not fn.endswith(".md"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                if any(rel.startswith(s.replace(os.sep, "/")) for s in SKIP_DIRS):
                    continue
                if fn in GENERATED:
                    continue
                yield rel, full


def test_extract_headers():
    out = []
    for rel, full in _iter_md():
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        m = STATUS_RE.search(text[:3000])
        if not m or m.group(1).lower() != "current":
            continue
        # title = first markdown H1, else first non-empty line
        title = ""
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("# "):
                title = s[2:].strip()
                break
            if s and not s.startswith(("Status:", "Type:", "Class:", "---")) and not title:
                title = s[:120]
        # task references + date references as evidence hooks
        tasks = sorted(set(re.findall(r"\bT\d{3}\b", text)))[:8]
        dates = sorted(set(re.findall(r"2026-07-\d{2}", text)))[:4]
        out.append(f"{rel} | {title[:100]} | tasks={','.join(tasks)} | dates={','.join(dates)}")
    corpus = os.path.join(ROOT, "scratch", "supersession_megaread_corpus.txt")
    with open(corpus, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"\n[extract] {len(out)} current-stamped files -> scratch/supersession_megaread_corpus.txt")
    print("[extract] first 12 rows:")
    for ln in out[:12]:
        print("   ", ln[:160])
