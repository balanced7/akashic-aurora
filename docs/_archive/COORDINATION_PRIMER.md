"""
ENTERPRISE COORDINATION PRIMER - AKASHIC AURORA
================================================
Version: 3.0
Updated: 2026-04-14

This document codifies enterprise-grade coordination patterns for all agents.
Every agent MUST understand and apply these patterns.

Source of truth: Redis key "kb:docs:coordination_primer"
Searchable by: "coordination", "patterns", "enterprise", "circuit", "breaker", "retry"
"""

# ============================================================================
# SECTION 1: THE EIGHT FALLACIES OF DISTRIBUTED SYSTEMS
# ============================================================================

FALLACIES = """
THE EIGHT FALLACIES (Every Agent Must Know):
============================================

1. THE NETWORK IS RELIABLE
   - Always implement retries with circuit breakers
   - Never assume a call will succeed
   - Plan for network partitions

2. LATENCY IS ZERO
   - All remote calls can timeout
   - Add timeout handling to ALL operations
   - Monitor latency trends

3. BANDWIDTH IS INFINITE
   - Don't flood connections
   - Implement rate limiting
   - Use pagination for large data

4. THE NETWORK IS SECURE
   - Always validate inputs
   - Encrypt sensitive data
   - Log security events

5. TOPOLOGY DOESN'T CHANGE
   - Use service discovery
   - Don't hardcode IPs or ports
   - Query Redis for current state

6. THERE IS ONE ADMINISTRATOR
   - Document all configuration
   - Use configuration management
   - Make configs versioned

7. COMPONENT VERSIONING IS SIMPLE
   - Assume backward compatibility may break
   - Version your APIs
   - Maintain changelogs

8. OBSERVABILITY CAN BE DELAYED
   - Log EVERY significant action
   - Health check all components
   - Alert on anomalies
"""

# ============================================================================
# SECTION 2: CIRCUIT BREAKER PATTERN
# ============================================================================

CIRCUIT_BREAKER = """
CIRCUIT BREAKER PATTERN (Prevent Cascading Failures):
=====================================================

STATES:
-------
CLOSED -> Normal operation, requests pass through
OPEN -> Failures detected, requests fail fast
HALF-OPEN -> Testing recovery, limited requests

IMPLEMENTATION:
---------------
After 3 consecutive failures:
  - Trip circuit to OPEN
  - Return error immediately
  - Log failure event

After 30 seconds in OPEN:
  - Move to HALF-OPEN
  - Allow 1 test request through

On test success:
  - Return to CLOSED
  - Reset failure counter

On test failure:
  - Return to OPEN
  - Wait 60 seconds

FOR OUR STACK:
--------------
Redis Circuit: If Redis fails 3x, fallback to file-based state
GPU Circuit: If GPU fails 3x, use CPU-only mode
Ollama Circuit: If Ollama fails 3x, try vLLM fallback
HTTP Circuit: If web fetch fails 3x, return cached content

REDIS KEY FORMAT:
----------------
circuit:<service>:state = "closed|open|half-open"
circuit:<service>:failures = <count>
circuit:<service>:last_failure = <timestamp>
"""

# ============================================================================
# SECTION 3: RETRY PATTERN WITH EXPONENTIAL BACKOFF
# ============================================================================

RETRY_PATTERN = """
RETRY PATTERN (Handle Transient Failures):
========================================

RULES:
------
1. Retry ONLY transient failures (network, timeout, 503)
2. NEVER retry permanent failures (404, 400, 401)
3. Use exponential backoff: 1s, 2s, 4s, 8s...
4. Add jitter: random(0.5x, 1.5x) to prevent thundering herd
5. Max 3 retries, then circuit breaker

RETRY DECISION MATRIX:
----------------------
HTTP 429 (Rate Limited): Retry with longer backoff (60s)
HTTP 503 (Unavailable): Retry with exponential backoff
HTTP 504 (Timeout): Retry immediately once
HTTP 404 (Not Found): DON'T RETRY - permanent failure
HTTP 500 (Server Error): Retry with exponential backoff

IMPLEMENTATION:
---------------
def retry_with_backoff(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) * random.uniform(0.5, 1.5)
            time.sleep(wait)
        except PermanentError:
            raise

FOR OUR STACK:
--------------
- Redis operations: 3 retries, 1s backoff
- HTTP fetches: 3 retries, 2s backoff with jitter
- Docker commands: 2 retries, 500ms backoff
- GPU operations: NO retries (fail fast)
"""

# ============================================================================
# SECTION 4: HEALTH ENDPOINT MONITORING
# ============================================================================

