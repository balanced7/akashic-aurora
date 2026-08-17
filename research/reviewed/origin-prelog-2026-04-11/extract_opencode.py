"""Extract the OpenCode archive into bounded packs. READ-ONLY (uri mode=ro).

Two products:
  1. operator-only corpus -- his 758 utterances in order, with session + timestamp. This is the
     small, high-value plane and it stays in MY window because it is the material a fanout
     cannot be re-interrogated about.
  2. per-session packs -- for the blind fan. Bounded and fully supplied, which is the ONE case
     Daniil's own ruling says blind branches are the right instrument for.
"""
import sqlite3, json, datetime, os

DB = r"C:\Users\L5\.local\share\opencode\opencode.db"
OUT = r"C:\Users\L5\AppData\Local\Temp\claude\E--\18762fcf-658e-4576-8558-6008ca0fbf55\scratchpad\archive"
os.makedirs(OUT, exist_ok=True)
AURORA_FIRST = datetime.datetime(2026, 4, 13, 2, 40, 19)

con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)


def ts(v):
    if v is None:
        return None
    if v > 10_000_000_000:
        v = v / 1000
    return datetime.datetime.fromtimestamp(v)


sessions = {}
for sid, title, created in con.execute("select id,title,time_created from session"):
    sessions[sid] = (title, ts(created))

# ---- operator-only corpus, chronological
rows = []
for pdata, mdata, created, sid in con.execute(
        "select p.data, m.data, p.time_created, p.session_id "
        "from part p join message m on m.id = p.message_id"):
    try:
        pobj = json.loads(pdata); mobj = json.loads(mdata)
    except Exception:
        continue
    if mobj.get("role") != "user" or pobj.get("type") != "text":
        continue
    txt = pobj.get("text") or ""
    if not isinstance(txt, str) or not txt.strip():
        continue
    rows.append((created or 0, sid, txt))
rows.sort(key=lambda r: r[0])

pre, post = [], []
for created, sid, txt in rows:
    when = ts(created)
    (pre if when and when < AURORA_FIRST else post).append((when, sid, txt))

with open(os.path.join(OUT, "operator-all.md"), "w", encoding="utf-8") as f:
    f.write("# Every operator utterance in the OpenCode archive (2026-04-11 .. 2026-06-27)\n")
    f.write(f"# {len(rows)} utterances. Verbatim, chronological, zero edits.\n\n")
    last = None
    for when, sid, txt in pre + post:
        if sid != last:
            title, screated = sessions.get(sid, ("?", None))
            f.write(f"\n\n## SESSION {sid}\n## title: {title!r}\n## started: {screated}\n\n")
            last = sid
        f.write(f"[{when}]\n{txt.strip()}\n\n")

with open(os.path.join(OUT, "operator-pre-aurora.md"), "w", encoding="utf-8") as f:
    f.write("# THE PRE-LOG ERA -- operator utterances BEFORE Aurora's first recorded event\n")
    f.write(f"# Aurora's first event: {AURORA_FIRST}. These predate it.\n")
    f.write(f"# {len(pre)} utterances across the 8 sessions the canonized packet never held.\n\n")
    last = None
    for when, sid, txt in pre:
        if sid != last:
            title, screated = sessions.get(sid, ("?", None))
            f.write(f"\n\n## SESSION {sid}\n## title: {title!r}\n## started: {screated}\n\n")
            last = sid
        f.write(f"[{when}]\n{txt.strip()}\n\n")

# ---- full transcript packs, one per session (for the fan)
packs = 0
for sid, (title, screated) in sorted(sessions.items(), key=lambda kv: kv[1][1] or datetime.datetime.min):
    lines = []
    for pdata, mdata, created in con.execute(
            "select p.data, m.data, p.time_created from part p join message m on m.id=p.message_id "
            "where p.session_id=? order by p.time_created", (sid,)):
        try:
            pobj = json.loads(pdata); mobj = json.loads(mdata)
        except Exception:
            continue
        ptype = pobj.get("type"); role = mobj.get("role")
        if ptype not in ("text", "reasoning"):
            continue
        txt = pobj.get("text") or ""
        if not isinstance(txt, str) or not txt.strip():
            continue
        lines.append(f"[{ts(created)}] {role}/{ptype}:\n{txt.strip()}\n")
    if not lines:
        continue
    safe = sid.replace("/", "_")[:40]
    with open(os.path.join(OUT, f"session_{(screated or datetime.datetime.min):%Y%m%d_%H%M}_{safe}.md"),
              "w", encoding="utf-8") as f:
        f.write(f"# {title}\n# session {sid}\n# started {screated}\n\n")
        f.write("\n".join(lines))
    packs += 1

con.close()
print(f"operator utterances : {len(rows)}  (pre-Aurora: {len(pre)}, after: {len(post)})")
print(f"session packs written: {packs}")
print(f"pre-aurora chars    : {sum(len(t) for _,_,t in pre):,}")
print(f"operator-all chars  : {sum(len(t) for _,_,t in rows):,}")
print(f"OUT: {OUT}")
