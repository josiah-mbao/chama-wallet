"""
Schema management utilities for multi-tenant chama-wallet.
Handles schema creation and tenant database operations.
"""
from sqlalchemy import text
from backend.database import AdminSessionLocal, get_schema_name
from backend import models
import logging

logger = logging.getLogger(__name__)


def create_tenant_schema(tenant_id: int) -> bool:
    """
    Create schema for a new tenant if it doesn't exist.

    Args:
        tenant_id: The chama ID for which to create schema

    Returns:
        bool: True if schema was created, False if it already exists
    """
    schema_name = get_schema_name(tenant_id)

    # Skip schema operations for non-PostgreSQL databases (like SQLite in tests)
    import os
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url.startswith('postgresql'):
        logger.info(f"Skipping schema creation for {schema_name} (non-PostgreSQL database)")
        return True  # Pretend schema was created

    try:
        with AdminSessionLocal() as session:
            # Check if schema already exists
            result = session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": schema_name}
            ).fetchone()

            if result:
                logger.info(f"Schema {schema_name} already exists")
                return False

            # Create schema
            session.execute(text(f"CREATE SCHEMA {schema_name}"))
            session.commit()

            logger.info(f"Created schema {schema_name} for tenant {tenant_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to create schema {schema_name}: {e}")
        raise


def initialize_tenant_schema(tenant_id: int):
    """
    Initialize schema with required tables and any initial data.

    Args:
        tenant_id: The chama ID for which to initialize schema
    """
    from backend.database import get_tenant_engine
    from backend.models.chama import Chama

    schema_name = get_schema_name(tenant_id)
    engine = get_tenant_engine(tenant_id)

    try:
        # Create all tables in the tenant schema
        # SQLAlchemy will create tables with the schema prefix based on search_path
        models.Base.metadata.create_all(bind=engine)

        logger.info(f"Initialized tables for schema {schema_name}")

    except Exception as e:
        logger.error(f"Failed to initialize schema {schema_name}: {e}")
        raise


def setup_tenant_database(tenant_id: int):
    """
    Complete setup for a new tenant: create schema and initialize tables.

    Args:
        tenant_id: The chama ID for the new tenant
    """
    logger.info(f"Setting up database for tenant {tenant_id}")

    # Create schema if needed
    schema_created = create_tenant_schema(tenant_id)

    if schema_created:
        # Initialize tables only if schema was newly created
        initialize_tenant_schema(tenant_id)

    logger.info(f"Database setup complete for tenant {tenant_id}")


def drop_tenant_schema(tenant_id: int):
    """
    Drop a tenant schema (admin operation - use with caution).

    Args:
        tenant_id: The chama ID whose schema to drop
    """
    schema_name = get_schema_name(tenant_id)

    try:
        with AdminSessionLocal() as session:
            # Check if schema exists
            result = session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": schema_name}
            ).fetchone()

            if not result:
                logger.warning(f"Schema {schema_name} does not exist")
                return

            # Drop schema and all its objects
            session.execute(text(f"DROP SCHEMA {schema_name} CASCADE"))
            session.commit()

            logger.info(f"Dropped schema {schema_name} for tenant {tenant_id}")

    except Exception as e:
        logger.error(f"Failed to drop schema {schema_name}: {e}")
        raise


def migrate_existing_chamas():
    """
    Migration utility to create schemas for existing chamas.
    Run this once after implementing multi-tenancy.
    """
    from backend.database import AdminSessionLocal

    try:
        with AdminSessionLocal() as session:
            # Get all existing chama IDs
            result = session.execute(text("SELECT id FROM public.chamas")).fetchall()

            for chama_row in result:
                chama_id = chama_row[0]
                logger.info(f"Migrating existing chama {chama_id}")
                setup_tenant_database(chama_id)

        logger.info("Migration of existing chamas completed")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