HEALTH_MONITORING = """
HEALTH ENDPOINT MONITORING (Know Your System State):
===================================================

EVERY SERVICE MUST EXPOSE:
--------------------------
GET /health -> Returns service health
GET /health/ready -> Returns if ready to serve
GET /health/live -> Returns if process alive

HEALTH CHECK RESPONSE:
----------------------
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "ISO8601",
  "version": "1.0.0",
  "checks": {
    "redis": "ok|fail",
    "gpu": "ok|fail",
    "memory": "ok|fail"
  }
}

IMPLEMENTATION RULES:
--------------------
1. Health checks every 30 seconds
2. Log health status changes
3. Alert on 3 consecutive unhealthy
4. Auto-recover when healthy again

FOR OUR STACK:
--------------
Redis: PING command every 30s
GPU: rocminfo check every 60s  
Ollama: API /api/tags every 30s
Docker: docker ps every 30s
"""

# ============================================================================
# SECTION 5: GRACEFUL DEGRADATION
# ============================================================================

GRACEFUL_DEGRADATION = """
GRACEFUL DEGRADATION (Stay Alive When Parts Fail):
================================================

PRINCIPLE: Partial is better than nothing

TIERED RESPONSE:
----------------
Tier 1: Full functionality (all systems healthy)
Tier 2: Reduced features (GPU unavailable, use CPU)
Tier 3: Basic functionality (Redis unavailable, use file)
Tier 4: Read-only mode (critical failure)
Tier 5: Error state with clear message

EXAMPLES:
---------
GPU Fail -> Use CPU inference (3-10x slower but works)
Redis Fail -> Use file-based state (E:\\AI-Setup\\blackboard_data\\)
Ollama Fail -> Try vLLM -> Try transformers
Web Fetch Fail -> Return cached content + stale indicator

IMPLEMENTATION:
---------------
def get_inference_engine():
    if ollama.is_healthy():
        return ollama
    if vllm.is_healthy():
        return vllm
    if transformers.is_healthy():
        return transformers
    raise ServiceUnavailable("All inference engines failed")

def get_state_store():
    if redis.is_healthy():
        return redis
    return FileStateStore()  # Fallback
"""

# ============================================================================
# SECTION 6: ORDER OF OPERATIONS
# ============================================================================

ORDER_OF_OPERATIONS = """
ORDER OF OPERATIONS (Sequence Matters):
=====================================

STARTUP SEQUENCE:
-----------------
1. Check Docker daemon running
2. Start Redis (blocking, critical)
3. Restore from backup if needed
4. Verify Redis keys loaded
5. Start other services in dependency order:
   - Redis -> Ollama -> vLLM -> WebUI

SHUTDOWN SEQUENCE:
-----------------
1. Save state to Redis
2. Force Redis BGSAVE
3. Wait for Redis save confirmation
4. Stop non-essential services
5. Stop Redis last

CRITICAL OPERATIONS ORDER:
--------------------------
BEFORE ANY DEPLOYMENT:
  1. Backup Redis
  2. Check port availability
  3. Verify resources available
  4. Notify health system

BEFORE RUNNING INFERENCE:
  1. Verify GPU accessible
  2. Verify model files exist
  3. Warm up model (load weights)
  4. Test with simple inference

BEFORE CONFIGURATION CHANGE:
  1. Document current config
  2. Create rollback point
  3. Apply change
  4. Verify change worked
  5. Update documentation
"""

# ============================================================================
# SECTION 7: RACE CONDITIONS PREVENTION
# ============================================================================

RACE_CONDITIONS = """
RACE CONDITIONS (Concurrent Access):
===================================

PROBLEM: Multiple agents accessing same resource simultaneously

SOLUTIONS:
----------
1. DISTRIBUTED LOCKING
   - Redis SETNX for locks
   - Lock key: lock:<resource>
   - Always set expiry!

2. COMPENSATING TRANSACTIONS
   - If step N fails, undo steps 1 to N-1
   - Log compensation actions

3. IDEMPOTENT OPERATIONS
   - Same input always produces same result
   - Use operation IDs to deduplicate

IMPLEMENTATION:
---------------
# Distributed lock with Redis
def acquire_lock(lock_name, ttl=30):
    lock_key = f"lock:{lock_name}"
    if redis.set(lock_key, "1", nx=True, ex=ttl):
        return True
    return False

def release_lock(lock_name):
    redis.delete(f"lock:{lock_name}")

# With compensation
def update_config_with_rollback(new_config):
    backup = get_current_config()
    try:
        apply_config(new_config)
        save_to_redis("config:backup", backup)
    except:
        restore_from_backup(backup)
        raise

FOR OUR STACK:
--------------
- Only one agent modifies port registry at a time
- Use Redis locks for config changes
- All state changes are idempotent
- Backup before any modification
"""

# ============================================================================
# SECTION 8: PORT MANAGEMENT (CRITICAL)
# ============================================================================

