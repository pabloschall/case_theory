import json
from typing import Protocol

from redis.asyncio import Redis


class JSONCache(Protocol):
    async def get(self, key: str) -> dict[str, object] | None: ...

    async def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None: ...


class RedisJSONCache:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> dict[str, object] | None:
        try:
            value = await self.redis.get(key)
        except Exception:
            return None
        if not value:
            return None
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None

    async def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        try:
            await self.redis.set(key, json.dumps(value, separators=(",", ":")), ex=ttl_seconds)
        except Exception:
            return
