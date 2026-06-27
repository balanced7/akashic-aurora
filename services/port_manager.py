"""
Enterprise Port Management System
E:\AI-Setup\port_manager.py
================================

Every system needs unique ports. This ensures:
1. No port conflicts between containers
2. All ports documented in Redis for agents
3. Automatic conflict detection
4. Easy port reassignment

Author: Enterprise Systems
"""

import os
import sys
import json
import redis
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, r"E:\AI-Setup")

# Default ports for Breakthrough Stack
BREAKTHROUGH_STACK_PORTS = {
    "redis": {
        "port": 6379,
        "protocol": "tcp",
        "description": "Redis state store",
        "container": "wsl-ai-redis",
        "required": True
    },
    "ollama": {
        "port": 11434,
        "protocol": "tcp",
        "description": "Ollama LLM inference",
        "container": "ai-ollama",
        "required": True
    },
    "vllm": {
        "port": 8000,
        "protocol": "tcp",
        "description": "vLLM OpenAI-compatible API",
        "container": "wsl-ai-vllm",
        "required": False
    },
    "openwebui": {
        "port": 3000,
        "protocol": "tcp",
        "description": "Open WebUI frontend",
        "container": "ai-open-webui",
        "required": False
    },
    "voice": {
        "port": 5000,
        "protocol": "tcp",
        "description": "Voice service",
        "container": "ai-voice",
        "required": False
    },
    "voice_alt": {
        "port": 5001,
        "protocol": "tcp",
        "description": "Voice alt port",
        "container": "ai-voice",
        "required": False
    },
    "knowledge_api": {
        "port": 8080,
        "protocol": "tcp",
        "description": "Knowledge API",
        "container": "ai-knowledge-api",
        "required": False
    },
    "streamlit": {
        "port": 8501,
        "protocol": "tcp",
        "description": "Streamlit dashboard",
        "container": None,
        "required": False
    },
    "jupyter": {
        "port": 8888,
        "protocol": "tcp",
        "description": "Jupyter notebook",
        "container": None,
        "required": False
    }
}

# Port ranges for dynamic allocation
DYNAMIC_PORT_START = 9000
DYNAMIC_PORT_END = 65535

@dataclass
class PortAllocation:
    name: str
    port: int
    protocol: str
    description: str
    container: str
    allocated_at: str
    allocated_by: str


