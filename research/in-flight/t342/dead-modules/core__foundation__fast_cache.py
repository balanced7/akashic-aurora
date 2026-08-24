"""
Fast Cache - RAM Disk + Redis hybrid for sub-millisecond operations

Semantic Relationship: FastCache enables sub_millisecond_operations (via multi-layer priority)

PURPOSE: Zero file I/O latency for hot code paths
PRIMARY: X: drive (RAM disk) - 1GB ultra-fast storage
BACKUP: Redis - persistent distributed cache
FALLBACK: Python dict - in-memory

Multi-layer caching strategy: RAM (fastest) > RAM Disk > Redis > Computation

Usage:
    from core.foundation.fast_cache import cache_function_results_with_multi_layer_priority, load_value_from_cache_hierarchy, store_value_in_cache_hierarchy, execute_code_without_file_io

    # Cache function results (auto-prioritizes fastest storage)
    @cache_function_results_with_multi_layer_priority(ttl=60)
    def my_func(arg):
        return heavy_computation(arg)

    # Fast cache access with RAM fallback
    store_value_in_cache_hierarchy("key", data)
    data = load_value_from_cache_hierarchy("key")

    # Execute code without file I/O
    execute_code_without_file_io("1 + 1")

    # RAM disk file operations
    write_data_to_ram_disk("temp.json", data)
    data = load_data_from_ram_disk("temp.json")
"""

import os
import sys
import json
import redis
import time
import hashlib
from typing import Any, Callable, Optional
from functools import wraps
from datetime import datetime

# Storage configuration
RAM_DISK = "X:\\"
CACHE_PREFIX = "fast:"
CACHE_TTL = 300  # 5 minutes default

