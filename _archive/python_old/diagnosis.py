import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# See what we need to fix
print('=== DIAGNOSIS ===')
print()

# My old format last entry
my_key = 'session:opencode_20260415_001327:actions'
my_count = r.llen(my_key)
my_last = r.lrange(my_key, -1, -1)
print('MY SESSION: ' + my_key)
print('  Entries: ' + str(my_count))
if my_last:
    data = json.loads(my_last[0])
    print('  Last timestamp: ' + data.get('timestamp', 'N/A'))
print()

# Their new format
other_key = 'session:session_20260415_055030:log'
other_count = r.llen(other_key)
print('THEIR SESSION: ' + other_key)
print('  Entries: ' + str(other_count))
if r.llen(other_key) > 0:
    other_last = r.lrange(other_key, -1, -1)
    data = json.loads(other_last[0])
    print('  Last timestamp: ' + data.get('timestamp', 'N/A'))
print()

# Problem: my session logger stopped at 04:42
# Solution: My session should start logging again OR merge into their format

print('=== SOLUTION OPTIONS ===')
print('1. FIX: Start my logger again (need session restart)')
print('2. MERGE: Continue logging to opencode_ format but use their pattern')
print('3. SYNC: Both log to both formats for redundancy')

# Check current session status
print()
print('=== ACTIVE SESSION ===')
active = r.hgetall('sessions:active')
my_session = active.get('opencode_20260415_001327', '{}')
parsed = json.loads(my_session)
print('  Session: opencode_20260415_001327')
print('  Status: ' + parsed.get('status', 'N/A'))
print('  Task: ' + parsed.get('task', 'N/A'))