PORT_MANAGEMENT = """
PORT MANAGEMENT (No Conflicts):
==============================

RULE 1: Query before allocate
-----------------------------
Before starting ANY service:
  1. Check: GET system:ports
  2. Verify port not in use
  3. Allocate and document

RULE 2: Unique ports per container
---------------------------------
Port conflict = "bind: address already in use"
Resolution:
  - Stop conflicting container, OR
  - Use different port

RULE 3: Register all allocations
-------------------------------
After allocating port:
  HSET system:ports <service>_port <port>

REGISTERED PORTS:
----------------
6379: Redis (wsl-ai-redis) - NEVER CONFLICT
11434: Ollama (ai-ollama)
8000: vLLM (planned)
3000: Open WebUI
5000/5001: Voice

DYNAMIC RANGE: 9000-65535
Use for: temporary services, debugging

PREVENTION:
-----------
Before docker run:
  docker ps | grep <port>
  If result, port is taken

After starting container:
  Verify: docker port <container>
"""

# ============================================================================
# SECTION 9: IO SCHEDULING AND RESOURCE MANAGEMENT
# ============================================================================

IO_SCHEDULING = """
IO SCHEDULING (Don't Overwhelm Resources):
=========================================

PRINCIPLES:
-----------
1. FIFO for sequential operations
2. Priority queue for urgent operations
3. Backpressure when overwhelmed
4. Batch operations when possible

IMPLEMENTATION:
---------------
# Batch Redis operations
def batch_redis_ops(operations):
    pipe = redis.pipeline()
    for op in operations:
        op(pipe)
    return pipe.execute()

# Backpressure with queue
def with_backpressure(work_queue, max_size=100):
    if work_queue.qsize() > max_size:
        raise QueueFull("Backpressure applied")
    return work_queue.enqueue(work)

# Rate limiting
def rate_limit(calls_per_second=10):
    def decorator(func):
        last_call = [0]
        def wrapper(*args):
            elapsed = time.time() - last_call[0]
            if elapsed < 1/calls_per_second:
                time.sleep(1/calls_per_second - elapsed)
            last_call[0] = time.time()
            return func(*args)
        return wrapper
    return decorator

FOR OUR STACK:
--------------
- Redis: Batch multi-key operations
- Web fetches: Max 2 concurrent
- File I/O: Batch writes, async reads
- GPU: One inference at a time (queue requests)
"""

# ============================================================================
# SECTION 10: TIMEOUT HANDLING
# ============================================================================

TIMEOUT_HANDLING = """
TIMEOUT HANDLING (Don't Wait Forever):
====================================

RULES:
------
1. ALL remote calls MUST have timeout
2. Timeout must be reasonable for operation
3. On timeout: retry once, then circuit breaker

TIMEOUT VALUES:
--------------
Redis operations: 5 seconds
Ollama inference: 120 seconds
Web fetch: 15 seconds
Docker commands: 30 seconds
Health checks: 10 seconds
GPU operations: 60 seconds

IMPLEMENTATION:
---------------
def with_timeout(operation, seconds=30):
    try:
        return asyncio.wait_for(operation(), timeout=seconds)
    except asyncio.TimeoutError:
        log_timeout(operation)
        raise

FOR OUR STACK:
--------------
Redis: timeout=5, retry=1
Ollama: timeout=120, retry=0 (long-running)
WebFetch: timeout=15, retry=3 with backoff
"""

# ============================================================================
# SECTION 11: LOGGING AND OBSERVABILITY
# ============================================================================

LOGGING = """
LOGGING AND OBSERVABILITY (See Everything):
=========================================

LOG LEVELS:
-----------
ERROR: Operation failed, needs attention
WARN: Degraded but working
INFO: Normal operations
DEBUG: Detailed tracing (disabled in prod)

REQUIRED LOG FIELDS:
-------------------
- timestamp (ISO8601)
- level (ERROR|WARN|INFO|DEBUG)
- component (who is logging)
- message (what happened)
- correlation_id (for tracing)

EXAMPLE:
--------
{
  "timestamp": "2026-04-14T12:00:00Z",
  "level": "ERROR",
  "component": "inference",
  "message": "Ollama GPU fallback to CPU",
  "details": {"latency_ms": 5000, "gpu_error": "timeout"},
  "correlation_id": "req-123"
}

FOR OUR STACK:
--------------
All logs to: E:\AI-Setup\blackboard_data\logs\
Format: JSONL (one JSON per line)
Rotation: Daily, keep 7 days
Alert on: ERROR rate > 1/minute
"""

# ============================================================================
# SECTION 12: COMPENSATING TRANSACTIONS (ROLLBACK)
# ============================================================================

