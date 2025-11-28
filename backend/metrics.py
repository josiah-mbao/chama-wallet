"""
Tenant-aware metrics collection for multi-tenant chama wallet.
Tracks performance metrics and operational data per tenant.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Optional, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from backend.database import current_tenant
from backend.logging_config import setup_logging

logger = setup_logging()

# Create a tenant-aware registry
TENANT_REGISTRY = CollectorRegistry()

# Global metrics with tenant labels
REQUEST_COUNT = Counter(
    'chama_api_requests_total',
    'Total number of API requests',
    ['tenant', 'method', 'endpoint', 'status_code'],
    registry=TENANT_REGISTRY
)

REQUEST_LATENCY = Histogram(
    'chama_api_request_duration_seconds',
    'API request duration in seconds',
    ['tenant', 'method', 'endpoint'],
    registry=TENANT_REGISTRY
)

DATABASE_QUERIES = Counter(
    'chama_database_queries_total',
    'Total number of database queries executed',
    ['tenant', 'operation', 'table'],
    registry=TENANT_REGISTRY
)

CACHE_OPERATIONS = Counter(
    'chama_cache_operations_total',
    'Total cache operations',
    ['tenant', 'operation', 'key_pattern'],
    registry=TENANT_REGISTRY
)

ACTIVE_SESSIONS = Gauge(
    'chama_active_sessions',
    'Number of currently active tenant sessions',
    ['tenant'],
    registry=TENANT_REGISTRY
)

RATE_LIMIT_VIOLATIONS = Counter(
    'chama_rate_limit_violations_total',
    'Total number of rate limit violations',
    ['tenant', 'violator_type'],
    registry=TENANT_REGISTRY
)

# Thread-local storage for metrics context
class MetricsContext:
    """Thread-local context for tracking metrics during request processing"""

    def __init__(self):
        self.tenant_id = None
        self.request_start_time = None
        self.db_query_count = 0
        self.cache_ops = defaultdict(int)

    def start_request(self, tenant_id: Optional[int] = None):
        """Start tracking a request"""
        self.tenant_id = tenant_id or current_tenant.get()
        self.request_start_time = time.time()
        self.db_query_count = 0
        self.cache_ops.clear()

        if self.tenant_id:
            ACTIVE_SESSIONS.labels(tenant=f"chama_{self.tenant_id}").inc()

    def end_request(self, method: str, endpoint: str, status_code: int):
        """End tracking a request and record metrics"""
        if not self.request_start_time or not self.tenant_id:
            return

        tenant_label = f"chama_{self.tenant_id}"
        duration = time.time() - self.request_start_time

        # Record request metrics
        REQUEST_COUNT.labels(
            tenant=tenant_label,
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        REQUEST_LATENCY.labels(
            tenant=tenant_label,
            method=method,
            endpoint=endpoint
        ).observe(duration)

        # Record DB query metrics
        if self.db_query_count > 0:
            DATABASE_QUERIES.labels(
                tenant=tenant_label,
                operation='query',
                table='all'
            ).inc(self.db_query_count)

        # Record cache operation metrics
        for op, count in self.cache_ops.items():
            if count > 0:
                CACHE_OPERATIONS.labels(
                    tenant=tenant_label,
                    operation=op,
                    key_pattern='tenant_scoped'
                ).inc(count)

        # Decrement active sessions
        ACTIVE_SESSIONS.labels(tenant=tenant_label).dec()

        logger.info(
            f"Request metrics recorded: tenant={tenant_label}, "
            f"duration={duration:.3f}s, queries={self.db_query_count}, "
            f"cache_ops={dict(self.cache_ops)}"
        )

    def record_db_query(self, operation: str = 'query', table: str = 'unknown'):
        """Record a database query execution"""
        self.db_query_count += 1
        if self.tenant_id:
            DATABASE_QUERIES.labels(
                tenant=f"chama_{self.tenant_id}",
                operation=operation,
                table=table
            ).inc()

    def record_cache_operation(self, operation: str, key_pattern: str = 'tenant_scoped'):
        """Record a cache operation"""
        self.cache_ops[operation] += 1

    def record_rate_limit_violation(self, violator_type: str = 'unknown'):
        """Record a rate limit violation"""
        if self.tenant_id:
            RATE_LIMIT_VIOLATIONS.labels(
                tenant=f"chama_{self.tenant_id}",
                violator_type=violator_type
            ).inc()

# Thread-local metrics context
_local = threading.local()

def get_metrics_context() -> MetricsContext:
    """Get the current thread's metrics context"""
    if not hasattr(_local, 'metrics_context'):
        _local.metrics_context = MetricsContext()
    return _local.metrics_context

def start_request_metrics(tenant_id: Optional[int] = None):
    """Start tracking metrics for a request"""
    context = get_metrics_context()
    context.start_request(tenant_id)

def end_request_metrics(method: str, endpoint: str, status_code: int):
    """End tracking metrics for a request"""
    context = get_metrics_context()
    context.end_request(method, endpoint, status_code)

def record_db_query(operation: str = 'query', table: str = 'unknown'):
    """Record a database query operation"""
    context = get_metrics_context()
    context.record_db_query(operation, table)

def record_cache_operation(operation: str, key_pattern: str = 'tenant_scoped'):
    """Record a cache operation"""
    context = get_metrics_context()
    context.record_cache_operation(operation, key_pattern)

def record_rate_limit_violation(violator_type: str = 'unknown'):
    """Record a rate limit violation"""
    context = get_metrics_context()
    context.record_rate_limit_violation(violator_type)

def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of current metrics for monitoring"""
    # Get basic registry info without the complex objects
    collectors = []
    for collector in TENANT_REGISTRY._collector_to_names.keys():
        collectors.append({
            "name": collector._name if hasattr(collector, '_name') else str(type(collector).__name__),
            "type": type(collector).__name__
        })

    return {
        "registry_info": {
            "collectors_count": len(collectors),
            "collectors": collectors
        },
        "summary": {
            "description": "Tenant-aware metrics for multi-tenant chama wallet",
            "total_tenants_tracked": len([c for c in collectors if 'chama_' in str(c)]),
            "metrics_types": ["requests", "latency", "database_queries", "cache_operations", "active_sessions", "rate_limit_violations"]
        }
    }

# Export Prometheus metrics endpoint
from prometheus_client import generate_latest

def get_prometheus_metrics():
    """Generate Prometheus-formatted metrics"""
    return generate_latest(registry=TENANT_REGISTRY)
