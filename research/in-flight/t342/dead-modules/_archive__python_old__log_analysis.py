import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print('=== NEW FORMAT LOGS ===')
new_logs = sorted([k for k in r.scan_iter('session:session_*')])

for log_key in new_logs:
    items = r.lrange(log_key, 0, -1)
    print('Log: ' + log_key)
    for item in items:
        data = json.loads(item)
        itype = data.get('type', 'unknown')
        content = data.get('content', '')[:60]
        tags = data.get('tags', [])
        ts = data.get('timestamp', '')
        print(f'  [{itype}] {ts[-12:]} - {content}')
        if tags:
            print(f'    Tags: {tags}')
    print()

print('=== TAG SEARCH ===')
all_items = []
for log_key in new_logs:
    items = r.lrange(log_key, 0, -1)
    for item in items:
        data = json.loads(item)
        all_items.append(data)

tags_found = {}
for item in all_items:
    for tag in item.get('tags', []):
        if tag not in tags_found:
            tags_found[tag] = []
        content = item.get('content', '')[:40]
        tags_found[tag].append(content)

for tag, items in tags_found.items():
    print(f'Tag "{tag}": {len(items)} entries')
    for c in items[:3]:
        print(f'  - {c}')

print()
print('=== RANDOM DEEP DIVE ===')
import random
if all_items:
    random_item = random.choice(all_items)
    print(json.dumps(random_item, indent=2))