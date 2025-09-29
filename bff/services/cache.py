"""
Caching Service

Provides intelligent caching for chart data and other expensive operations.
Uses Redis for distributed caching with appropriate TTL strategies.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib

from bff.models.chart_data import ChartDataResponse, BarData, ResponseMetadata
from bff.models.run_data import CompleteRunResponse
from bff.app.config import (
    REDIS_ENABLED,
    REDIS_TTL_CHART_DATA,
    DEFAULT_CHART_TARGET_POINTS
)


class CacheService:
    """Service for caching chart data and responses."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.logger = logging.getLogger("bff.cache")
        self.enabled = REDIS_ENABLED and redis_client is not None
    
    def generate_chart_cache_key(
        self,
        symbol: str,
        timeframe: str,
        from_date: str,
        to_date: str,
        target_points: int = DEFAULT_CHART_TARGET_POINTS,
        rth_only: bool = True
    ) -> str:
        """
        Generate cache key for chart data.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            from_date: Start date
            to_date: End date
            target_points: Target data points
            rth_only: Regular trading hours only
            
        Returns:
            str: Cache key
        """
        # Create deterministic cache key
        key_data = f"{symbol}:{timeframe}:{from_date}:{to_date}:{target_points}:{rth_only}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"chart:{key_hash}"
    
    async def get_chart_data(
        self,
        cache_key: str,
        correlation_id: Optional[str] = None
    ) -> Optional[ChartDataResponse]:
        """
        Get chart data from cache.
        
        Args:
            cache_key: Cache key
            correlation_id: Request correlation ID
            
        Returns:
            Optional[ChartDataResponse]: Cached data or None
        """
        if not self.enabled:
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                self.logger.info(
                    "cache.hit",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                        "data_size": len(cached_data),
                    }
                )
                
                # Deserialize cached data
                data_dict = json.loads(cached_data)
                return ChartDataResponse(**data_dict)
            else:
                self.logger.info(
                    "cache.miss",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                    }
                )
                return None
                
        except Exception as e:
            self.logger.error(
                "cache.get_error",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "error": str(e),
                }
            )
            return None
    
    async def set_chart_data(
        self,
        cache_key: str,
        data: ChartDataResponse,
        ttl_seconds: int = REDIS_TTL_CHART_DATA,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Store chart data in cache.
        
        Args:
            cache_key: Cache key
            data: Chart data to cache
            ttl_seconds: Time to live in seconds
            correlation_id: Request correlation ID
            
        Returns:
            bool: True if cached successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Update metadata to indicate cache storage
            data.metadata.cache_hit = False  # This is the original data
            
            # Serialize data
            serialized_data = data.json()
            
            # Store in cache with TTL
            await self.redis_client.setex(
                cache_key,
                ttl_seconds,
                serialized_data
            )
            
            self.logger.info(
                "cache.set",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "ttl_seconds": ttl_seconds,
                    "data_size": len(serialized_data),
                    "bars_count": len(data.bars),
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "cache.set_error",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "error": str(e),
                }
            )
            return False
    
    async def invalidate_chart_data(
        self,
        symbol: str,
        correlation_id: Optional[str] = None
    ) -> int:
        """
        Invalidate all cached chart data for a symbol.
        
        Args:
            symbol: Trading symbol
            correlation_id: Request correlation ID
            
        Returns:
            int: Number of keys invalidated
        """
        if not self.enabled:
            return 0
        
        try:
            # Find all cache keys for this symbol
            pattern = f"chart:*{symbol}*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                
                self.logger.info(
                    "cache.invalidate",
                    extra={
                        "correlation_id": correlation_id,
                        "symbol": symbol,
                        "keys_deleted": deleted_count,
                    }
                )
                
                return deleted_count
            else:
                return 0
                
        except Exception as e:
            self.logger.error(
                "cache.invalidate_error",
                extra={
                    "correlation_id": correlation_id,
                    "symbol": symbol,
                    "error": str(e),
                }
            )
            return 0
    
    def calculate_ttl(
        self,
        from_date: str,
        to_date: str,
        timeframe: str
    ) -> int:
        """
        Calculate appropriate TTL based on data recency.
        
        Args:
            from_date: Start date
            to_date: End date
            timeframe: Data timeframe
            
        Returns:
            int: TTL in seconds
        """
        try:
            to_date_obj = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            now = datetime.now(to_date_obj.tzinfo) if to_date_obj.tzinfo else datetime.now()
            
            days_old = (now - to_date_obj).days
            
            # Shorter TTL for recent data, longer for historical
            if days_old <= 1:
                # Recent data: 5 minutes
                return 300
            elif days_old <= 7:
                # Week old: 1 hour
                return 3600
            elif days_old <= 30:
                # Month old: 6 hours
                return 21600
            else:
                # Historical data: 24 hours
                return 86400
                
        except Exception:
            # Fallback to default TTL
            return REDIS_TTL_CHART_DATA
    
    async def get_cache_stats(
        self,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            correlation_id: Request correlation ID
            
        Returns:
            Dict[str, Any]: Cache statistics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "redis_available": False,
            }
        
        try:
            info = await self.redis_client.info()
            
            return {
                "enabled": True,
                "redis_available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
            
        except Exception as e:
            self.logger.error(
                "cache.stats_error",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                }
            )
            
            return {
                "enabled": True,
                "redis_available": False,
                "error": str(e),
            }

    def generate_run_cache_key(
        self,
        run_id: str,
        include_orders: bool = True,
        include_equity: bool = True,
        include_metrics: bool = True
    ) -> str:
        """
        Generate cache key for run data.

        Args:
            run_id: Run identifier
            include_orders: Whether orders are included
            include_equity: Whether equity is included
            include_metrics: Whether metrics are included

        Returns:
            str: Cache key
        """
        # Create deterministic cache key
        key_data = f"{run_id}:{include_orders}:{include_equity}:{include_metrics}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"run:{key_hash}"

    async def get_run_data(
        self,
        cache_key: str,
        correlation_id: Optional[str] = None
    ) -> Optional[CompleteRunResponse]:
        """
        Get run data from cache.

        Args:
            cache_key: Cache key
            correlation_id: Request correlation ID

        Returns:
            Optional[CompleteRunResponse]: Cached data or None
        """
        if not self.enabled:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                self.logger.info(
                    "cache.hit",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                        "data_size": len(cached_data),
                    }
                )

                # Deserialize cached data
                data_dict = json.loads(cached_data)
                return CompleteRunResponse(**data_dict)
            else:
                self.logger.info(
                    "cache.miss",
                    extra={
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                    }
                )
                return None

        except Exception as e:
            self.logger.error(
                "cache.get_error",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "error": str(e),
                }
            )
            return None

    async def set_run_data(
        self,
        cache_key: str,
        data: CompleteRunResponse,
        ttl_seconds: int,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Store run data in cache.

        Args:
            cache_key: Cache key
            data: Run data to cache
            ttl_seconds: Time to live in seconds
            correlation_id: Request correlation ID

        Returns:
            bool: True if cached successfully
        """
        if not self.enabled:
            return False

        try:
            # Update metadata to indicate cache storage
            data.metadata.cache_hit = False  # This is the original data

            # Serialize data
            serialized_data = data.json()

            # Store in cache with TTL
            await self.redis_client.setex(
                cache_key,
                ttl_seconds,
                serialized_data
            )

            self.logger.info(
                "cache.set",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "ttl_seconds": ttl_seconds,
                    "data_size": len(serialized_data),
                    "run_status": data.run.status,
                }
            )

            return True

        except Exception as e:
            self.logger.error(
                "cache.set_error",
                extra={
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "error": str(e),
                }
            )
            return False
