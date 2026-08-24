import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get newest (active) logs
new_logs = sorted([k for k in r.scan_iter('session:session_*')])
if new_logs:
    latest_log_key = new_logs[-1]
    items = r.lrange(latest_log_key, 0, -1)
    print('=== LATEST ACTIVE SESSION LOG ===')
    print('Log key: ' + latest_log_key)
    print('Entries: ' + str(len(items)))
    print()
    for item in items:
        data = json.loads(item)
        ts = data.get('timestamp', 'N/A')
        itype = data.get('type', 'unknown')
        content = data.get('content', '')
        tags = data.get('tags', [])
        sequence = data.get('sequence', 'N/A')
        print('[' + itype + '] Seq ' + str(sequence) + ' | ' + ts[-12:])
        print('  ' + content)
        if tags:
            print('  Tags: ' + str(tags))
        print()

# Check active sessions
print('=== ACTIVE SESSIONS ===')
active = r.hgetall('sessions:active')
for session_id, info in active.items():
    try:
        data = json.loads(info)
        if data.get('status') == 'active':
            task = data.get('task', 'N/A')
            print('  ' + session_id + ': ' + task[:60])
    except:
        pass

# Check old format for most recent actions with intent
print()
print('=== NEWEST ACTIONS (OLD FORMAT) ===')
old_logs = sorted([k for k in r.scan_iter('session:opencode_20260415_*:actions')])
if old_logs:
    latest = old_logs[-1]
    items = r.lrange(latest, -3, -1)
    for item in items:
        try:
            data = json.loads(item)
            ts = data.get('timestamp', 'N/A')
            desc = data.get('description', data.get('action', ''))
            data_str = data.get('data', {})
            print('  ' + ts[-12:] + ' - ' + desc[:60])
            if data_str:
                print('    Data: ' + str(data_str)[:60])
        except:
            pass

# Check for any decisions or plan statements
print()
print('=== DECLARED INTENTIONS (from decisions) ===')
decisions = r.hgetall('decisions:registry')
for d_id, d_json in decisions.items():
    try:
        d = json.loads(d_json)
        title = d.get('title', 'N/A')
        status = d.get('status', 'N/A')
        print('  ' + d_id + ': ' + title)
    except:
        pass