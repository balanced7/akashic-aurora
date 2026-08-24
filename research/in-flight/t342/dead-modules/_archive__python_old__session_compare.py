import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Check OUR old format (opencode_) sessions
print('=== OUR SESSIONS (opencode_*) ===')
our_logs = [k for k in r.scan_iter('session:opencode_20260415_*:actions')]
our_logs.sort()
for k in our_logs:
    count = r.llen(k)
    print('  ' + k + ': ' + str(count) + ' entries')

# Check OTHER (session_) sessions
print()
print('=== OTHER SESSIONS (session_*) ===')
other_logs = [k for k in r.scan_iter('session:session_*')]
other_logs.sort()
for k in other_logs:
    count = r.llen(k)
    print('  ' + k + ': ' + str(count) + ' entries')

# Check active sessions in detail
print()
print('=== sessions:active STATUS ===')
active = r.hgetall('sessions:active')
for s, info in active.items():
    data = json.loads(info)
    status = data.get('status', 'N/A')
    task = data.get('task', 'N/A')
    task_str = task[:40] if task else 'N/A'
    print('  ' + s + ': ' + status + ' - ' + task_str)

# Check what's different between log types
print()
print('=== LOG TYPE COMPARISON ===')
print('Old format (opencode_): Our session logger')
print('New format (session_): New compact logger by other agent')