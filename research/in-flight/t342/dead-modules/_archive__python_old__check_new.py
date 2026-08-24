import redis, json
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print('=== CHECKING FOR NEW ENTRIES ===')
print()

# Get all new format logs sorted
new_logs = sorted([k for k in r.scan_iter('session:session_*')])
print('New format logs found: ' + str(len(new_logs)))
print()

# Get the absolute newest
latest = new_logs[-1]
print('=== NEWEST LOG: ' + latest + ' ===')
items = r.lrange(latest, 0, -1)
for item in items:
    data = json.loads(item)
    ts = data.get('timestamp', 'N/A')
    itype = data.get('type', 'unknown')
    content = data.get('content', '')
    tags = data.get('tags', [])
    seq = data.get('sequence', 'N/A')
    print('Seq ' + str(seq) + ' [' + itype + '] ' + ts[-12:])
    print('  ' + content)
    if tags:
        print('  Tags: ' + str(tags))
    print()

# Check ALL new logs for newest timestamp across all
print('=== NEWEST ENTRY ACROSS ALL ===')
all_items = []
for log_key in new_logs:
    items = r.lrange(log_key, 0, -1)
    for item in items:
        data = json.loads(item)
        all_items.append((data.get('timestamp', ''), data))
        
all_items.sort(key=lambda x: x[0], reverse=True)
if all_items:
    newest_ts, newest_data = all_items[0]
    print('Timestamp: ' + newest_ts)
    print(json.dumps(newest_data[1], indent=2))

# Try searching by common tags
print()
print('=== SEARCH BY TAG: "implementation" ===')
for log_key in new_logs:
    items = r.lrange(log_key, 0, -1)
    for item in items:
        data = json.loads(item)
        if 'implementation' in data.get('tags', []):
            print('  ' + data.get('content', ''))

print()
print('=== SEARCH BY TAG: "vision" ===')
for log_key in new_logs:
    items = r.lrange(log_key, 0, -1)
    for item in items:
        data = json.loads(item)
        if 'vision' in data.get('tags', []):
            print('  ' + data.get('content', ''))

# Check old format too
print()
print('=== OLD FORMAT NEWEST ===')
old_logs = sorted([k for k in r.scan_iter('session:opencode_20260415_*:actions')])
if old_logs:
    latest_old = old_logs[-1]
    items = r.lrange(latest_old, -5, -1)
    for item in items:
        data = json.loads(item)
        ts = data.get('timestamp', 'N/A')
        desc = data.get('description', data.get('action', ''))
        print('  ' + ts[-12:] + ' - ' + desc[:60])

# Evaluate readability
print()
print('=== READABILITY EVALUATION ===')
print()
print('Strengths of current format:')
print('  1. JSON structure - easy to parse programmatically')
print('  2. Tags present - can filter by category')
print('  3. Sequence numbers - ordered correctly')
print('  4. Type field - action vs decision clear')
print('  5. Timestamp - chronological order')
print()
print('Areas for improvement:')
print('  1. No "session" field in all entries - ambiguous which agent')
print('  2. Content is short - could use more detail')
print('  3. No "why" rationale in most action entries')
print('  4. No data field with specifics')