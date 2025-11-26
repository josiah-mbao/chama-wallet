
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings
import contextvars
from typing import Optional, Generator

DATABASE_URL = settings.DATABASE_URL

# Context variable to hold current tenant (chama_id)
current_tenant: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    'current_tenant', default=None
)


def get_schema_name(tenant_id: int) -> str:
    """Generate schema name for a tenant."""
    return f"chama_{tenant_id}"


def get_tenant_engine(tenant_id: Optional[int] = None):
    """Get SQLAlchemy engine configured for specific tenant schema."""
    # Use current tenant if none specified
    tenant_id = tenant_id or current_tenant.get()

    if tenant_id is None:
        raise ValueError("No tenant context set for database connection")

    schema_name = get_schema_name(tenant_id)

    # Create schema-specific connection
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        # Set search_path for this connection to the tenant schema
        connect_args={"options": f"-c search_path={schema_name},public"}
    )

    return engine


# Global engine for non-tenant operations (shared tables, admin operations)
admin_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Global sessionmaker for admin operations
AdminSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_engine)

# For operations that need tenant scoping (when tenant context is set)
def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a SQLAlchemy session (public or tenant-scoped)."""
    tenant_id = current_tenant.get()
    if tenant_id is not None:
        # Tenant context is set - use tenant-scoped session
        engine = get_tenant_engine()
        db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    else:
        # No tenant context - use admin session for public schema operations
        db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()
