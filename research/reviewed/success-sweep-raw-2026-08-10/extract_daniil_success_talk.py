# Extract Daniil-voice utterances resembling "define success / measure progress" from ALL
# session transcripts. Pre-chew stage for a deepseek fan: cast a WIDE regex net here; the
# fan branches judge relevance. Reads BOTH user turns AND queue-operation records per
# lesson operator_speech_hides_in_queue_operation_records.
import json, re, glob, os, sys, hashlib

ROOT = os.path.expanduser("~/.claude/projects")
OUT_MD = sys.argv[1] if len(sys.argv) > 1 else "candidates.md"
OUT_JSONL = OUT_MD.replace(".md", ".jsonl")

# Word groupings: broad on purpose. Each named so the pack shows WHICH net caught it.
GROUPS = {
    "success":      r"\bsuccess",
    "measure":      r"\bmeasur",
    "progress":     r"\bprogress",
    "goal":         r"\bgoal|\bnorth star|\bdestination",
    "win":          r"\bwinning|\bwin condition|\bwhat a win",
    "worth":        r"\bworth (it|building|doing)",
    "working":      r"\b(is it|if it'?s?|it'?s not|know.{0,12}) work",
    "know-tell":    r"\bhow (do|would|will) (we|i|you) (know|tell)|\bknow (if|whether|when)",
    "metric":       r"\bmetric|\bkpi|\bbenchmark|\bbaseline|\bgauge",
    "bar":          r"\b(the|success|high|quality|homecoming) bar\b|\bbar (is|for|of)\b",
    "prove":        r"\bprove|\bproof|\breceipt",
    "target":       r"\btarget|\baim(ing)?\b|\bobjective",
    "better":       r"\bbetter at\b|\bimprov(e|ing) (at|on|the)|\bdoing well\b|\bhow are we doing",
    "visibility":   r"\bvisibilit|\bdashboard|\bsee (what|how|if)|\btell if",
    # lens-3 harvest: his informal, non-native phrasings the seed nets missed
    "informal":     r"did it work|is (it|this) (helping|working)|are we on track|right direction"
                    r"|getting better|any progress|how (far|close) (are|is)|good enough"
                    r"|better than|worse than|before and after|did we improve|what (worked|failed)"
                    r"|run it and see|see the difference|make sure it|any better",
}
COMPILED = {k: re.compile(v, re.I) for k, v in GROUPS.items()}

# Noise filters: agent/meta/system material that rides user-typed turns.
SKIP_MARKERS = ("<command-name>", "<local-command", "Caveat: The messages below",
                "tool_use_error", "<system-reminder>", "[Request interrupted",
                "<task-notification", "<task-id")  # agent/system blocks, not his voice (lens-3 catch)

def texts_from_content(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "text":
                yield blk.get("text", "")

def clean(t):
    t = t.strip()
    return t if 12 <= len(t) <= 2400 else (t[:2400] if len(t) > 2400 else "")

seen, rows = set(), []
files = glob.glob(os.path.join(ROOT, "*", "*.jsonl"))
for fp in files:
    sid = os.path.basename(fp)[:-6]
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                typ = obj.get("type", "")
                cands = []
                if typ == "user" and not obj.get("isMeta"):
                    msg = obj.get("message") or {}
                    if msg.get("role") == "user":
                        cands += list(texts_from_content(msg.get("content")))
                elif typ == "queue-operation":          # operator speech hides here
                    for key in ("prompt", "text", "content"):
                        v = obj.get(key)
                        if isinstance(v, str):
                            cands.append(v)
                ts = (obj.get("timestamp") or "")[:10]
                for raw in cands:
                    if any(m in raw for m in SKIP_MARKERS):
                        continue
                    t = clean(raw)
                    if not t:
                        continue
                    hits = [g for g, rx in COMPILED.items() if rx.search(t)]
                    if not hits:
                        continue
                    key = hashlib.sha1(t[:300].lower().encode()).hexdigest()[:12]
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({"date": ts or "????-??-??", "session": sid[:13],
                                 "groups": hits, "text": t})
    except OSError:
        continue

rows.sort(key=lambda r: r["date"])
with open(OUT_JSONL, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Compact MD pack for the fan. Hard cap so the shared pack never blows the ask budget.
CAP = 90_000
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("# CANDIDATES: Daniil utterances matching success/measurement groupings\n")
    f.write(f"# {len(rows)} unique utterances, {len(files)} transcript files swept\n")
    f.write("# fields: [date | session | nets that caught it]\n\n")
    used = 0
    for r in rows:
        blk = f"[{r['date']} | {r['session']} | {','.join(r['groups'])}]\n{r['text']}\n\n"
        if used + len(blk) > CAP:
            f.write(f"\n# CLIPPED at {CAP} chars -- {len(rows)} total in {OUT_JSONL}\n")
            break
        f.write(blk); used += len(blk)

print(f"files={len(files)} candidates={len(rows)} md_chars={used}")
print("top dates:", [r['date'] for r in rows[:3]], "...", [r['date'] for r in rows[-3:]])
