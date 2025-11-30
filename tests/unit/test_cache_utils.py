"""
Unit tests for cache utilities.
Tests tenant-aware caching, Redis operations, and data isolation.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.cache_utils import (
    TenantRedisCache,
    get_tenant_cache,
    set_chama_summary,
    get_chama_summary,
    set_chama_analytics,
    get_chama_analytics
)


class TestTenantRedisCache:
    """Test the TenantRedisCache class functionality."""

    @patch('backend.cache_utils.redis.Redis')
    def test_initialization(self, mock_redis_class):
        """Test cache initialization with custom parameters."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        cache = TenantRedisCache(host="localhost", port=6379, db=1, password="secret")

        # Trigger connection creation to test parameters
        cache._get_connection()

        mock_redis_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=1,
            password="secret"
        )

        assert cache.host == "localhost"
        assert cache.port == 6379
        assert cache.db == 1

    @patch('backend.cache_utils.redis.Redis')
    def test_connection_lazy_loading(self, mock_redis_class):
        """Test that Redis connection is created lazily."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        cache = TenantRedisCache()

        # Connection should not be created until first use
        mock_redis_class.assert_not_called()

        # Trigger connection creation
        cache._get_connection()

        mock_redis_class.assert_called_once()

    @patch('backend.cache_utils.current_tenant')
    def test_make_tenant_key_with_tenant(self, mock_current_tenant):
        """Test key prefixing when tenant context is set."""
        mock_current_tenant.get.return_value = 123

        cache = TenantRedisCache()
        tenant_key = cache._make_tenant_key("test_key")

        assert tenant_key == "tenant:123:test_key"

    @patch('backend.cache_utils.current_tenant')
    def test_make_tenant_key_without_tenant(self, mock_current_tenant):
        """Test key prefixing when no tenant context exists."""
        mock_current_tenant.get.return_value = None

        cache = TenantRedisCache()
        tenant_key = cache._make_tenant_key("test_key")

        assert tenant_key == "global:test_key"

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_get_operation(self, mock_current_tenant, mock_redis_class):
        """Test basic get operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        mock_redis.get.return_value = b"test_value"

        cache = TenantRedisCache()
        result = cache.get("my_key")

        # Should call Redis get with tenant-prefixed key
        mock_redis.get.assert_called_once_with("tenant:456:my_key")
        assert result == b"test_value"

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_operation(self, mock_current_tenant, mock_redis_class):
        """Test basic set operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 789

        mock_redis.set.return_value = True

        cache = TenantRedisCache()
        result = cache.set("my_key", "my_value")

        # Should call Redis set with tenant-prefixed key
        mock_redis.set.assert_called_once_with("tenant:789:my_key", "my_value")
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_with_expiry(self, mock_current_tenant, mock_redis_class):
        """Test set operation with expiry time."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.setex.return_value = True

        cache = TenantRedisCache()
        result = cache.set("my_key", "my_value", ex=300)

        # Should call Redis setex with tenant-prefixed key and expiry
        mock_redis.setex.assert_called_once_with("tenant:123:my_key", 300, "my_value")
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_delete_operation(self, mock_current_tenant, mock_redis_class):
        """Test delete operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        mock_redis.delete.return_value = 1

        cache = TenantRedisCache()
        result = cache.delete("my_key")

        # Should call Redis delete with tenant-prefixed key
        mock_redis.delete.assert_called_once_with("tenant:456:my_key")
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_delete_operation_not_found(self, mock_current_tenant, mock_redis_class):
        """Test delete operation when key doesn't exist."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        mock_redis.delete.return_value = 0  # Redis returns 0 when key doesn't exist

        cache = TenantRedisCache()
        result = cache.delete("my_key")

        assert result is False

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_exists_operation(self, mock_current_tenant, mock_redis_class):
        """Test exists operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 789

        mock_redis.exists.return_value = 1

        cache = TenantRedisCache()
        result = cache.exists("my_key")

        # Should call Redis exists with tenant-prefixed key
        mock_redis.exists.assert_called_once_with("tenant:789:my_key")
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_exists_operation_not_found(self, mock_current_tenant, mock_redis_class):
        """Test exists operation when key doesn't exist."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 789

        mock_redis.exists.return_value = 0

        cache = TenantRedisCache()
        result = cache.exists("my_key")

        assert result is False

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_get_json_operation(self, mock_current_tenant, mock_redis_class):
        """Test JSON get operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        test_data = {"key": "value", "number": 42}
        mock_redis.get.return_value = json.dumps(test_data).encode('utf-8')

        cache = TenantRedisCache()
        result = cache.get_json("my_key")

        # Should call Redis get with tenant-prefixed key
        mock_redis.get.assert_called_once_with("tenant:123:my_key")
        assert result == test_data

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_get_json_operation_none(self, mock_current_tenant, mock_redis_class):
        """Test JSON get operation when key doesn't exist."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.get.return_value = None

        cache = TenantRedisCache()
        result = cache.get_json("my_key")

        assert result is None

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_get_json_operation_invalid_json(self, mock_current_tenant, mock_redis_class):
        """Test JSON get operation with invalid JSON data."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.get.return_value = b"invalid json data"

        cache = TenantRedisCache()
        result = cache.get_json("my_key")

        assert result is None

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_json_operation(self, mock_current_tenant, mock_redis_class):
        """Test JSON set operation with tenant scoping."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        mock_redis.set.return_value = True

        test_data = {"key": "value", "number": 42}
        cache = TenantRedisCache()
        result = cache.set_json("my_key", test_data)

        # Should call Redis set with tenant-prefixed key and JSON data
        expected_json = json.dumps(test_data)
        mock_redis.set.assert_called_once_with("tenant:456:my_key", expected_json)
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_json_with_expiry(self, mock_current_tenant, mock_redis_class):
        """Test JSON set operation with expiry time."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        mock_redis.setex.return_value = True

        test_data = {"key": "value"}
        cache = TenantRedisCache()
        result = cache.set_json("my_key", test_data, ex=600)

        # Should call Redis setex with tenant-prefixed key and JSON data
        expected_json = json.dumps(test_data)
        mock_redis.setex.assert_called_once_with("tenant:456:my_key", 600, expected_json)
        assert result is True

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_json_operation_invalid_data(self, mock_current_tenant, mock_redis_class):
        """Test JSON set operation with non-serializable data."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 456

        # Non-serializable data (set)
        test_data = {"invalid": set([1, 2, 3])}
        cache = TenantRedisCache()
        result = cache.set_json("my_key", test_data)

        # Should not call Redis operations
        mock_redis.set.assert_not_called()
        mock_redis.setex.assert_not_called()
        assert result is False