COMPENSATING_TRANSACTIONS = """
COMPENSATING TRANSACTIONS (Undo on Failure):
==========================================

PATTERN: Saga (long-running distributed transactions)

IMPLEMENTATION:
---------------
def saga_step(step_name, forward, backward):
    try:
        result = forward()
        log(f"Saga step {step_name} completed")
        return result
    except Exception as e:
        log(f"Saga step {step_name} failed: {e}")
        log(f"Running compensation for {step_name}")
        backward()
        raise

EXAMPLE:
--------
def deploy_service_saga(service_config):
    # Step 1: Pull image
    saga_step(
        "pull_image",
        forward=lambda: docker.pull(config.image),
        backward=lambda: docker.rmi(config.image)
    )
    
    # Step 2: Start container
    saga_step(
        "start_container",
        forward=lambda: docker.run(config),
        backward=lambda: docker.stop(config.name)
    )
    
    # Step 3: Health check
    saga_step(
        "health_check",
        forward=lambda: verify_health(config.name),
        backward=lambda: docker.stop(config.name)
    )

FOR OUR STACK:
--------------
- Config changes: backup -> apply -> verify -> (rollback on fail)
- Deployment: pull -> start -> health -> (rollback on fail)
- Inference: load_model -> warmup -> serve -> (unload on fail)
"""

# ============================================================================
# SECTION 13: SERVICE DISCOVERY
# ============================================================================

SERVICE_DISCOVERY = """
SERVICE DISCOVERY (Find Services Dynamically):
============================================

NEVER HARDCODE:
--------------
- IP addresses
- Port numbers
- Hostnames

ALWAYS QUERY:
-------------
Redis: HGET system:ports ollama_port
DNS/Service Registry when available

IMPLEMENTATION:
---------------
def get_service_url(service_name):
    port = redis.hget("system:ports", f"{service_name}_port")
    host = redis.hget("system:hosts", service_name) or "localhost"
    protocol = redis.hget("system:protocols", service_name) or "http"
    return f"{protocol}://{host}:{port}"

# Cache with TTL
_cached_urls = {}
def get_service_url_cached(service_name, ttl=60):
    if service_name not in _cached_urls:
        _cached_urls[service_name] = get_service_url(service_name)
        # Refresh after TTL
    return _cached_urls[service_name]

FOR OUR STACK:
-------------
Redis key: system:ports
Format: HGETALL returns {ollama_port: 11434, ...}
Update on: container start/stop
"""

# ============================================================================
# SECTION 14: BULKHEAD (ISOLATION)
# ============================================================================

BULKHEAD = """
BULKHEAD PATTERN (Isolate Failures):
====================================

PRINCIPLE: If one pool drains, others stay alive

IMPLEMENTATION:
---------------
# Separate connection pools
redis_pool = redis.ConnectionPool(max_connections=10)
cache_pool = redis.ConnectionPool(max_connections=5)
state_pool = redis.ConnectionPool(max_connections=3)

# Separate thread pools
inference_pool = ThreadPoolExecutor(max_workers=2)
background_pool = ThreadPoolExecutor(max_workers=1)

# Separate queues
gpu_queue = Queue(maxsize=5)  # GPU inference
cpu_queue = Queue(maxsize=10)   # CPU tasks
io_queue = Queue(maxsize=100)  # File I/O

FOR OUR STACK:
--------------
- GPU inference: 1 concurrent (expensive)
- CPU inference: 2 concurrent
- Redis: 10 connections max
- File writes: 1 at a time (sequential)
"""

# ============================================================================
# SECTION 15: QUICK REFERENCE
# ============================================================================

QUICK_REFERENCE = """
QUICK REFERENCE FOR AGENTS:
==========================

BEFORE ANY ACTION:
------------------
1. Is it safe? (backup Redis)
2. Is it available? (check health)
3. Is there conflict? (check ports)
4. Can it be undone? (compensation ready)

WHEN FAILURE OCCURS:
--------------------
1. Log the failure with details
2. Retry with backoff (if transient)
3. Circuit break (if persistent)
4. Graceful degrade (if possible)
5. Escalate (if cannot resolve)

HEALTH CHECK ORDER:
-------------------
1. Redis (critical)
2. GPU (inference)
3. Ollama (inference)
4. Services (non-critical)

ERROR HANDLING MATRIX:
----------------------
Network timeout -> Retry 3x with backoff
Port conflict -> Find alternative port
Container crash -> Restart with backoff
GPU unavailable -> Fall back to CPU
Redis unavailable -> Use file fallback

CONTACT POINTS:
---------------
Ports: HGET system:ports (Redis)
Logs: E:\AI-Setup\blackboard_data\logs\
Health: E:\AI-Setup\redis_manager.py --status
Config: Redis hash system:config
Deploy: E:\AI-Setup\deployment_framework.py
"""
