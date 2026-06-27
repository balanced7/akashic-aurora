"""
Redis HA Manager - Triple Redundancy with Sentinel
================================================
Enterprise-grade Redis High Availability implementation.

ARCHITECTURE:
- 1 Master (port 6379) - Primary for writes
- 2 Replicas (ports 6380, 6381) - Read redundancy
- 3 Sentinels (ports 26379, 26380, 26381) - Automatic failover

QUORUM: 2 (majority of 3 Sentinels needed to failover)

Author: Senior Systems Architect
Version: 1.0 Enterprise HA
"""

import os
import sys
import json
import time
import socket
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, r"E:\AI-Setup")
from dataclasses import dataclass
from enum import Enum

# Configuration
REDIS_MASTER_PORT = 6379
REDIS_REPLICA1_PORT = 6380
REDIS_REPLICA2_PORT = 6381

SENTINEL1_PORT = 26379
SENTINEL2_PORT = 26380
SENTINEL3_PORT = 26381

SENTINEL_QUORUM = 2
SENTINEL_DOWN_AFTER_MS = 5000

WSL_DISTRO = "Ubuntu-24.04"
BASE_DIR = r"E:\AI-Setup\dockerized-ai\redis"

# Docker network mode for WSL2
DOCKER_NETWORK = "host"  # Use host networking to avoid NAT issues


class RedisRole(Enum):
    MASTER = "master"
    REPLICA = "replica"
    SENTINEL = "sentinel"


@dataclass
class RedisInstance:
    name: str
    role: RedisRole
    host: str
    port: int
    status: str
    is_healthy: bool = False
    last_ping: float = 0


