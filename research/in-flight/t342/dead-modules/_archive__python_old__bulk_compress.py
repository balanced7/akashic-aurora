#!/usr/bin/env python3
"""
Bulk Session Compressor - Process Past Sessions
=============================================
Uses Gemma 2B to:
1. Search through manual session logs of the past
2. Compress them into searchable summaries
3. Store in session_text_idx for future retrieval
4. Delete raw logs (space savings)
"""

import sys
import time
import logging
import requests
from redis import Redis

# Config
WSL_HOST = '127.0.0.1'
WSL_PORT = 6379
WIN_HOST = '127.0.0.1'
WIN_PORT = 6379
GEMMA_URL = 'http://localhost:5000'
SUMMARY_PREFIX = 'session:summary:'
LOG_PATTERN = 'session:*:log'
ACTIONS_PATTERN = 'session:*:actions'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class BulkCompressor:
    def __init__(self):
        self.wsl_redis = Redis(host=WSL_HOST, port=WSL_PORT, decode_responses=True)
        self.win_redis = Redis(host=WIN_HOST, port=WIN_PORT, decode_responses=True)
        self.gemma_available = self._check_gemma()

    def _check_gemma(self):
        try:
            resp = requests.get(f"{GEMMA_URL}/health", timeout=5)
            if resp.status_code == 200:
                logger.info("Gemma 2B is available")
                return True
        except Exception as e:
            logger.warning(f"Gemma not available: {e}")
        return False

    def summarize_with_gemma(self, log_text, session_id):
        if not self.gemma_available:
            return log_text[:200]  # Fallback

        try:
            prompt = f"""Summarize this session log in 2-3 sentences. Focus on:
- Key decisions made
- Problems solved
- Important learnings
- Outcomes achieved

Session ID: {session_id}
Log:
{log_text[:2000]}

Concise summary:"""

            resp = requests.post(f"{GEMMA_URL}/generate",
                               json={"prompt": prompt, "max_tokens": 200},
                               timeout=30)
            if resp.status_code == 200:
                summary = resp.json().get("response", "")[:300]
                logger.info(f"Gemma summarized {session_id}")
                return summary
        except Exception as e:
            logger.error(f"Gemma failed for {session_id}: {e}")
        return log_text[:200]

    def compress_session(self, session_id, source='wsl'):
        """Compress a single session log"""
        log_key = f"session:{session_id}:log"
        actions_key = f"session:{session_id}:actions"

        # Get log data from appropriate source
        if source == 'wsl':
            log_data = self.wsl_redis.get(log_key)
            actions_data = self.wsl_redis.get(actions_key)
        else:
            log_data = self.win_redis.get(log_key)
            actions_data = self.win_redis.get(actions_key)

        if not log_data:
            logger.warning(f"No log data for {session_id}")
            return False

        # Combine log and actions if available
        full_text = log_data
        if actions_data:
            full_text += f"\n\nActions: {actions_data}"

        # Summarize
        summary = self.summarize_with_gemma(full_text, session_id)
        timestamp = int(time.time())

        # Store summary in both Redis instances
        key = f"{SUMMARY_PREFIX}{session_id}"
        mapping = {
            "session_id": session_id,
            "timestamp": str(timestamp),
            "summary": summary
        }

        for redis_inst, name in [(self.wsl_redis, 'WSL'), (self.win_redis, 'Windows')]:
            try:
                redis_inst.hset(key, mapping=mapping)
                logger.info(f"Stored summary in {name}: {key}")
            except Exception as e:
                logger.error(f"Failed to store in {name}: {e}")

        # Keep raw logs as fallback (user handles deletion)
        logger.info(f"Raw logs preserved for {session_id} ({len(full_text)} bytes) - fallback available")

        return True

    def find_and_compress_all(self):
        """Find all past session logs and compress them"""
        total = 0
        compressed = 0

        # Search in WSL Redis
        logger.info("Searching for past sessions in WSL Redis...")
        wsl_keys = self.wsl_redis.keys(LOG_PATTERN)
        total += len(wsl_keys)
        logger.info(f"Found {len(wsl_keys)} log keys in WSL")

        for key in wsl_keys:
            if 'summary' in key:
                continue
            session_id = key.replace('session:', '').replace(':log', '')
            logger.info(f"Compressing WSL session: {session_id}")
            if self.compress_session(session_id, source='wsl'):
                compressed += 1
                time.sleep(1)  # Rate limiting for Gemma

        # Search in Windows Redis
        logger.info("Searching for past sessions in Windows Redis...")
        win_keys = self.win_redis.keys(LOG_PATTERN)
        total += len(win_keys)
        logger.info(f"Found {len(win_keys)} log keys in Windows")

        for key in win_keys:
            if 'summary' in key:
                continue
            session_id = key.replace('session:', '').replace(':log', '')
            logger.info(f"Compressing Windows session: {session_id}")
            if self.compress_session(session_id, source='windows'):
                compressed += 1
                time.sleep(1)

        # Also check for action keys without logs
        wsl_actions = self.wsl_redis.keys(ACTIONS_PATTERN)
        for key in wsl_actions:
            if 'summary' in key:
                continue
            session_id = key.replace('session:', '').replace(':actions', '')
            summary_key = f"{SUMMARY_PREFIX}{session_id}"
            if not self.wsl_redis.exists(summary_key):
                logger.info(f"Compressing WSL actions: {session_id}")
                if self.compress_session(session_id, source='wsl'):
                    compressed += 1
                    time.sleep(1)

        logger.info("=== Compression Complete ===")
        logger.info(f"Total sessions found: {total}")
        logger.info(f"Sessions compressed: {compressed}")
        logger.info(f"Space saved: ~{compressed * 10}KB")

    def search_past_sessions(self, query, limit=5):
        """Search through compressed sessions"""
        logger.info(f"Searching for: {query}")
        results = []

        for redis_inst, name in [(self.wsl_redis, 'WSL'), (self.win_redis, 'Windows')]:
            try:
                res = redis_inst.execute_command(
                    'FT.SEARCH', 'session_text_idx', f"@summary:{query}",
                    'LIMIT', '0', str(limit), 'RETURN', '3',
                    'session_id', 'summary', 'timestamp'
                )
                # Parse results
                if res and len(res) > 1:
                    for i in range(1, len(res), 2):
                        if i + 1 < len(res):
                            doc = res[i + 1]
                            results.append(dict(zip(doc[::2], doc[1::2])))
            except Exception as e:
                logger.error(f"Search failed in {name}: {e}")

        return results[:limit]


if __name__ == '__main__':
    compressor = BulkCompressor()

    if '--compress-all' in sys.argv:
        logger.info("Starting bulk compression of past sessions...")
        compressor.find_and_compress_all()

    elif '--search' in sys.argv and len(sys.argv) > 2:
        query = sys.argv[2]
        results = compressor.search_past_sessions(query, limit=5)
        print(f"\nSearch results for '{query}':")
        for r in results:
            print(f"  - {r.get('session_id', 'N/A')}: {r.get('summary', 'N/A')[:100]}")

    else:
        print("Usage:")
        print("  --compress-all    : Find and compress ALL past session logs")
        print("  --search <query>  : Search compressed sessions")
        print("\nExample:")
        print("  python bulk_compress.py --compress-all")
        print("  python bulk_compress.py --search 'Redis setup'")
