"""
Cache Service
============

Service for managing Redis-based caching for Yahoo Finance data.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 3
    redis_password: Optional[str] = None

    # Cache TTLs (in seconds)
    # 200s = rate-limit-optimal: 9 symbols × 18 refreshes/hr = 162 quote req/hr
    # + 9 trend req/hr = 171/hr total, within 180/hr limit with ~5% headroom
    global_context_ttl: int = 200
    fundamentals_ttl: int = 86400  # 1 day
    trends_ttl: int = 3600         # 1 hour — trends don't shift fast

    max_cache_size: int = 10000
    enable_compression: bool = False

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create configuration from environment variables"""
        return cls(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "3")),
            redis_password=os.getenv("REDIS_PASSWORD") or None,
            global_context_ttl=int(os.getenv("CACHE_TTL_GLOBAL_CONTEXT", "200")),
            fundamentals_ttl=int(os.getenv("CACHE_TTL_FUNDAMENTALS", "86400")),
            trends_ttl=int(os.getenv("CACHE_TTL_TRENDS", "3600")),
            max_cache_size=int(os.getenv("MAX_CACHE_SIZE", "10000")),
            enable_compression=os.getenv("ENABLE_COMPRESSION", "false").lower() == "true",
        )


class CacheService:
    """Cache service for Yahoo Finance data"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self._initialized = False
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        self.delete_count = 0

    async def initialize(self) -> None:
        """Initialize the cache service. Non-fatal if Redis is unavailable."""
        try:
            logger.info("🔧 Initializing Cache Service...")
            redis_url = f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"
            if self.config.redis_password:
                redis_url = f"redis://:{self.config.redis_password}@{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"
            self.redis_client = aioredis.from_url(redis_url)
            await self.redis_client.ping()
            self._initialized = True
            logger.info("✅ Cache Service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Cache Service unavailable (running without cache): {e}")
            self._initialized = False

    def _get_cache_key(self, data_type: str, identifier: str) -> str:
        return f"yahoo:{data_type}:{identifier}"

    def _get_stale_key(self, data_type: str, identifier: str) -> str:
        return f"yahoo:stale:{data_type}:{identifier}"

    def _get_ttl(self, data_type: str) -> int:
        ttl_map = {
            "quote": self.config.global_context_ttl,
            "global_context": self.config.global_context_ttl,
            "fundamental": self.config.fundamentals_ttl,
            "fundamentals": self.config.fundamentals_ttl,
            "trend": self.config.trends_ttl,
        }
        return ttl_map.get(data_type, self.config.global_context_ttl)

    async def get(self, data_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        try:
            if not self._initialized:
                return None
            cache_key = self._get_cache_key(data_type, identifier)
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                self.hit_count += 1
                logger.debug(f"✅ Cache hit for {cache_key}")
                return json.loads(cached_data)
            self.miss_count += 1
            logger.debug(f"❌ Cache miss for {cache_key}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting from cache: {e}")
            return None

    async def set(self, data_type: str, identifier: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set data in cache"""
        try:
            if not self._initialized:
                return False
            cache_key = self._get_cache_key(data_type, identifier)
            cache_ttl = ttl or self._get_ttl(data_type)
            data_with_timestamp = {**data, "_cached_at": datetime.now().isoformat(), "_cache_ttl": cache_ttl}
            await self.redis_client.setex(cache_key, cache_ttl, json.dumps(data_with_timestamp))
            self.set_count += 1
            logger.debug(f"💾 Cached {cache_key} with TTL {cache_ttl}s")
            return True
        except Exception as e:
            logger.error(f"❌ Error setting cache: {e}")
            return False

    async def get_stale(self, data_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Get stale fallback data (long-lived copy, served when live fetch fails)."""
        try:
            if not self._initialized:
                return None
            stale_key = self._get_stale_key(data_type, identifier)
            cached_data = await self.redis_client.get(stale_key)
            if cached_data:
                logger.debug(f"⚠️ Stale cache hit for {stale_key}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"❌ Error getting stale cache: {e}")
            return None

    async def set_stale(self, data_type: str, identifier: str, data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Store a long-lived stale copy (default 2h). Updated whenever fresh data is fetched."""
        try:
            if not self._initialized:
                return False
            stale_key = self._get_stale_key(data_type, identifier)
            await self.redis_client.setex(stale_key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"❌ Error setting stale cache: {e}")
            return False

    async def delete(self, data_type: str, identifier: str) -> bool:
        """Delete data from cache"""
        try:
            if not self._initialized:
                return False
            cache_key = self._get_cache_key(data_type, identifier)
            result = await self.redis_client.delete(cache_key)
            if result:
                self.delete_count += 1
                logger.debug(f"🗑️ Deleted {cache_key}")
            return bool(result)
        except Exception as e:
            logger.error(f"❌ Error deleting from cache: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete multiple keys matching pattern"""
        try:
            if not self._initialized:
                return 0
            keys = await self.redis_client.keys(pattern)
            if keys:
                result = await self.redis_client.delete(*keys)
                self.delete_count += result
                logger.info(f"🗑️ Deleted {result} keys matching pattern: {pattern}")
                return result
            return 0
        except Exception as e:
            logger.error(f"❌ Error deleting pattern from cache: {e}")
            return 0

    async def exists(self, data_type: str, identifier: str) -> bool:
        """Check if data exists in cache"""
        try:
            if not self._initialized:
                return False
            return bool(await self.redis_client.exists(self._get_cache_key(data_type, identifier)))
        except Exception as e:
            logger.error(f"❌ Error checking cache existence: {e}")
            return False

    async def get_ttl(self, data_type: str, identifier: str) -> Optional[int]:
        """Get remaining TTL for cached data"""
        try:
            if not self._initialized:
                return None
            ttl = await self.redis_client.ttl(self._get_cache_key(data_type, identifier))
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"❌ Error getting TTL: {e}")
            return None

    async def clear_all(self) -> bool:
        """Clear all cached data"""
        try:
            if not self._initialized:
                return False
            result = await self.redis_client.flushdb()
            logger.info("🧹 Cleared all cache data")
            return bool(result)
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            return False

    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information and statistics"""
        try:
            if not self._initialized:
                return {}
            info = await self.redis_client.info()
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate": hits / max(hits + misses, 1),
                "statistics": {
                    "hit_count": self.hit_count,
                    "miss_count": self.miss_count,
                    "set_count": self.set_count,
                    "delete_count": self.delete_count,
                    "total_requests": self.hit_count + self.miss_count,
                    "hit_rate": self.hit_count / max(self.hit_count + self.miss_count, 1),
                },
                "configuration": {
                    "redis_host": self.config.redis_host,
                    "redis_port": self.config.redis_port,
                    "redis_db": self.config.redis_db,
                    "global_context_ttl": self.config.global_context_ttl,
                    "trends_ttl": self.config.trends_ttl,
                    "max_cache_size": self.config.max_cache_size,
                },
            }
        except Exception as e:
            logger.error(f"❌ Error getting cache info: {e}")
            return {}

    async def is_healthy(self) -> bool:
        """Check if cache service is healthy"""
        try:
            if not self._initialized:
                return False
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the cache service"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 Cache Service connections closed")

    def is_initialized(self) -> bool:
        return self._initialized
