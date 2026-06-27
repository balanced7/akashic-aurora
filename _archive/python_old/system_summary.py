import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Summary
print('=== SYSTEM SUMMARY ===')
print(f'Total Redis keys: {r.dbsize()}')
print()

# Categories
categories = {
    'context': list(r.scan_iter('context:*')),
    'decisions': list(r.scan_iter('decisions:*')),
    'approaches': list(r.scan_iter('approaches:*')),
    'learnings': list(r.scan_iter('learnings:*')),
    'kb': list(r.scan_iter('kb:*')),
    'experience': list(r.scan_iter('experience:*')),
    'session': list(r.scan_iter('session:*')),
    'reflections': list(r.scan_iter('reflections:*')),
}

for cat, keys in categories.items():
    print(f'{cat}: {len(keys)} keys')

# Current task
task_str = r.get('context:current_task')
if task_str:
    t = json.loads(task_str)
    task_name = t.get('task', 'N/A')
    print()
    print(f'CURRENT TASK: {task_name}')
    
    # What's happening now
    print()
    print('=== WHAT THE OTHER INSTANCE IS DOING ===')
    # Get recent logs from the new format
    new_logs = sorted([k for k in r.scan_iter('session:session_*')])
    for log_key in new_logs[-3:]:
        items = r.lrange(log_key, 0, -1)
        for item in items[-2:]:
            data = json.loads(item)
            content = data.get('content', '')
            print(f'  {content[:80]}')