class TestCacheErrorHandling:
    """Test error handling in cache operations."""

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_get_operation_redis_error(self, mock_current_tenant, mock_redis_class):
        """Test get operation handles Redis connection errors."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.get.side_effect = Exception("Redis connection failed")

        cache = TenantRedisCache()
        result = cache.get("my_key")

        assert result is None

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_set_operation_redis_error(self, mock_current_tenant, mock_redis_class):
        """Test set operation handles Redis connection errors."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.set.side_effect = Exception("Redis connection failed")

        cache = TenantRedisCache()
        result = cache.set("my_key", "value")

        assert result is False

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_delete_operation_redis_error(self, mock_current_tenant, mock_redis_class):
        """Test delete operation handles Redis connection errors."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.delete.side_effect = Exception("Redis connection failed")

        cache = TenantRedisCache()
        result = cache.delete("my_key")

        assert result is False

    @patch('backend.cache_utils.redis.Redis')
    @patch('backend.cache_utils.current_tenant')
    def test_exists_operation_redis_error(self, mock_current_tenant, mock_redis_class):
        """Test exists operation handles Redis connection errors."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_current_tenant.get.return_value = 123

        mock_redis.exists.side_effect = Exception("Redis connection failed")

        cache = TenantRedisCache()
        result = cache.exists("my_key")

        assert result is False


