import json
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

with open(r'E:\AI-Setup\blackboard_data\redis_backups\redis_backup_latest.json', 'r') as f:
    data = json.load(f)

restored = 0
for key, item in data['keys'].items():
    key_type = item['type']
    value = item['value']
    
    try:
        if key_type == 'string':
            r.set(key, value)
        elif key_type == 'list':
            r.delete(key)
            if value:
                r.rpush(key, *value)
        elif key_type == 'hash':
            r.delete(key)
            if value:
                r.hset(key, mapping=value)
        elif key_type == 'set':
            r.delete(key)
            if value:
                r.sadd(key, *value)
        restored += 1
        print(f'Restored: {key} ({key_type})')
    except Exception as e:
        print(f'Failed {key}: {e}')

print(f'\nTotal restored: {restored}/{len(data["keys"])}')