class RedisHAManager:
    """
    Manages triple-redundant Redis setup with Sentinel.
    """
    
    def __init__(self):
        self.instances: Dict[str, RedisInstance] = {}
        self.current_master: Optional[RedisInstance] = None
        self.sentinel_clients: List[Tuple[str, int]] = [
            ("127.0.0.1", SENTINEL1_PORT),
            ("127.0.0.1", SENTINEL2_PORT),
            ("127.0.0.1", SENTINEL3_PORT)
        ]
        self._lock = threading.Lock()
        
    def _run_wsl(self, cmd: List[str], timeout: int = 30) -> Tuple[str, int]:
        """Execute command in WSL2"""
        full_cmd = ["wsl.exe", "-d", WSL_DISTRO, "-e"] + cmd
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "TIMEOUT", -1
        except Exception as e:
            return str(e), -1
    
    def _redis_command(self, host: str, port: int, cmd: str) -> Tuple[str, int]:
        """Run redis-cli command"""
        return self._run_wsl(["redis-cli", "-h", host, "-p", str(port), cmd])
    
    def _sentinel_command(self, host: str, port: int, cmd: str) -> Tuple[str, int]:
        """Run sentinel command"""
        return self._run_wsl(["redis-cli", "-p", str(port), cmd])
    
    def get_current_master_via_sentinel(self) -> Optional[Tuple[str, int]]:
        """Get current master address from Sentinel"""
        for host, port in self.sentinel_clients:
            output, code = self._sentinel_command(host, port, f"SENTINEL get-master-addr-by-name breakthrough")
            if code == 0 and output:
                parts = output.split('\n')
                if len(parts) >= 2:
                    try:
                        ip = parts[0].strip()
                        redis_port = int(parts[1].strip())
                        if ip and redis_port:
                            return (ip, redis_port)
                    except:
                        pass
        return None
    
    def check_instance_health(self, host: str, port: int, role: RedisRole) -> bool:
        """Check if a Redis instance is healthy"""
        try:
            if role == RedisRole.SENTINEL:
                output, code = self._sentinel_command(host, port, "PING")
            else:
                output, code = self._redis_command(host, port, "PING")
            
            if output == "PONG":
                return True
        except:
            pass
        return False
    
    def get_replication_status(self, host: str, port: int) -> Dict[str, Any]:
        """Get replication info from a Redis instance"""
        output, code = self._redis_command(host, port, "INFO replication")
        if code != 0:
            return {"status": "error", "output": output}
        
        result = {"status": "ok"}
        for line in output.split('\n'):
            if ':' in line:
                key, value = line.strip().split(':', 1)
                result[key] = value
        return result
    
    def get_sentinel_master_info(self, host: str, port: int) -> Dict[str, Any]:
        """Get master info from Sentinel"""
        output, code = self._sentinel_command(host, port, "SENTINEL master breakthrough")
        if code != 0:
            return {"status": "error"}
        
        result = {"status": "ok"}
        for line in output.split('\n'):
            if ':' in line:
                parts = line.strip().split(':', 1)
                if len(parts) == 2:
                    result[parts[0]] = parts[1]
        return result
    
    def get_all_sentinel_info(self) -> List[Dict[str, Any]]:
        """Get info from all Sentinels"""
        results = []
        for host, port in self.sentinel_clients:
            info = self.get_sentinel_master_info(host, port)
            info["sentinel_host"] = host
            info["sentinel_port"] = port
            results.append(info)
        return results
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive health of the Redis HA system"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "sentinels": [],
            "redis_instances": [],
            "current_master": None,
            "quorum_reachable": 0,
            "system_healthy": False
        }
        
        # Get master from Sentinel
        master = self.get_current_master_via_sentinel()
        if master:
            health["current_master"] = {"host": master[0], "port": master[1]}
        
        # Check each Sentinel
        for host, port in self.sentinel_clients:
            is_healthy = self.check_instance_health(host, port, RedisRole.SENTINEL)
            sentinel_info = self.get_sentinel_master_info(host, port)
            
            if is_healthy:
                health["quorum_reachable"] += 1
            
            health["sentinels"].append({
                "host": host,
                "port": port,
                "healthy": is_healthy,
                "master_ip": sentinel_info.get("ip"),
                "master_port": sentinel_info.get("port"),
                "flags": sentinel_info.get("flags")
            })
        
        # Check Redis instances
        redis_instances = [
            ("master", "127.0.0.1", REDIS_MASTER_PORT, RedisRole.MASTER),
            ("replica1", "127.0.0.1", REDIS_REPLICA1_PORT, RedisRole.REPLICA),
            ("replica2", "127.0.0.1", REDIS_REPLICA2_PORT, RedisRole.REPLICA),
        ]
        
        for name, host, port, role in redis_instances:
            is_healthy = self.check_instance_health(host, port, role)
            rep_status = self.get_replication_status(host, port) if role != RedisRole.MASTER else {}
            
            health["redis_instances"].append({
                "name": name,
                "host": host,
                "port": port,
                "role": role.value,
                "healthy": is_healthy,
                "replication": rep_status
            })
        
        # System healthy if quorum reached and master known
        health["system_healthy"] = (
            health["quorum_reachable"] >= SENTINEL_QUORUM and
            health["current_master"] is not None
        )
        
        return health
    
    def print_health_report(self):
        """Print human-readable health report"""
        health = self.get_system_health()
        
        print("\n" + "=" * 70)
        print("  REDIS HIGH AVAILABILITY - TRIPLE REDUNDANCY")
        print("=" * 70)
        print(f"\nTimestamp: {health['timestamp']}")
        print(f"System Healthy: {'YES ✓' if health['system_healthy'] else 'NO ✗'}")
        print(f"Quorum Reachable: {health['quorum_reachable']}/{len(self.sentinel_clients)}")
        
        print("\n--- Current Master ---")
        if health['current_master']:
            m = health['current_master']
            print(f"  {m['host']}:{m['port']}")
        else:
            print("  UNKNOWN (failover in progress?)")
        
        print("\n--- Sentinels ---")
        for s in health['sentinels']:
            status = "[OK]" if s['healthy'] else "[FAIL]"
            print(f"  {status} {s['host']}:{s['port']} -> master={s.get('master_ip')}:{s.get('master_port')} flags={s.get('flags')}")
        
        print("\n--- Redis Instances ---")
        for r in health['redis_instances']:
            status = "[OK]" if r['healthy'] else "[FAIL]"
            role = r['role'].upper()
            print(f"  {status} {r['name']} ({role}) {r['host']}:{r['port']}")
        
        print("\n" + "=" * 70 + "\n")
        
        return health


