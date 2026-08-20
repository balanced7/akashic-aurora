import json, re, collections

d = json.load(open('state/coord/tasks.json', encoding='utf-8'))
tasks = d.get('tasks', d) if isinstance(d, dict) else d
if isinstance(tasks, dict):
    tasks = list(tasks.values())

print("TOTAL ROWS:", len(tasks))
print()
print("KEYS of first row:", list(tasks[0].keys()))
print()
# count populated deps
deps_pop = sum(1 for t in tasks if t.get('deps'))
print("rows with populated deps:", deps_pop)
# count rows whose title cites another T-number
pat = re.compile(r'\bT\d{3}\b')
citing = [(t.get('id',''), t.get('title','')) for t in tasks if pat.search(t.get('title','') or '')]
print("rows citing a Tnnn in title:", len(citing))
print()
# every edge: (source_id, cited_id, title) with the citation context
edges = []
for t in tasks:
    title = t.get('title','') or ''
    for m in pat.finditer(title):
        edges.append((t.get('id',''), m.group(0), title))
print("RAW T-citation occurrences in titles:", len(edges))
print()
# deps field content
print("SAMPLE deps values:")
for t in tasks:
    if t.get('deps'):
        print("  ", t.get('id'), "deps=", t.get('deps'))
