import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print('=== CURRENT LOGGING STACK ANALYSIS ===')
print()

# My session details
print('1. MY SESSION LOG DETAILS')
my_key = 'session:opencode_20260415_001327:actions'
entries = r.lrange(my_key, 0, -1)
print('   Key: ' + my_key)
print('   Entries: ' + str(len(entries)))
for e in entries[:5]:
    data = json.loads(e)
    dtype = data.get('type', 'N/A')
    desc = str(data)[:80]
    print('   - [' + dtype + '] ' + desc)
print()

# Their session details  
print('2. THEIR SESSION LOG DETAILS')
other_key = 'session:session_20260415_055030:log'
entries = r.lrange(other_key, 0, -1)
print('   Key: ' + other_key)
print('   Entries: ' + str(len(entries)))
for e in entries[:5]:
    data = json.loads(e)
    dtype = data.get('type', 'N/A')
    content = data.get('content', 'N/A')
    print('   - [' + dtype + '] ' + content)
print()

# Compare structure
print('3. STRUCTURE COMPARISON')
my_sample = json.loads(r.lrange(my_key, -1, -1)[0])
their_sample = json.loads(r.lrange(other_key, -1, -1)[0])
print('   MY keys: ' + str(list(my_sample.keys())))
print('   THEIR keys: ' + str(list(their_sample.keys())))
print()

# Check if session_logger is working
print('4. LOGGER HEALTH CHECK')
print('   My session exists: ' + str(r.exists(my_key)))
print('   My session type: ' + str(r.type(my_key)))
print()

# Check if there's a config issue in active sessions
print('5. ACTIVE SESSION STATUS')
active = r.hgetall('sessions:active')
my_active = active.get('opencode_20260415_001327', '{}')
parsed = json.loads(my_active)
print('   Session: opencode_20260415_001327')
print('   Status: ' + parsed.get('status', 'N/A'))
print('   Task: ' + parsed.get('task', 'N/A'))
print('   Last update: ' + parsed.get('last_update', 'N/A'))
print('   Last action: ' + parsed.get('last_action', 'N/A'))