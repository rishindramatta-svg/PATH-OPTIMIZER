from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from uuid import uuid4

logger = logging.getLogger("png9.shared")
INSTANCE_ID = str(uuid4())
redis_client = None
_redis_warned = False
_fallback_hits: dict[str, deque[float]] = defaultdict(deque)
_fallback_cache: dict[str, tuple[float, str]] = {}
_lock = threading.Lock()


def get_redis():
    global redis_client, _redis_warned
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    if redis_client is None:
        try:
            import redis

            redis_client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            redis_client.ping()
            logger.info(json.dumps({"event": "redis_connected", "url": url.split("@")[-1]}))
        except Exception as exc:
            redis_client = False
            if not _redis_warned:
                logger.warning(json.dumps({"event": "redis_unavailable_fallback", "reason": str(exc)}))
                _redis_warned = True
    if redis_client is False:
        return None
    try:
        redis_client.ping()
        return redis_client
    except Exception as exc:
        redis_client = False
        if not _redis_warned:
            logger.warning(json.dumps({"event": "redis_unavailable_fallback", "reason": str(exc)}))
            _redis_warned = True
        return None


def cache_get(key: str):
    client = get_redis()
    if not client:
        with _lock:
            entry = _fallback_cache.get(key)
            if not entry:
                return None
            if entry[0] <= time.monotonic():
                _fallback_cache.pop(key, None)
                return None
            return json.loads(entry[1])
    try:
        value = client.get(f"png9:cache:{key}")
        return json.loads(value) if value else None
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_cache_read_fallback", "reason": str(exc)}))
        return None


def cache_set(key: str, value, ttl: int = 120):
    client = get_redis()
    if not client:
        with _lock:
            _fallback_cache[key] = (
                time.monotonic() + ttl,
                json.dumps(value, separators=(",", ":")),
            )
        return
    try:
        client.setex(f"png9:cache:{key}", ttl, json.dumps(value, separators=(",", ":")))
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_cache_write_fallback", "reason": str(exc)}))


def cache_delete(*keys: str):
    client = get_redis()
    if not client:
        with _lock:
            for key in keys:
                _fallback_cache.pop(key, None)
        return
    try:
        if keys:
            client.delete(*(f"png9:cache:{key}" for key in keys))
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_cache_invalidation_fallback", "reason": str(exc)}))


def shared_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    client = get_redis()
    if client:
        try:
            now = time.time()
            redis_key = f"png9:rate:{key}"
            pipe = client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            pipe.zadd(
                redis_key,
                {f"{now}:{threading.get_ident()}:{time.perf_counter_ns()}": now},
            )
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds + 1)
            return pipe.execute()[2] <= limit
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_rate_limit_fallback", "reason": str(exc)}))
    return None


def publish_shared_event(user_id: int, event: str, data: dict):
    client = get_redis()
    if not client:
        return
    try:
        client.publish(
            "png9:events",
            json.dumps(
                {
                    "userId": user_id,
                    "event": event,
                    "data": data,
                    "origin": INSTANCE_ID,
                },
                separators=(",", ":"),
            ),
        )
    except Exception as exc:
        logger.warning(json.dumps({"event": "redis_event_fallback", "reason": str(exc)}))


def start_pubsub(dispatch):
    client = get_redis()
    if not client:
        return

    def listen():
        while True:
            try:
                pubsub = client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe("png9:events")
                for message in pubsub.listen():
                    if message and message.get("type") == "message":
                        try:
                            dispatch(json.loads(message["data"]))
                        except (ValueError, KeyError, TypeError) as exc:
                            logger.warning(json.dumps({"event": "redis_event_invalid", "reason": str(exc)}))
            except Exception as exc:
                logger.warning(json.dumps({"event": "redis_pubsub_fallback", "reason": str(exc)}))
                time.sleep(2)

    threading.Thread(target=listen, daemon=True, name="png9-redis-events").start()
