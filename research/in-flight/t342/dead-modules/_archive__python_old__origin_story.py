import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get all sessions sorted by age
sessions = sorted(list(r.scan_iter('session:*:actions')))
print('=== ALL SESSIONS ===')
for s in sessions:
    first = r.lrange(s, 0, 0)
    if first:
        try:
            data = json.loads(first[0])
            ts = data.get('timestamp', 'N/A')
            desc = data.get('description', data.get('type', ''))[:50]
            print('  ' + s)
            print('    First: ' + ts + ' - ' + desc)
        except:
            print('  ' + s + ' (parse error)')

# Check oldest approach entries
print()
print('=== APPROACHES ===')
approaches = r.hgetall('approaches:registry')
for k, v in approaches.items():
    try:
        data = json.loads(v)
        created = data.get('created_at', 'N/A')
        comp = data.get('component', 'N/A')
        name = data.get('name', 'N/A')
        status = data.get('status', 'N/A')
        if created:
            created_short = created[:19]
        else:
            created_short = 'N/A'
        print('  ' + comp + '/' + name + ': ' + status + ' (' + created_short + ')')
    except:
        pass

# Check experience by date
print()
print('=== EXPERIENCE ===')
exp = r.hgetall('experience:registry')
for k, v in exp.items():
    try:
        data = json.loads(v)
        ts = data.get('timestamp', 'N/A')
        task = data.get('task', 'N/A')
        success = data.get('success', 'N/A')
        if ts:
            ts_short = ts[:19]
        else:
            ts_short = 'N/A'
        task_short = task[:40]
        print('  ' + task_short + ' success=' + str(success) + ' (' + ts_short + ')')
    except:
        pass

# Work log
print()
print('=== WORK LOG ===')
work_log = r.lrange('context:work_log', 0, -1)
print('  Entries: ' + str(len(work_log)))
for w in work_log[:8]:
    try:
        data = json.loads(w)
        ent = data.get('entry', '')
        ent_short = ent[:80]
        print('    ' + ent_short)
    except:
        w_short = str(w)[:80]
        print('    ' + w_short)

# Check WSL learnings - has 100 fields - likely origin
print()
print('=== WSL ROCM DOC COMPLETE (original origin) ===')
wsl = r.hgetall('learnings:wsl_rocm_docker_complete')
keys = list(wsl.keys())[:15]
for f in keys:
    val = str(wsl[f])[:60]
    print('  ' + f + ': ' + val)