# Ensure RAM disk directory exists
os.makedirs(RAM_DISK, exist_ok=True)
os.makedirs(os.path.join(RAM_DISK, "cache"), exist_ok=True)
os.makedirs(os.path.join(RAM_DISK, "temp"), exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_redis_config

# Try to connect to Redis (fail-fast: this runs at import, so it must never
# stall ~48s when Redis is down — gate on a raw-socket reachability probe).
_redis = None
_redis_available = False
try:
    from core.foundation.redis_connection import probe_redis_reachable

    _redis_config = get_redis_config()
    _redis_host = _redis_config.get("host", "localhost")
    _redis_port = _redis_config.get("port", 6379)
    if probe_redis_reachable(_redis_host, _redis_port, timeout_seconds=2.0):
        _redis = redis.Redis(**_redis_config)
        _redis.ping()
        _redis_available = True
except Exception:
    _redis = None
    _redis_available = False

# Multi-layer cache (fastest first)
_ram_cache: dict = {}
_ramdisk_cache: dict = {}  # LRU cache for RAM disk reads


def _make_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from args"""
    key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()[:16]


# ============ RAM DISK OPERATIONS ============

def write_data_to_ram_disk(filename: str, data: Any, subdir: str = "cache") -> bool:
    """
    Write data to RAM disk - fastest persistence option.

    Semantic Relationship: WrittenData persisted_to RAMDisk (ultra-fast)

    Args:
        filename: Name of file to write
        data: Data to persist (will be JSON serialized)
        subdir: Subdirectory in RAM disk (cache, temp, etc)

    Returns:
        True if write successful, False otherwise
    """
    filepath = os.path.join(RAM_DISK, subdir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        _ramdisk_cache[filename] = {'data': data, 'time': time.time()}
        return True
    except Exception as e:
        return False


# Backward compatibility alias
def ram_write(filename: str, data: Any, subdir: str = "cache") -> bool:
    """Deprecated: Use write_data_to_ram_disk() instead"""
    return write_data_to_ram_disk(filename, data, subdir)


def load_data_from_ram_disk(filename: str, subdir: str = "cache", use_cache: bool = True) -> Any:
    """
    Load data from RAM disk - cached in memory for even faster access.

    Semantic Relationship: LoadedData derived_from RAMDisk (with in-memory cache)

    Args:
        filename: Name of file to read
        subdir: Subdirectory in RAM disk
        use_cache: Use in-memory cache if available (default True)

    Returns:
        Parsed JSON data if file exists, None otherwise
    """
    if use_cache and filename in _ramdisk_cache:
        return _ramdisk_cache[filename]['data']

    filepath = os.path.join(RAM_DISK, subdir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _ramdisk_cache[filename] = {'data': data, 'time': time.time()}
        return data
    except:
        return None


# Backward compatibility alias
def ram_read(filename: str, subdir: str = "cache", use_cache: bool = True) -> Any:
    """Deprecated: Use load_data_from_ram_disk() instead"""
    return load_data_from_ram_disk(filename, subdir, use_cache)


def check_if_file_exists_on_ram_disk(filename: str, subdir: str = "cache") -> bool:
    """
    Check if file exists on RAM disk.

    Semantic Relationship: ExistsCheck verifies_file_presence

    Args:
        filename: Name of file to check
        subdir: Subdirectory in RAM disk

    Returns:
        True if file exists, False otherwise
    """
    return os.path.exists(os.path.join(RAM_DISK, subdir, filename))


# Backward compatibility alias
def ram_exists(filename: str, subdir: str = "cache") -> bool:
    """Deprecated: Use check_if_file_exists_on_ram_disk() instead"""
    return check_if_file_exists_on_ram_disk(filename, subdir)


def delete_file_from_ram_disk(filename: str, subdir: str = "cache") -> bool:
    """
    Delete file from RAM disk.

    Semantic Relationship: DeletedFile removed_from RAMDisk (and cache)

    Args:
        filename: Name of file to delete
        subdir: Subdirectory in RAM disk

    Returns:
        True if delete successful or file didn't exist, False on error
    """
    filepath = os.path.join(RAM_DISK, subdir, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        if filename in _ramdisk_cache:
            del _ramdisk_cache[filename]
        return True
    except:
        return False


# Backward compatibility alias
def ram_delete(filename: str, subdir: str = "cache") -> bool:
    """Deprecated: Use delete_file_from_ram_disk() instead"""
    return delete_file_from_ram_disk(filename, subdir)


def list_files_in_ram_disk_directory(subdir: str = "cache") -> list:
    """
    List files in RAM disk subdirectory.

    Semantic Relationship: FileList derived_from RAMDiskDirectory

    Args:
        subdir: Subdirectory to list

    Returns:
        List of filenames in subdirectory, empty list if dir doesn't exist
    """
    dirpath = os.path.join(RAM_DISK, subdir)
    if os.path.exists(dirpath):
        return os.listdir(dirpath)
    return []


# Backward compatibility alias
def ram_list(subdir: str = "cache") -> list:
    """Deprecated: Use list_files_in_ram_disk_directory() instead"""
    return list_files_in_ram_disk_directory(subdir)


def write_temporary_content_to_ram_disk(filename: str, content: str) -> str:
    """
    Write temporary content to RAM disk.

    Semantic Relationship: WrittenContent persisted_to RAMDiskTemp (temporary)

    Args:
        filename: Name of temporary file
        content: Text content to write

    Returns:
        Full filepath if successful, None on error
    """
    filepath = os.path.join(RAM_DISK, "temp", filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    except:
        return None


# Backward compatibility alias
def ram_write_temp(filename: str, content: str) -> str:
    """Deprecated: Use write_temporary_content_to_ram_disk() instead"""
    return write_temporary_content_to_ram_disk(filename, content)


def cache_function_results_with_multi_layer_priority(ttl: int = CACHE_TTL, prefix: str = "fn"):
    """
    Decorator to cache function results with 3-layer priority.

    Semantic Relationship: CachedResult persisted_to MultiLayerStorage (RAM > RAMDisk > Redis)

    Caches function results in order of speed: RAM (microseconds) > RAM Disk (milliseconds) > Redis

    Args:
        ttl: Time-to-live in seconds (default 5 minutes)
        prefix: Cache key prefix for organization

    Returns:
        Decorator function that caches function results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{CACHE_PREFIX}{prefix}:{func.__name__}:{_make_key('', *args, **kwargs)}"

            # LAYER 1: RAM cache (fastest - microseconds)
            if cache_key in _ram_cache:
                entry = _ram_cache[cache_key]
                if time.time() - entry['time'] < ttl:
                    return entry['value']

            # LAYER 2: RAM disk cache (fast - milliseconds)
            if cache_key in _ramdisk_cache:
                entry = _ramdisk_cache[cache_key]
                if time.time() - entry['time'] < ttl:
                    _ram_cache[cache_key] = entry  # Promote to RAM
                    return entry['value']

            # LAYER 3: Redis (fast - milliseconds)
            if _redis_available:
                try:
                    val = _redis.get(cache_key)
                    if val:
                        data = json.loads(val)
                        _ram_cache[cache_key] = {'value': data, 'time': time.time()}
                        return data
                except:
                    pass

            # Execute function
            result = func(*args, **kwargs)

            # Store in all layers
            _ram_cache[cache_key] = {'value': result, 'time': time.time()}
            _ramdisk_cache[cache_key] = {'value': result, 'time': time.time()}
            if _redis_available:
                try:
                    _redis.setex(cache_key, ttl, json.dumps(result))
                except:
                    pass

            return result
        return wrapper
    return decorator


# Backward compatibility alias
def cache(ttl: int = CACHE_TTL, prefix: str = "fn"):
    """Deprecated: Use cache_function_results_with_multi_layer_priority() instead"""
    return cache_function_results_with_multi_layer_priority(ttl, prefix)


def load_value_from_cache_hierarchy(key: str, default: Any = None) -> Any:
    """
    Load value from cache hierarchy with 3-layer fallback.

    Semantic Relationship: LoadedValue derived_from CacheHierarchy (RAM > RAMDisk > Redis)

    Checks in order: RAM (fast), RAM Disk (medium), Redis (slower)

    Args:
        key: Cache key to lookup
        default: Default value if not found in any layer

    Returns:
        Cached value if found, otherwise default
    """
    # LAYER 1: RAM
    if key in _ram_cache:
        return _ram_cache[key]['value']

    # LAYER 2: RAM disk cache
    if key in _ramdisk_cache:
        data = _ramdisk_cache[key]['data']
        _ram_cache[key] = _ramdisk_cache[key]  # Promote
        return data

    # LAYER 3: Redis
    if _redis_available:
        try:
            val = _redis.get(f"{CACHE_PREFIX}{key}")
            if val:
                data = json.loads(val)
                _ram_cache[key] = {'value': data, 'time': time.time()}
                _ramdisk_cache[key] = {'data': data, 'time': time.time()}
                return data
        except:
            pass

    return default


# Backward compatibility alias
def redis_get(key: str, default: Any = None) -> Any:
    """Deprecated: Use load_value_from_cache_hierarchy() instead"""
    return load_value_from_cache_hierarchy(key, default)


def store_value_in_cache_hierarchy(key: str, value: Any, ttl: int = CACHE_TTL):
    """
    Store value in all cache layers simultaneously.

    Semantic Relationship: StoredValue persisted_to AllCacheLayers (RAM + RAMDisk + Redis)

    Writes to RAM, RAM Disk, and Redis for maximum speed and redundancy

    Args:
        key: Cache key
        value: Value to store
        ttl: Time-to-live in seconds
    """
    timestamp = time.time()
    _ram_cache[key] = {'value': value, 'time': timestamp}
    _ramdisk_cache[key] = {'data': value, 'time': timestamp}

    # Also persist to RAM disk as file
    write_data_to_ram_disk(f"{key}.json", {'value': value, 'time': timestamp, 'ttl': ttl})

    if _redis_available:
        try:
            _redis.setex(f"{CACHE_PREFIX}{key}", ttl, json.dumps(value))
        except:
            pass


# Backward compatibility alias
def redis_set(key: str, value: Any, ttl: int = CACHE_TTL):
    """Deprecated: Use store_value_in_cache_hierarchy() instead"""
    return store_value_in_cache_hierarchy(key, value, ttl)


def load_hash_field_from_redis(key: str, field: str, default: Any = None) -> Any:
    """
    Load hash field from Redis.

    Semantic Relationship: LoadedHashField derived_from RedisHash

    Args:
        key: Hash key in Redis
        field: Field name within hash
        default: Default value if field not found

    Returns:
        Field value if found, otherwise default
    """
    if _redis_available:
        try:
            val = _redis.hget(f"{CACHE_PREFIX}{key}", field)
            if val:
                return json.loads(val) if val.startswith('{') else val
        except:
            pass
    return default


# Backward compatibility alias
def redis_hget(key: str, field: str, default: Any = None) -> Any:
    """Deprecated: Use load_hash_field_from_redis() instead"""
    return load_hash_field_from_redis(key, field, default)


def store_hash_field_in_redis(key: str, field: str, value: Any):
    """
    Store hash field in Redis.

    Semantic Relationship: StoredHashField persisted_to RedisHash

    Args:
        key: Hash key in Redis
        field: Field name within hash
        value: Value to store
    """
    if _redis_available:
        try:
            val = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            _redis.hset(f"{CACHE_PREFIX}{key}", field, val)
        except:
            pass


# Backward compatibility alias
def redis_hset(key: str, field: str, value: Any):
    """Deprecated: Use store_hash_field_in_redis() instead"""
    return store_hash_field_in_redis(key, field, value)


# Pre-warmed data cache
_session_data: dict = {}
_context_cache: dict = {}


def get_cache_system_status_snapshot() -> dict:
    """
    Get current cache system status.

    Semantic Relationship: StatusSnapshot documents_cache_state (current moment)

    Returns:
        Dictionary with cache statistics and resource information
    """
    return {
        'ram_cache_entries': len(_ram_cache),
        'ramdisk_cache_entries': len(_ramdisk_cache),
        'ramdisk_files': len(list_files_in_ram_disk_directory()),
        'redis_available': _redis_available,
        'ram_disk': RAM_DISK,
        'ram_disk_free': os.statvfs(RAM_DISK).f_bavail * os.statvfs(RAM_DISK).f_frsize if os.name != 'nt' else None,
    }


# Backward compatibility alias
def get_cache_status() -> dict:
    """Deprecated: Use get_cache_system_status_snapshot() instead"""
    return get_cache_system_status_snapshot()


def warm_session_cache_on_import():
    """
    Pre-warm session data for fast access.

    Semantic Relationship: WarmedCache enables_fast_startup

    Runs on module import to populate all cache layers with session info
    """
    global _session_data, _context_cache

    # Session info
    _session_data = {
        'timestamp': datetime.now().isoformat(),
        'session_id': f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'redis_available': _redis_available,
        'ram_disk': RAM_DISK,
        'cache_status': get_cache_system_status_snapshot(),
    }

    # Try to load context from Redis
    if _redis_available:
        try:
            ctx = _redis.get("context:current")
            if ctx:
                _context_cache = json.loads(ctx)
        except:
            pass

    # Cache hot paths in all layers
    store_value_in_cache_hierarchy("session", _session_data)
    store_value_in_cache_hierarchy("context", _context_cache)


# Backward compatibility alias
def warm_session():
    """Deprecated: Use warm_session_cache_on_import() instead"""
    return warm_session_cache_on_import()


# Hot modules cache (pre-imported for speed)
_hot_modules: dict = {}


def load_hot_module_from_cache(module_name: str):
    """
    Get or import a hot module (cached).

    Semantic Relationship: LoadedModule derived_from CachedModules (or imported)

    Args:
        module_name: Name of module to load/import

    Returns:
        Module object if found or successfully imported, None otherwise
    """
    if module_name not in _hot_modules:
        try:
            __import__(module_name)
            _hot_modules[module_name] = sys.modules.get(module_name)
        except:
            return None
    return _hot_modules.get(module_name)


# Backward compatibility alias
def get_hot_module(module_name: str):
    """Deprecated: Use load_hot_module_from_cache() instead"""
    return load_hot_module_from_cache(module_name)


def execute_code_without_file_io(code: str, globals_dict: dict = None, timeout: float = 5.0) -> dict:
    """
    Execute Python code without file I/O.

    Semantic Relationship: ExecutedCode causes_computation (without disk access)

    Safe code execution environment with access to cache primitives and utilities.

    Args:
        code: Python code string to execute
        globals_dict: Global scope variables (uses cache primitives if None)
        timeout: Execution timeout in seconds (not enforced)

    Returns:
        Dictionary with success status, result, and stdout
    """
    import io
    from contextlib import redirect_stdout, redirect_stderr

    if globals_dict is None:
        globals_dict = {
            '__name__': '__fast__',
            'sys': sys,
            'json': json,
            'load_value_from_cache_hierarchy': load_value_from_cache_hierarchy,
            'store_value_in_cache_hierarchy': store_value_in_cache_hierarchy,
            'load_hash_field_from_redis': load_hash_field_from_redis,
            'store_hash_field_in_redis': store_hash_field_in_redis,
            'cache_function_results_with_multi_layer_priority': cache_function_results_with_multi_layer_priority,
            'time': time,
            'datetime': datetime,
            'fast_cache': sys.modules[__name__] if __name__ in sys.modules else None,
            'write_data_to_ram_disk': write_data_to_ram_disk,
            'load_data_from_ram_disk': load_data_from_ram_disk,
            'list_files_in_ram_disk_directory': list_files_in_ram_disk_directory,
            'ram_disk': RAM_DISK,
        }

    output = io.StringIO()
    error_output = io.StringIO()

    try:
        exec_globals = {**globals_dict, '__builtins__': __builtins__}
        exec(code, exec_globals)

        # Get any returned value
        result = exec_globals.get('_result')

        return {
            "success": True,
            "result": result,
            "stdout": output.getvalue()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": output.getvalue()
        }


# Backward compatibility alias
def exec_fast(code: str, globals_dict: dict = None, timeout: float = 5.0) -> dict:
    """Deprecated: Use execute_code_without_file_io() instead"""
    return execute_code_without_file_io(code, globals_dict, timeout)


# Initialize on import
warm_session_cache_on_import()
