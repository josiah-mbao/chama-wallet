#!/usr/bin/env python3
"""
Migration script to set up multi-tenancy for existing chamas.
Run this after updating to multi-tenant architecture.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Set basic environment for migration
os.environ.setdefault("DATABASE_URL", "postgresql://chamauser:chamapassword@localhost:5432/chamadb")
os.environ.setdefault("SECRET_KEY", "migration_secret_key")

from backend.schema_management import migrate_existing_chamas

if __name__ == "__main__":
    print("🔄 Starting multi-tenant migration...")
    migrate_existing_chamas()
    print("✅ Multi-tenant migration completed!")
