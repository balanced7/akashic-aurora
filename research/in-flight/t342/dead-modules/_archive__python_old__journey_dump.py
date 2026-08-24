import redis, json
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

journey = {}

# Current task
journey['current_task'] = r.get('context:current_task')

# Milestones
journey['milestones'] = r.hgetall('context:milestones')

# Decisions (ADRs)
journey['decisions'] = r.hgetall('decisions:registry')

# Approaches tried
journey['approaches'] = r.hgetall('approaches:registry')

# Experience by task
journey['experience'] = r.hgetall('experience:registry')

# Learnings
journey['learnings_keys'] = list(r.scan_iter('learnings:*'))

# Session logs
journey['sessions'] = {}
for k in r.scan_iter('session:*:actions'):
    session_name = k.replace('session:', '').replace(':actions', '')
    items = r.lrange(k, 0, -1)
    journey['sessions'][session_name] = {'count': len(items), 'actions': items}

# New format logs
journey['new_logs'] = {}
for k in r.scan_iter('session:session_*'):
    items = r.lrange(k, 0, -1)
    journey['new_logs'][k] = items

# KB docs
journey['kb'] = r.hgetall('kb:docs:current_status')

# Architecture
journey['architecture'] = r.get('context:architecture')

print(json.dumps(journey, indent=2, default=str))