class TestTenantIsolation:
    """Test tenant data isolation in cache operations."""

    @patch('backend.cache_utils.redis.Redis')
    def test_tenant_isolation_different_tenants(self, mock_redis_class):
        """Test that different tenants cannot access each other's data."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        # Mock Redis to return None for tenant 2's get (no data for that key)
        mock_redis.get.return_value = None

        cache = TenantRedisCache()

        # Simulate tenant 1 setting data
        with patch('backend.cache_utils.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 1
            cache.set("shared_key", "tenant_1_data")

        # Simulate tenant 2 trying to access the same key
        with patch('backend.cache_utils.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 2
            result = cache.get("shared_key")

        # Should get None because tenant 2 has different key
        assert result is None

        # Verify Redis was called with different keys
        set_call = mock_redis.set.call_args[0]
        assert set_call[0] == "tenant:1:shared_key"

        get_call = mock_redis.get.call_args[0]
        assert get_call[0] == "tenant:2:shared_key"

    @patch('backend.cache_utils.redis.Redis')
    def test_global_operations_without_tenant(self, mock_redis_class):
        """Test global operations when no tenant context exists."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        cache = TenantRedisCache()

        # Simulate no tenant context (global operations)
        with patch('backend.cache_utils.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = None

            cache.set("global_key", "global_data")
            result = cache.get("global_key")

        # Should use global prefix
        mock_redis.set.assert_called_with("global:global_key", "global_data")
        assert result == mock_redis.get.return_value


class TestCacheUtilityFunctions:
    """Test the high-level cache utility functions."""

    @patch('backend.cache_utils.get_tenant_cache')
    @patch('backend.database.current_tenant')
    def test_set_chama_summary(self, mock_current_tenant, mock_cache):
        """Test setting chama summary with tenant context management."""
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.set_json.return_value = True

        test_data = {"total_members": 10, "total_contributions": 5000}

        result = set_chama_summary(123, test_data)

        # Should set tenant context
        mock_current_tenant.set.assert_called_once_with(123)

        # Should reset tenant context
        mock_current_tenant.reset.assert_called_once()

        # Should call set_json with correct parameters
        mock_cache_instance.set_json.assert_called_once_with("summary", test_data, ex=3600)

        assert result is True

    @patch('backend.cache_utils.get_tenant_cache')
    @patch('backend.database.current_tenant')
    def test_set_chama_summary_with_exception(self, mock_current_tenant, mock_cache):
        """Test setting chama summary handles exceptions properly."""
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.set_json.side_effect = Exception("Cache error")

        test_data = {"total_members": 5}

        # The function should propagate the exception but still reset tenant context
        with pytest.raises(Exception, match="Cache error"):
            set_chama_summary(456, test_data)

        # Should still reset tenant context even on exception
        mock_current_tenant.set.assert_called_once_with(456)
        mock_current_tenant.reset.assert_called_once()

    @patch('backend.cache_utils.get_tenant_cache')
    def test_get_chama_summary(self, mock_cache):
        """Test getting chama summary."""
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance

        test_data = {"total_members": 15}
        mock_cache_instance.get_json.return_value = test_data

        result = get_chama_summary(789)

        # Should call get_json with summary key
        mock_cache_instance.get_json.assert_called_once_with("summary")

        assert result == test_data

    @patch('backend.cache_utils.get_tenant_cache')
    @patch('backend.database.current_tenant')
    def test_set_chama_analytics(self, mock_current_tenant, mock_cache):
        """Test setting chama analytics with tenant context management."""
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance
        mock_cache_instance.set_json.return_value = True

        test_data = {"monthly_growth": 15.5, "active_users": 50}

        result = set_chama_analytics(321, test_data)

        # Should set tenant context
        mock_current_tenant.set.assert_called_once_with(321)

        # Should reset tenant context
        mock_current_tenant.reset.assert_called_once()

        # Should call set_json with correct parameters
        mock_cache_instance.set_json.assert_called_once_with("analytics", test_data, ex=3600)

        assert result is True

    @patch('backend.cache_utils.get_tenant_cache')
    def test_get_chama_analytics(self, mock_cache):
        """Test getting chama analytics."""
        mock_cache_instance = Mock()
        mock_cache.return_value = mock_cache_instance

        test_data = {"monthly_growth": 12.3}
        mock_cache_instance.get_json.return_value = test_data

        result = get_chama_analytics(654)

        # Should call get_json with analytics key
        mock_cache_instance.get_json.assert_called_once_with("analytics")

        assert result == test_data

    def test_get_tenant_cache_returns_global_instance(self):
        """Test that get_tenant_cache returns the global cache instance."""
        cache_instance = get_tenant_cache()

        # Should return a TenantRedisCache instance
        assert isinstance(cache_instance, TenantRedisCache)

        # Should be the same instance (singleton pattern)
        cache_instance2 = get_tenant_cache()
        assert cache_instance is cache_instance2


class TestCacheConcurrency:
    """Test cache operations under concurrent access patterns."""

    @patch('backend.cache_utils.redis.Redis')
    def test_concurrent_tenant_operations(self, mock_redis_class):
        """Test that concurrent tenant operations don't interfere."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        cache = TenantRedisCache()

        # Simulate concurrent operations from different tenants
        operations = []

        # Tenant 1 operations
        with patch('backend.cache_utils.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 1

            # Set some data
            cache.set("key1", "value1")
            operations.append(("set", "tenant:1:key1", "value1"))

            # Get the data
            cache.get("key1")
            operations.append(("get", "tenant:1:key1"))

        # Tenant 2 operations
        with patch('backend.cache_utils.current_tenant') as mock_tenant:
            mock_tenant.get.return_value = 2

            # Set different data
            cache.set("key1", "value2")  # Same key name, different tenant
            operations.append(("set", "tenant:2:key1", "value2"))

            # Get tenant 2's data
            cache.get("key1")
            operations.append(("get", "tenant:2:key1"))

        # Verify all operations used correct tenant-prefixed keys
        set_calls = mock_redis.set.call_args_list
        get_calls = mock_redis.get.call_args_list

        assert len(set_calls) == 2
        assert len(get_calls) == 2

        # Check that tenant 1 and tenant 2 used different keys
        set_keys = [call[0][0] for call in set_calls]
        get_keys = [call[0][0] for call in get_calls]

        assert "tenant:1:key1" in set_keys
        assert "tenant:2:key1" in set_keys
        assert "tenant:1:key1" in get_keys
        assert "tenant:2:key1" in get_keys

        # Ensure no key collisions
        assert len(set(set_keys)) == 2
        assert len(set(get_keys)) == 2
