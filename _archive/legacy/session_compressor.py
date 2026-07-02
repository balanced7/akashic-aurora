#!/usr/bin/env python3
"""
Session Context Compressor
==========================
Compresses session logs into searchable summaries on WSL Redis + Docker Stack.

Signals:
1) Redis STRING ``session:<id>:log`` (legacy, keyevent set)
2) Redis LIST ``session:<id>:log`` (entries from session_logger RPUSH — keyevent rpush)
3) Redis Stream ``session:events`` (canonical MCP envelopes — XREAD consumer + debounced flush)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time

import requests
from redis import Redis
from redis.exceptions import RedisError

from config import SESSION_EVENTS_STREAM
from session_canonical import envelope_to_plaintext

# Config
WSL_HOST = "127.0.0.1"
WSL_PORT = 6380
WIN_HOST = "127.0.0.1"
WIN_PORT = 16379
GEMMA_URL = "http://localhost:5000"
SUMMARY_PREFIX = "session:summary:"

DEBOUNCE_SEC = float(os.environ.get("SESSION_SUMMARY_DEBOUNCE", "18"))
STREAM_XREAD_MS = int(os.environ.get("SESSION_STREAM_BLOCK_MS", "4000"))
STREAM_START_ID = os.environ.get("SESSION_EVENTS_STREAM_FROM", "$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SessionCompressor:
    def __init__(self):
        self.wsl_redis = Redis(host=WSL_HOST, port=WSL_PORT, decode_responses=True)
        self.win_redis = Redis(host=WIN_HOST, port=WIN_PORT, decode_responses=True)
        self._stream_stop = threading.Event()
        self._ensure_text_index()

    def _ensure_text_index(self):
        for redis_inst, name in [(self.wsl_redis, "WSL"), (self.win_redis, "Windows")]:
            try:
                redis_inst.execute_command("FT.INFO", "session_text_idx")
                logger.info(f"{name}: text index exists")
            except Exception:
                try:
                    redis_inst.execute_command(
                        "FT.CREATE",
                        "session_text_idx",
                        "ON",
                        "HASH",
                        "PREFIX",
                        "1",
                        SUMMARY_PREFIX,
                        "SCHEMA",
                        "session_id",
                        "TAG",
                        "timestamp",
                        "NUMERIC",
                        "summary",
                        "TEXT",
                    )
                    logger.info(f"{name}: created text index")
                except Exception as e:
                    logger.error(f"{name}: index creation failed: {e}")

    def summarize_with_gemma(self, log_text):
        try:
            prompt = (
                "Summarize this session log in 2-3 sentences. "
                "Focus on decisions, outcomes, and key learnings.\n\n"
                + log_text[:15000]
            )
            resp = requests.post(
                f"{GEMMA_URL}/api/chat",
                json={"prompt": prompt, "model": "gemma2:2b"},
                timeout=90,
            )
            if resp.status_code == 200:
                return str(resp.json().get("response", ""))[:300]
        except Exception as e:
            logger.warning("Gemma failed: %s", e)
        return log_text[:200]

    def _gather_raw_log(self, session_id: str) -> str:
        """Support STRING blob (legacy compressor) OR LIST JSON lines from session_logger."""
        log_key = f"session:{session_id}:log"
        kt = ""
        try:
            kt = self.wsl_redis.type(log_key) or ""
            if kt == "string":
                blob = self.wsl_redis.get(log_key)
                return str(blob or "")
            if kt == "list":
                lines = self.wsl_redis.lrange(log_key, 0, -1) or []
                return "\n".join(str(l) for l in lines)

            kb = self.win_redis.type(log_key) if log_key else None
            kb_s = kb or ""
            if kb_s == "string":
                return str(self.win_redis.get(log_key) or "")
            if kb_s == "list":
                lines = self.win_redis.lrange(log_key, 0, -1) or []
                return "\n".join(str(l) for l in lines)
        except Exception as e:
            logger.warning("gather log %s (type=%s): %s", log_key, kt, e)
        return ""

    def compress_body_to_summaries(self, session_id: str, log_text: str) -> bool:
        raw = log_text.strip()
        if not raw:
            logger.warning("No log payload for session %s", session_id)
            return False

        summary = self.summarize_with_gemma(raw)
        ts = int(time.time())

        key = f"{SUMMARY_PREFIX}{session_id}"
        mapping = {"session_id": session_id, "timestamp": str(ts), "summary": summary}

        for redis_inst, name in [(self.wsl_redis, "WSL"), (self.win_redis, "Windows")]:
            try:
                redis_inst.hset(key, mapping=mapping)
                logger.info("Stored summary in %s: %s", name, key)
            except Exception as e:
                logger.error("Failed to store in %s: %s", name, e)

        logger.debug("Compressed session %s (%d chars input)", session_id, len(raw))
        return True

    def compress_session(self, session_id):
        payload = self._gather_raw_log(session_id)
        return self.compress_body_to_summaries(session_id, payload)

    def compress_session_from_plaintext(self, session_id: str, text: str) -> bool:
        """Used by MCP / manual flush when aggregates are assembled off-Redis."""
        return self.compress_body_to_summaries(session_id, text)

    def search_context(self, query, limit=3):
        results = []
        for redis_inst, name in [(self.wsl_redis, "WSL"), (self.win_redis, "Windows")]:
            try:
                res = redis_inst.execute_command(
                    "FT.SEARCH",
                    "session_text_idx",
                    f"@summary:{query}",
                    "LIMIT",
                    "0",
                    str(limit),
                    "RETURN",
                    "3",
                    "session_id",
                    "summary",
                    "timestamp",
                )
                if res and len(res) > 1:
                    for i in range(1, len(res), 2):
                        if i + 1 < len(res):
                            doc = res[i + 1]
                            results.append(dict(zip(doc[::2], doc[1::2])))
            except Exception as e:
                logger.error("Search failed in %s: %s", name, e)
        return results[:limit]

    def _flush_stream_buffer(self, session_id: str, buf: str) -> None:
        if not buf.strip():
            return
        combined = self._gather_raw_log(session_id)
        if combined.strip():
            merged = buf.rstrip() + "\n\n--- list/string log ---\n" + combined
        else:
            merged = buf
        self.compress_body_to_summaries(session_id, merged)

    def _stream_consumer_loop(self):
        last_id = STREAM_START_ID
        buf = {}
        deadline = {}
        while not self._stream_stop.is_set():
            now = time.time()
            for sid, dl in list(deadline.items()):
                if dl <= now and buf.get(sid, "").strip():
                    try:
                        self._flush_stream_buffer(sid, buf[sid])
                    except Exception as e:
                        logger.error("Stream flush failed %s: %s", sid, e)
                    buf.pop(sid, None)
                    deadline.pop(sid, None)

            try:
                out = self.wsl_redis.xread(
                    {SESSION_EVENTS_STREAM: last_id}, count=80, block=STREAM_XREAD_MS
                )
            except RedisError as e:
                logger.warning("XREAD stall: %s", e)
                time.sleep(1)
                continue

            if not out:
                continue

            for _name, msgs in out:
                for mid, fields in msgs:
                    last_id = mid
                    sid = str(fields.get("session_id") or "").strip()
                    payload = fields.get("payload") or "{}"
                    try:
                        env = json.loads(payload)
                    except json.JSONDecodeError:
                        env = {}
                    if not sid and env.get("session_id"):
                        sid = str(env["session_id"]).strip()
                    if not sid:
                        logger.warning("Stream entry %s missing session_id; skip", mid)
                        continue
                    ev = str(fields.get("event_type") or env.get("event_type") or "").lower()
                    txt = envelope_to_plaintext(env) if env else ""

                    immediate = ev in ("close", "summary_request", "flush_summary")
                    buf[sid] = (buf.get(sid, "").rstrip() + "\n" + txt).strip()
                    deadline[sid] = now if immediate else now + DEBOUNCE_SEC

                    if immediate and buf[sid]:
                        try:
                            self._flush_stream_buffer(sid, buf[sid])
                        except Exception as e:
                            logger.error("Immediate flush %s: %s", sid, e)
                        buf.pop(sid, None)
                        deadline.pop(sid, None)

    def watch_and_compress(self):
        try:
            self.wsl_redis.config_set("notify-keyspace-events", "KE$l")
        except Exception as e:
            logger.warning("Keyspace config failed: %s", e)

        t = threading.Thread(target=self._stream_consumer_loop, daemon=True)
        t.start()
        logger.info(
            "Stream consumer on %s (debounce %.1fs, start_id=%s)",
            SESSION_EVENTS_STREAM,
            DEBOUNCE_SEC,
            STREAM_START_ID,
        )

        pubsub = self.wsl_redis.pubsub()
        pubsub.psubscribe("__keyevent@0__:set", "__keyevent@0__:rpush")

        logger.info("Watching Redis keyevents + stream ingestion...")
        for msg in pubsub.listen():
            if self._stream_stop.is_set():
                break
            if msg["type"] != "pmessage":
                continue
            channel = ""
            try:
                channel = msg.get("channel", "")
                channel = channel.decode() if isinstance(channel, bytes) else str(channel)
            except Exception:
                channel = ""

            raw_key = msg.get("data")
            key = (
                raw_key.decode()
                if isinstance(raw_key, (bytes, bytearray))
                else str(raw_key or "")
            )

            trigger = ":set" in channel or ":rpush" in channel
            if not trigger:
                continue
            if ":log" in key and key.startswith("session:"):
                strip = key[len("session:") :]
                session_id = strip[: -len(":log")] if strip.endswith(":log") else strip.split(":log")[0]
                logger.info("Log activity: %s (session %s)", key, session_id)
                time.sleep(1)
                try:
                    self.compress_session(session_id)
                except Exception as e:
                    logger.error("compress_session %s: %s", session_id, e)


if __name__ == "__main__":
    c = SessionCompressor()
    if "--test" in sys.argv:
        test_log = (
            "Started Redis HA, installed redis-stack, created text indexes. "
            "Session log compression working."
        )
        c.wsl_redis.set("session:test_001:log", test_log)
        c.compress_session("test_001")
        print("\nSearch test:")
        results = c.search_context("Redis HA")
        for r in results:
            print(f"  - {r.get('session_id')}: {r.get('summary')}")
    elif "--daemon" in sys.argv:
        c.watch_and_compress()
    else:
        print("Usage: session_compressor.py [--test|--daemon]")
