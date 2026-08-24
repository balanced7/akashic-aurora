#!/usr/bin/env python3
"""
Real-time Session Log Summarizer
==================================
Watches Redis for new session logs, summarizes them via Gemma 2B,
generates vector embeddings, and stores in both WSL and Windows Redis.

Setup:
    WSL Redis (port 6379): Has RediSearch module for vector search
    Windows Redis (Docker, port 6379): Has RediSearch module for vector search
    Gemma 2B API: http://localhost:5000
"""

import sys
import time
import logging
import requests
import numpy as np
from datetime import datetime
from redis import Redis

# Config
WSL_HOST = '127.0.0.1'
WSL_PORT = 6379
WIN_HOST = '127.0.0.1'
WIN_PORT = 6379
GEMMA_URL = 'http://localhost:5000'
EMBED_MODEL = 'all-MiniLM-L6-v2'
VEC_INDEX = 'session_vec_idx'
LOG_PATTERN = 'session:*:log'
SUMMARY_PREFIX = 'session:summary:'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class SessionSummarizer:
    def __init__(self):
        self.wsl_redis = Redis(host=WSL_HOST, port=WSL_PORT, decode_responses=True)
        self.win_redis = Redis(host=WIN_HOST, port=WIN_PORT, decode_responses=True)
        self.embedder = None
        self._init_embedder()
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create vector indexes if they don't exist"""
        for redis_inst, name in [(self.wsl_redis, 'WSL'), (self.win_redis, 'Windows')]:
            try:
                redis_inst.execute_command('FT.INFO', VEC_INDEX)
                logger.info(f"{name} Redis: vector index exists")
            except Exception:
                try:
                    redis_inst.execute_command(
                        'FT.CREATE', VEC_INDEX, 'ON', 'HASH', 'PREFIX', '1', f'{SUMMARY_PREFIX}',
                        'SCHEMA', 'session_id', 'TAG', 'timestamp', 'NUMERIC', 'summary', 'TEXT',
                        'embedding', 'VECTOR', 'HNSW', '6', 'TYPE', 'FLOAT32', 'DIM', '384', 'DISTANCE_METRIC', 'COSINE'
                    )
                    logger.info(f"{name} Redis: created vector index")
                except Exception as e:
                    logger.error(f"{name} Redis index creation failed: {e}")

    def _init_embedder(self):
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading {EMBED_MODEL}...")
            self.embedder = SentenceTransformer(EMBED_MODEL)
            logger.info("Embedder ready")
        except Exception as e:
            logger.error(f"Embedder init failed: {e}")

    def summarize_with_gemma(self, log_text):
        try:
            prompt = f"Summarize in 3 bullet points:\n{log_text[:1500]}\n\nSummary:"
            resp = requests.post(f"{GEMMA_URL}/generate", json={"prompt": prompt, "max_tokens": 200}, timeout=20)
            if resp.status_code == 200:
                return resp.json().get("response", "")[:400]
        except Exception as e:
            logger.warning(f"Gemma failed: {e}")
        return log_text[:200]

    def get_embedding(self, text):
        if not self.embedder:
            return None
        try:
            vec = self.embedder.encode(text, normalize_embeddings=True)
            return vec.astype(np.float32)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    def store_summary(self, session_id, summary, embedding):
        """Store in both Redis instances"""
        key = f"{SUMMARY_PREFIX}{session_id}"
        mapping = {"session_id": session_id, "timestamp": str(int(time.time())), "summary": summary}

        for redis_inst, name in [(self.wsl_redis, 'WSL'), (self.win_redis, 'Windows')]:
            try:
                mapping_copy = dict(mapping)
                if embedding is not None:
                    mapping_copy["embedding"] = embedding.tobytes()
                redis_inst.hset(key, mapping=mapping_copy)
                logger.info(f"Stored in {name}: {key}")
            except Exception as e:
                logger.error(f"Store failed in {name}: {e}")

    def process_session(self, session_id):
        log_key = f"session:{session_id}:log"
        log_data = self.wsl_redis.get(log_key) or self.win_redis.get(log_key)
        
        if not log_data:
            logger.warning(f"No log for {session_id}")
            return False

        summary = self.summarize_with_gemma(str(log_data))
        embedding = self.get_embedding(summary) if self.embedder else None
        self.store_summary(session_id, summary, embedding)
        return True

    def watch_sessions(self):
        """Watch for new sessions via Pub/Sub"""
        try:
            self.wsl_redis.config_set('notify-keyspace-events', 'K$g')
        except Exception as e:
            logger.warning(f"Keyspace config failed: {e}")

        pubsub = self.wsl_redis.pubsub()
        pubsub.psubscribe('__keyevent@0__:set')
        
        logger.info("Watching for new sessions...")
        for msg in pubsub.listen():
            if msg['type'] != 'pmessage':
                continue
            key = msg['data']
            if isinstance(key, str) and ':log' in key and 'session:' in key:
                session_id = key.replace('session:', '').replace(':log', '')
                logger.info(f"New session: {session_id}")
                time.sleep(1)
                self.process_session(session_id)


if __name__ == '__main__':
    s = SessionSummarizer()
    if '--test' in sys.argv:
        # Create a test session
        test_log = "Started bootstrap, checked Redis, installed packages, created vector indexes."
        s.wsl_redis.set('session:test_001:log', test_log)
        s.process_session('test_001')
    elif '--daemon' in sys.argv:
        s.watch_sessions()
    else:
        print("Usage: session_summarizer.py [--test|--daemon]")