def create_ha_docker_compose() -> str:
    """
    Generate docker-compose.yml for Redis HA setup.
    Uses host networking to avoid Docker NAT issues with Sentinel.
    """
    return """version: '3.8'

services:
  # Redis Master
  redis-master:
    image: redis:alpine
    container_name: redis-master
    ports:
      - "6379:6379"
    volumes:
      - redis-master-data:/data
    command: redis-server --appendonly yes --requirepass redis-master-pass
    restart: unless-stopped
    networks:
      - redis-ha

  # Redis Replica 1
  redis-replica1:
    image: redis:alpine
    container_name: redis-replica1
    ports:
      - "6380:6380"
    volumes:
      - redis-replica1-data:/data
    command: redis-server --appendonly yes --replicaof redis-master 6379 --requirepass redis-master-pass
    depends_on:
      - redis-master
    restart: unless-stopped
    networks:
      - redis-ha

  # Redis Replica 2
  redis-replica2:
    image: redis:alpine
    container_name: redis-replica2
    ports:
      - "6381:6381"
    volumes:
      - redis-replica2-data:/data
    command: redis-server --appendonly yes --replicaof redis-master 6379 --requirepass redis-master-pass
    depends_on:
      - redis-master
    restart: unless-stopped
    networks:
      - redis-ha

  # Sentinel 1
  sentinel1:
    image: redis:alpine
    container_name: sentinel1
    ports:
      - "26379:26379"
    volumes:
      - ./sentinel1.conf:/usr/local/etc/redis/sentinel.conf:ro
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    restart: unless-stopped
    networks:
      - redis-ha

  # Sentinel 2
  sentinel2:
    image: redis:alpine
    container_name: sentinel2
    ports:
      - "26380:26380"
    volumes:
      - ./sentinel2.conf:/usr/local/etc/redis/sentinel.conf:ro
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    restart: unless-stopped
    networks:
      - redis-ha

  # Sentinel 3
  sentinel3:
    image: redis:alpine
    container_name: sentinel3
    ports:
      - "26381:26381"
    volumes:
      - ./sentinel3.conf:/usr/local/etc/redis/sentinel.conf:ro
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    restart: unless-stopped
    networks:
      - redis-ha

volumes:
  redis-master-data:
  redis-replica1-data:
  redis-replica2-data:

networks:
  redis-ha:
    driver: bridge
"""


def create_sentinel_config(port: int, output_path: str):
    """Create a Sentinel configuration file"""
    config = f"""port {port}
sentinel monitor breakthrough 127.0.0.1 6379 2
sentinel down-after-milliseconds breakthrough 5000
sentinel failover-timeout breakthrough 60000
sentinel parallel-syncs breakthrough 1
sentinel deny-scripts-reconfig yes
dir /tmp
"""
    with open(output_path, 'w') as f:
        f.write(config)
    print(f"Created Sentinel config: {output_path}")


def get_sentinel_client(host: str = "127.0.0.1", port: int = 26379):
    """Get a Sentinel client connection for service discovery"""
    from core.foundation.redis_connection import connect_to_redis_with_fail_fast
    return connect_to_redis_with_fail_fast(
        host=host, port=port, timeout_seconds=5, decode_responses=False
    )


def get_current_master_from_sentinel(host: str = "127.0.0.1", port: int = 26379) -> Optional[Tuple[str, int]]:
    """Get current master address from Sentinel"""
    try:
        client = get_sentinel_client(host, port)
        result = client.execute_command("SENTINEL", "get-master-addr-by-name", "breakthrough")
        if result:
            return (result[0].decode(), int(result[1]))
    except Exception as e:
        print(f"Sentinel query failed: {e}")
    return None


def wait_for_failover(timeout: int = 60) -> bool:
    """Wait for failover to complete"""
    start = time.time()
    old_master = get_current_master_from_sentinel()
    
    while time.time() - start < timeout:
        new_master = get_current_master_from_sentinel()
        if new_master and new_master != old_master:
            print(f"Failover complete: {old_master} -> {new_master}")
            return True
        time.sleep(1)
    
    print("Failover timeout")
    return False


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis HA Manager")
    parser.add_argument("--health", "-H", action="store_true", help="Show system health")
    parser.add_argument("--master", "-m", action="store_true", help="Get current master")
    parser.add_argument("--setup", "-s", action="store_true", help="Generate HA docker-compose")
    parser.add_argument("--sentinel-config", "-c", type=int, metavar="PORT", help="Create sentinel config for port")
    
    args = parser.parse_args()
    
    manager = RedisHAManager()
    
    if args.health:
        manager.print_health_report()
    elif args.master:
        master = manager.get_current_master_via_sentinel()
        if master:
            print(f"Current master: {master[0]}:{master[1]}")
        else:
            print("Master unknown (failover in progress?)")
    elif args.setup:
        compose = create_ha_docker_compose()
        output_file = os.path.join(BASE_DIR, "docker-compose-ha.yml")
        with open(output_file, 'w') as f:
            f.write(compose)
        print(f"Generated: {output_file}")
    elif args.sentinel_config:
        create_sentinel_config(args.sentinel_config, 
                            os.path.join(BASE_DIR, f"sentinel{args.sentinel_config - 26379 + 1}.conf"))
    else:
        manager.print_health_report()
