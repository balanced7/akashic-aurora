#!/usr/bin/env python3
"""Update port registry in Redis"""
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

ports = {
    'port:redis': {
        'port': '6379',
        'protocol': 'tcp',
        'description': 'Redis state store (master)',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:redis-replica1': {
        'port': '6380',
        'protocol': 'tcp',
        'description': 'Redis read replica 1',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:redis-replica2': {
        'port': '6381',
        'protocol': 'tcp',
        'description': 'Redis read replica 2',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:sentinel1': {
        'port': '26379',
        'protocol': 'tcp',
        'description': 'Redis Sentinel 1 (failover monitor)',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:sentinel2': {
        'port': '26380',
        'protocol': 'tcp',
        'description': 'Redis Sentinel 2 (failover monitor)',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:sentinel3': {
        'port': '26381',
        'protocol': 'tcp',
        'description': 'Redis Sentinel 3 (failover monitor)',
        'container': 'wsl-ai-redis',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:ollama': {
        'port': '11434',
        'protocol': 'http',
        'description': 'Ollama LLM inference API',
        'models': 'gemma2:2b',
        'allocated_at': '2026-04-22T23:30:00'
    },
    'port:gemma-voice': {
        'port': '5000',
        'protocol': 'http',
        'description': 'Gemma Voice AI Service (chat, STT, TTS)',
        'components': 'flask+whisper+espeak',
        'allocated_at': '2026-04-22T23:45:00'
    },
    'port:gemma-stt': {
        'port': '5001',
        'protocol': 'http',
        'description': 'STT API (faster-whisper)',
        'allocated_at': '2026-04-22T23:45:00'
    },
    'port:gemma-tts': {
        'port': '5002',
        'protocol': 'http',
        'description': 'TTS API (espeak-ng)',
        'allocated_at': '2026-04-22T23:45:00'
    },
    'port:openwebui': {
        'port': '3000',
        'protocol': 'http',
        'description': 'Open WebUI frontend (future)',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:knowledge': {
        'port': '8080',
        'protocol': 'http',
        'description': 'Knowledge base API',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:florence2': {
        'port': '9001',
        'protocol': 'http',
        'description': 'Florence-2 Vision API',
        'allocated_at': '2026-04-18T22:06:39'
    },
    'port:jupyter': {
        'port': '8888',
        'protocol': 'http',
        'description': 'Jupyter notebook',
        'allocated_at': '2026-04-18T22:06:39'
    },
}

for key, data in ports.items():
    r.delete(key)
    r.hset(key, mapping=data)

print("Port registry updated!")
print("\nCurrent allocations:")
for key in sorted(r.keys('port:*')):
    data = r.hgetall(key)
    print(f"  {key}: {data['port']} - {data['description']}")