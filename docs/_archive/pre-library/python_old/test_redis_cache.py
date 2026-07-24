#!/usr/bin/env python3
"""
Test Redis connectivity and session cache
"""
import socket
import sys

def test_port(host, port, timeout=2):
    """Test if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    finally:
        sock.close()

def main():
    print("=" * 60)
    print("Akashic Aurora - Redis & Session Cache Diagnostics")
    print("=" * 60)
    print()

    # Test ports
    ports = {
        6380: "WSL Redis (application master - WRITES)",
        6379: "WSL Redis (read replica)",
        16379: "Docker Redis Stack mirror",
    }

    print("[1] Port Connectivity Test")
    print("-" * 60)
    for port, desc in ports.items():
        open_port = test_port('127.0.0.1', port)
        status = "[OK]" if open_port else "[CLOSED]"
        print(f"  {port:5d}: {status:10s} | {desc}")
    print()

    # Try to connect with redis-py
    print("[2] Attempting Redis Connection (port 6380)")
    print("-" * 60)
    try:
        import redis
        print("  redis-py module: [OK] Found")

        try:
            r = redis.Redis(
                host='localhost',
                port=6380,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_keepalive=True
            )

            # Ping
            ping_result = r.ping()
            print(f"  PING response: [OK] {ping_result}")

            # Get server info
            info = r.info('server')
            print(f"  Redis version: {info.get('redis_version', 'unknown')}")
            print(f"  Uptime: {info.get('uptime_in_seconds', 0)} seconds")
            print()

            # Check session data
            print("[3] Session Cache Contents")
            print("-" * 60)

            # Session keys
            session_keys = r.keys('session:*')
            print(f"  Total session:* keys: {len(session_keys)}")

            # Summaries
            summaries = r.keys('session:summary:*')
            print(f"  Session summaries: {len(summaries)}")
            if summaries:
                print("\n  Recent summaries:")
                for key in sorted(summaries, reverse=True)[:5]:
                    val = r.get(key)
                    snippet = str(val)[:150].replace('\n', ' ')
                    print(f"    {key}")
                    print(f"      -> {snippet}...")
            print()

            # Events stream
            print("[4] Session Events Stream")
            print("-" * 60)
            try:
                stream_len = r.xlen('session:events')
                print(f"  Total events: {stream_len}")

                if stream_len > 0:
                    print(f"\n  Last 5 events:")
                    events = r.xrevrange('session:events', count=5)
                    for event_id, event_data in events:
                        print(f"    {event_id.decode() if isinstance(event_id, bytes) else event_id}:")
                        for k, v in event_data.items():
                            k_str = k.decode() if isinstance(k, bytes) else k
                            v_str = v.decode()[:100] if isinstance(v, bytes) else str(v)[:100]
                            print(f"      {k_str}: {v_str}")
            except Exception as e:
                print(f"  [WARNING] Could not read stream: {e}")
            print()

            # Learning data
            print("[5] Learning Storage (learn:*)")
            print("-" * 60)
            learn_keys = r.keys('learn:*')
            print(f"  Total learn:* keys: {len(learn_keys)}")
            for key in learn_keys[:10]:
                print(f"    {key}")
            print()

            # Context keys
            print("[6] Context Keys")
            print("-" * 60)
            context_keys = r.keys('context:*')
            migration_summary = r.get('migration:summary')
            print(f"  context:* keys: {len(context_keys)}")
            print(f"  migration:summary exists: {migration_summary is not None}")
            if migration_summary:
                print(f"    Content: {migration_summary[:200]}...")
            print()

            # Session compressor status
            print("[7] Session Compressor Status")
            print("-" * 60)
            compressor_status = r.get('system:compressor:status')
            print(f"  Compressor status key exists: {compressor_status is not None}")
            if compressor_status:
                print(f"    {compressor_status}")
            print()

        except redis.ConnectionError as e:
            print(f"  [FAIL] Connection failed: {e}")
            print()
            print("  DIAGNOSIS:")
            print("    - Redis port 6380 is not accessible")
            print("    - Redis might not be running in WSL")
            print("    - WSL Ubuntu-Migrate might not be started")
            print()
            print("  SUGGESTED FIX:")
            print("    WSL not running. Check bootstrap.md for startup commands.")

    except ImportError:
        print("  [FAIL] redis-py not installed")
        print()
        print("  Install with: pip install redis")

    print()
    print("=" * 60)
    print("Diagnostics complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