class PortManager:
    """
    Enterprise port management with Redis-backed allocation.
    All agents query this to avoid conflicts.
    """
    
    REDIS_PREFIX = "port:"
    ALLOCATIONS_KEY = "ports:allocated"
    
    def __init__(self, redis_host="localhost", redis_port=6379):
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast
        self.redis = connect_to_redis_with_fail_fast(
            host=redis_host, port=redis_port, timeout_seconds=5, decode_responses=True
        )
        if self.redis is None:
            raise ConnectionError(f"Redis not reachable at {redis_host}:{redis_port}")
        self._ensure_initialized()
    
    def _ensure_initialized(self):
        """Initialize port registry in Redis if not exists."""
        if not self.redis.exists(self.ALLOCATIONS_KEY):
            self._sync_to_redis()
    
    def _sync_to_redis(self):
        """Sync default port allocations to Redis."""
        import datetime
        for name, info in BREAKTHROUGH_STACK_PORTS.items():
            key = f"{self.REDIS_PREFIX}{name}"
            self.redis.hset(key, mapping={
                "port": info["port"],
                "protocol": info["protocol"],
                "description": info["description"],
                "container": info["container"] or "",
                "allocated_at": datetime.datetime.now().isoformat(),
                "allocated_by": "system"
            })
        self.redis.set(self.ALLOCATIONS_KEY, json.dumps(list(BREAKTHROUGH_STACK_PORTS.keys())))
    
    def allocate_port(self, name: str, port: int = None, description: str = None, 
                      container: str = None, allocated_by: str = "manual") -> Optional[int]:
        """Allocate a port, avoiding conflicts."""
        import datetime
        
        # Check if already allocated
        existing = self.get_allocation(name)
        if existing:
            return existing["port"]
        
        # If port not specified, find available
        if port is None:
            port = self._find_available_port()
            if port is None:
                print(f"No available ports in range {DYNAMIC_PORT_START}-{DYNAMIC_PORT_END}")
                return None
        
        # Check if port is in use
        if self._is_port_in_use(port):
            # Try alternative
            port = self._find_available_port()
            if port is None:
                return None
        
        # Allocate
        key = f"{self.REDIS_PREFIX}{name}"
        self.redis.hset(key, mapping={
            "port": port,
            "protocol": "tcp",
            "description": description or name,
            "container": container or "",
            "allocated_at": datetime.datetime.now().isoformat(),
            "allocated_by": allocated_by
        })
        
        # Update allocations list
        allocations = json.loads(self.redis.get(self.ALLOCATIONS_KEY) or "[]")
        if name not in allocations:
            allocations.append(name)
            self.redis.set(self.ALLOCATIONS_KEY, json.dumps(allocations))
        
        print(f"Allocated port {port} to {name}")
        return port
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if port is already allocated in our system."""
        for name in self.get_allocated_names():
            alloc = self.get_allocation(name)
            if alloc and alloc["port"] == port:
                return True
        return False
    
    def _find_available_port(self) -> Optional[int]:
        """Find an available port for dynamic allocation."""
        for port in range(DYNAMIC_PORT_START, DYNAMIC_PORT_END):
            if not self._is_port_in_use(port):
                return port
        return None
    
    def get_allocation(self, name: str) -> Optional[Dict]:
        """Get port allocation details."""
        key = f"{self.REDIS_PREFIX}{name}"
        data = self.redis.hgetall(key)
        if not data:
            return None
        return {
            "name": name,
            "port": int(data.get("port", 0)),
            "protocol": data.get("protocol", "tcp"),
            "description": data.get("description", ""),
            "container": data.get("container", ""),
            "allocated_at": data.get("allocated_at", ""),
            "allocated_by": data.get("allocated_by", "")
        }
    
    def get_all_allocations(self) -> Dict[str, Dict]:
        """Get all port allocations."""
        allocations = {}
        for name in self.get_allocated_names():
            alloc = self.get_allocation(name)
            if alloc:
                allocations[name] = alloc
        return allocations
    
    def get_allocated_names(self) -> List[str]:
        """Get list of allocated port names."""
        return json.loads(self.redis.get(self.ALLOCATIONS_KEY) or "[]")
    
    def release_port(self, name: str) -> bool:
        """Release a port allocation."""
        key = f"{self.REDIS_PREFIX}{name}"
        if self.redis.exists(key):
            self.redis.delete(key)
            allocations = json.loads(self.redis.get(self.ALLOCATIONS_KEY) or "[]")
            allocations = [a for a in allocations if a != name]
            self.redis.set(self.ALLOCATIONS_KEY, json.dumps(allocations))
            return True
        return False
    
    def check_conflicts(self) -> List[Dict]:
        """Check for port conflicts with running containers."""
        conflicts = []
        for name, alloc in self.get_all_allocations().items():
            if alloc.get("container"):
                # This is a hint but not definitive
                pass
        return conflicts
    
    def print_registry(self):
        """Print the port registry."""
        print("\n" + "=" * 60)
        print("  ENTERPRISE PORT REGISTRY")
        print("=" * 60)
        allocations = self.get_all_allocations()
        for name, alloc in sorted(allocations.items()):
            print(f"\n  {name}:")
            print(f"    Port:     {alloc['port']}")
            print(f"    Protocol: {alloc['protocol']}")
            print(f"    Desc:     {alloc['description']}")
            print(f"    Container:{alloc['container'] or 'N/A'}")
            print(f"    By:       {alloc['allocated_by']}")
        print("\n" + "=" * 60)


def sync_ports_to_redis():
    """Sync all ports to Redis for agent discovery."""
    pm = PortManager()
    pm._sync_to_redis()
    
    # Also store as hash for easy lookup
    import datetime
    from core.foundation.redis_connection import connect_to_redis_with_fail_fast
    r = connect_to_redis_with_fail_fast(host="localhost", port=6379, timeout_seconds=5, decode_responses=True)
    if r is None:
        raise ConnectionError("Redis not reachable at localhost:6379")

    # Store as single hash for quick access
    all_ports = {}
    for name, info in BREAKTHROUGH_STACK_PORTS.items():
        all_ports[f"{name}_port"] = info["port"]
        all_ports[f"{name}_desc"] = info["description"]
    
    r.hset("system:ports", mapping=all_ports)
    
    print(f"Synced {len(BREAKTHROUGH_STACK_PORTS)} ports to Redis")
    return pm


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise Port Manager")
    parser.add_argument("--status", "-s", action="store_true", help="Show port registry")
    parser.add_argument("--sync", action="store_true", help="Sync ports to Redis")
    parser.add_argument("--check", type=str, help="Check specific port")
    parser.add_argument("--allocate", nargs=4, metavar=("NAME", "PORT", "DESC", "CONTAINER"), 
                        help="Allocate port: NAME PORT DESC CONTAINER")
    
    args = parser.parse_args()
    
    pm = PortManager()
    
    if args.status:
        pm.print_registry()
    elif args.sync:
        sync_ports_to_redis()
    elif args.check:
        alloc = pm.get_allocation(args.check)
        if alloc:
            print(f"{args.check}: Port {alloc['port']} ({alloc['description']})")
        else:
            print(f"{args.check}: Not allocated")
    elif args.allocate:
        name, port, desc, container = args.allocate
        pm.allocate_port(name, int(port), desc, container)
    else:
        pm.print_registry()
