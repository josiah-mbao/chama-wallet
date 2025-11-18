"""
Tenant-aware caching utilities for multi-tenant chama-wallet.
Ensures all cache operations are scoped to specific tenants.
"""
import json
import redis
from typing import Optional, Any, Dict, Union
from backend.config import settings
from backend.database import current_tenant
from backend.logging_config import setup_logging

logger = setup_logging()


class TenantRedisCache:
    """Redis cache wrapper that automatically scopes operations to current tenant."""

    def __init__(self, host: str = None, port: int = None, db: int = None, **kwargs):
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db or settings.REDIS_DB
        self._redis_kwargs = kwargs
        self._redis_conn = None

    def _get_connection(self) -> redis.Redis:
        """Get Redis connection instance."""
        if self._redis_conn is None:
            self._redis_conn = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                **self._redis_kwargs
            )
        return self._redis_conn

    def _make_tenant_key(self, key: str) -> str:
        """Prefix key with tenant identifier for isolation."""
        tenant_id = current_tenant.get()
        if tenant_id is None:
            # For operations that don't have tenant context (admin operations)
            # Use a global prefix to avoid collisions
            return f"global:{key}"
        return f"tenant:{tenant_id}:{key}"

    def get(self, key: str) -> Optional[str]:
        """Get value from cache with tenant scoping."""
        tenant_key = self._make_tenant_key(key)
        try:
            r = self._get_connection()
            return r.get(tenant_key)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{tenant_key}': {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in cache with tenant scoping."""
        tenant_key = self._make_tenant_key(key)
        try:
            r = self._get_connection()
            if ex:
                return r.setex(tenant_key, ex, value)
            else:
                return r.set(tenant_key, value)
        except Exception as e:
            logger.warning(f"Cache set failed for key '{tenant_key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache with tenant scoping."""
        tenant_key = self._make_tenant_key(key)
        try:
            r = self._get_connection()
            return r.delete(tenant_key) > 0
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{tenant_key}': {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache with tenant scoping."""
        tenant_key = self._make_tenant_key(key)
        try:
            r = self._get_connection()
            return r.exists(tenant_key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for key '{tenant_key}': {e}")
            return False

    def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache with tenant scoping."""
        raw_value = self.get(key)
        if raw_value is None:
            return None

        try:
            return json.loads(raw_value.decode('utf-8') if isinstance(raw_value, bytes) else raw_value)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to decode JSON for key '{key}': {e}")
            return None

    def set_json(self, key: str, value: Dict, ex: Optional[int] = None) -> bool:
        """Set JSON value in cache with tenant scoping."""
        try:
            serialized = json.dumps(value)
            return self.set(key, serialized, ex)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize JSON for key '{key}': {e}")
            return False


# Global cache instance
tenant_cache = TenantRedisCache(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    socket_connect_timeout=5,
    socket_timeout=5
)


def get_tenant_cache() -> TenantRedisCache:
    """Get the tenant-aware Redis cache instance."""
    return tenant_cache


def set_chama_summary(chama_id: int, summary_data: Dict) -> bool:
    """Cache chama summary data with proper tenant scoping."""
    # This function is used by background tasks and needs to temporarily set tenant context
    from backend.database import current_tenant

    token = current_tenant.set(chama_id)
    try:
        cache = get_tenant_cache()
        return cache.set_json("summary", summary_data, ex=3600)  # 1 hour
    finally:
        current_tenant.reset(token)


def get_chama_summary(chama_id: int) -> Optional[Dict]:
    """Retrieve chama summary data with tenant scoping."""
    # This function can be used from API endpoints without needing to set context
    # since the middleware will have set it already
    cache = get_tenant_cache()
    return cache.get_json("summary")


def set_chama_analytics(chama_id: int, analytics_data: Dict) -> bool:
    """Cache chama analytics data with proper tenant scoping."""
    from backend.database import current_tenant

    token = current_tenant.set(chama_id)
    try:
        cache = get_tenant_cache()
        return cache.set_json("analytics", analytics_data, ex=3600)  # 1 hour
    finally:
        current_tenant.reset(token)


def get_chama_analytics(chama_id: int) -> Optional[Dict]:
    """Retrieve chama analytics data with tenant scoping."""
    cache = get_tenant_cache()
    return cache.get_json("analytics")
