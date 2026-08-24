#!/usr/bin/env python3
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("=" * 60)
print("  AKASHIC AURORA - PORT & SERVICE REGISTRY")
print("=" * 60)

print("\n[1] PORT ALLOCATIONS")
print("-" * 40)
for key in sorted(r.keys('port:*')):
    data = r.hgetall(key)
    port = data.get('port', 'N/A')
    desc = data.get('description', 'N/A')
    proto = data.get('protocol', 'N/A')
    print(f"  {key}: {port}/{proto} - {desc}")

print("\n[2] SERVICES STATUS")
print("-" * 40)
services = [
    ('redis', 'localhost', 6379),
    ('redis-replica1', 'localhost', 6380),
    ('redis-replica2', 'localhost', 6381),
    ('sentinel1', 'localhost', 26379),
    ('sentinel2', 'localhost', 26380),
    ('sentinel3', 'localhost', 26381),
    ('ollama', 'localhost', 11434),
    ('gemma-voice-service', 'localhost', 5000),
]
for name, host, port in services:
    try:
        if name == 'ollama':
            import requests
            resp = requests.get(f'http://{host}:{port}/api/tags', timeout=1)
            status = "UP" if resp.status_code == 200 else "DOWN"
        else:
            r2 = redis.Redis(host=host, port=port, socket_connect_timeout=1)
            r2.ping()
            status = "UP"
    except:
        status = "DOWN"
    print(f"  {name} ({host}:{port}): {status}")

print("\n[3] GATEWAY IP MAPPING")
print("-" * 40)
gateway_ips = [
    ('localhost', 'WSL internal'),
    ('172.26.124.50', 'WSL bridge IP'),
]
for ip, desc in gateway_ips:
    print(f"  {ip} - {desc}")

print("\n" + "=" * 60)