"""
Cache Service
============

Service for managing Redis-based caching for Yahoo Finance data.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration"""
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 2
    redis_password: Optional[str] = None
    
    # Cache TTLs (in seconds)
    default_ttl: int = 1800  # 30 minutes
    quote_ttl: int = 300     # 5 minutes
    historical_ttl: int = 3600  # 1 hour
    fundamental_ttl: int = 7200  # 2 hours
    statement_ttl: int = 86400   # 24 hours
    search_ttl: int = 1800       # 30 minutes
    
    # Cache settings
    max_cache_size: int = 10000
    enable_compression: bool = False
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create configuration from environment variables"""
        import os
        return cls(
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "2")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            default_ttl=int(os.getenv("CACHE_TTL", "1800")),
            quote_ttl=int(os.getenv("QUOTE_CACHE_TTL", "300")),
            historical_ttl=int(os.getenv("HISTORICAL_CACHE_TTL", "3600")),
            fundamental_ttl=int(os.getenv("FUNDAMENTAL_CACHE_TTL", "7200")),
            statement_ttl=int(os.getenv("STATEMENT_CACHE_TTL", "86400")),
            search_ttl=int(os.getenv("SEARCH_CACHE_TTL", "1800")),
            max_cache_size=int(os.getenv("MAX_CACHE_SIZE", "10000")),
            enable_compression=os.getenv("ENABLE_COMPRESSION", "false").lower() == "true"
        )


class CacheService:
    """Cache service for Yahoo Finance data"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self._initialized = False
        
        # Statistics
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        self.delete_count = 0
    
    async def initialize(self) -> None:
        """Initialize the cache service"""
        try:
            logger.info("🔧 Initializing Cache Service...")
            
            # Create Redis connection
            redis_url = f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"
            if self.config.redis_password:
                redis_url = f"redis://:{self.config.redis_password}@{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"
            
            self.redis_client = aioredis.from_url(redis_url)
            
            # Test connection
            await self.redis_client.ping()
            
            self._initialized = True
            logger.info("✅ Cache Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Cache Service: {e}")
            raise
    
    def _get_cache_key(self, data_type: str, identifier: str) -> str:
        """Generate cache key for data type and identifier"""
        return f"yahoo:{data_type}:{identifier}"
    
    def _get_ttl(self, data_type: str) -> int:
        """Get TTL for data type"""
        ttl_map = {
            "quote": self.config.quote_ttl,
            "historical": self.config.historical_ttl,
            "fundamental": self.config.fundamental_ttl,
            "statement": self.config.statement_ttl,
            "search": self.config.search_ttl,
            "company": self.config.fundamental_ttl,
            "statistics": self.config.quote_ttl
        }
        return ttl_map.get(data_type, self.config.default_ttl)
    
    async def get(self, data_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        try:
            if not self._initialized:
                return None
            
            cache_key = self._get_cache_key(data_type, identifier)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                self.hit_count += 1
                data = json.loads(cached_data)
                logger.debug(f"✅ Cache hit for {cache_key}")
                return data
            else:
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
            
            # Add timestamp to data
            data_with_timestamp = {
                **data,
                "_cached_at": datetime.now().isoformat(),
                "_cache_ttl": cache_ttl
            }
            
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(data_with_timestamp)
            )
            
            self.set_count += 1
            logger.debug(f"💾 Cached {cache_key} with TTL {cache_ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting cache: {e}")
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
            
            cache_key = self._get_cache_key(data_type, identifier)
            return bool(await self.redis_client.exists(cache_key))
            
        except Exception as e:
            logger.error(f"❌ Error checking cache existence: {e}")
            return False
    
    async def get_ttl(self, data_type: str, identifier: str) -> Optional[int]:
        """Get remaining TTL for cached data"""
        try:
            if not self._initialized:
                return None
            
            cache_key = self._get_cache_key(data_type, identifier)
            ttl = await self.redis_client.ttl(cache_key)
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
            
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1),
                "statistics": {
                    "hit_count": self.hit_count,
                    "miss_count": self.miss_count,
                    "set_count": self.set_count,
                    "delete_count": self.delete_count,
                    "total_requests": self.hit_count + self.miss_count,
                    "hit_rate": self.hit_count / max(self.hit_count + self.miss_count, 1)
                },
                "configuration": {
                    "redis_host": self.config.redis_host,
                    "redis_port": self.config.redis_port,
                    "redis_db": self.config.redis_db,
                    "default_ttl": self.config.default_ttl,
                    "max_cache_size": self.config.max_cache_size
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting cache info: {e}")
            return {}
    
    async def is_healthy(self) -> bool:
        """Check if cache service is healthy"""
        try:
            if not self._initialized:
                return False
            
            # Test Redis connection
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
        """Check if service is initialized"""
        return self._initialized 