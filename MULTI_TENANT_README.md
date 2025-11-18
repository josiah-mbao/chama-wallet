# Multi-Tenant Chama Wallet Implementation

## Overview

This document describes the schema-per-tenant multi-tenancy implementation for the Chama Wallet project. Each chama (cooperative group) now has its own isolated database environment providing complete data separation and scalability.

## Architecture

### Database Design
- **Global Schema (public)**: Users and Chamas tables for cross-tenant operations
- **Tenant Schemas (chama_X)**: Memberships and Contributions tables per chama
- **Schema Naming**: `chama_{chama_id}` (e.g., chama_123)

### Components

#### 1. Database Layer (`backend/database.py`)
- Context-aware database connection management
- Dynamic schema selection based on tenant context
- PostgreSQL `search_path` configuration for schema isolation

#### 2. Tenant Context Middleware (`backend/middleware.py`)
- Extracts `chama_id` from request URLs (`/chamas/{chama_id}/*`)
- Sets tenant context for the request lifecycle
- Automatic cleanup after request processing

#### 3. Schema Management (`backend/schema_management.py`)
- Automatic schema creation for new chamas
- Database initialization utilities
- Migration utilities for existing data

## Data Isolation

### Public Schema
- **users**: Global user accounts (users can belong to multiple chamas)
- **chamas**: Global chama directory

### Tenant Schemas (chama_{id})
- **memberships**: Members of this chama only
- **contributions**: Contribution records for this chama only

## Security & Access Control

### Existing Security Maintained
- JWT-based user authentication
- Role-based access control (owner/treasurer/member)
- Membership verification per chama

### Enhanced Isolation
- Database-level separation prevents data leakage
- Middleware ensures tenant context is always set
- Cross-chama queries are architecturally impossible

## Implementation Details

### Request Flow
1. Request arrives with `/chamas/{chama_id}/...` URL
2. `TenantContextMiddleware` extracts `chama_id` and sets context
3. `get_db()` dependency creates tenant-scoped database session
4. Application logic operates within tenant schema
5. Response sent, context cleaned up

### Schema Creation
- **New Chama Creation**: Automatically creates and initializes schema
- **Migration**: Utility script migrates existing chamas
- **Error Handling**: Robust schema creation with rollback

## Configuration

### Environment Variables
No changes required to existing configuration. The multi-tenant layer is transparent to application code.

### Database Requirements
- PostgreSQL 13+ (schema support)
- User with schema creation permissions
- Existing Docker setup unchanged

## Usage Examples

### Creating New Chama
```bash
POST /chamas/
# Automatically creates: chama_123 schema with tables
# Returns chama details with memberships
```

### Accessing Chama Data
```bash
GET /chamas/123/members
# Uses chama_123 schema for memberships table
```

### Cross-Chama Operations
```bash
GET /chamas/
# Uses public schema for chamas directory
GET /users/profile
# Uses public schema for user data
```

## Migration Strategy

### For Existing Deployments

1. **Backup Database**: Ensure complete backup before migration
2. **Deploy Code**: Update to new multi-tenant version
3. **Run Migration**:
   ```bash
   python -c "from backend.schema_management import migrate_existing_chamas; migrate_existing_chamas()"
   ```
4. **Verify**: Test existing chamas still work
5. **Monitor**: Watch for schema-related errors

### Data Preservation
- All existing user and chama data preserved in public schema
- Membership and contribution data copied to tenant schemas
- Rolling back requires manual data restoration

## Performance Considerations

### Benefits
- **Query Performance**: Smaller tenant table sizes
- **Backup Efficiency**: Per-tenant backup/restore
- **Resource Isolation**: One chama's activity doesn't affect others

### Trade-offs
- Schema management overhead
- Connection pooling complexity
- Cross-chama analytics require special implementation

## Troubleshooting

### Common Issues

#### Schema Not Found
```
ERROR: relation "contributions" does not exist
```
**Solution**: Ensure tenant context is set in middleware. Check URL format.

#### Database Connection Errors
```
ERROR: No tenant context set for database connection
```
**Solution**: Verify TenantContextMiddleware is properly configured in startup sequence.

#### Migration Failures
**Symptoms**: Existing chamas don't work after upgrade
**Solution**: Check schema creation logs, verify database permissions

### Debugging
- Check middleware logs for tenant context setting
- Verify schema exists: `SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'chama_%';`
- Test with specific chama URLs to isolate issues

## Testing

Run the multi-tenant verification script:
```bash
python test_multitenant.py
```

For full integration testing, start the application with PostgreSQL and test:
1. User registration (public schema)
2. Chama creation (auto-creates schema)
3. Chama operations (tenant schema isolation)
4. Cross-chama data isolation

## Future Enhancements

### Schema Evolution
- Alembic integration for schema-specific migrations
- Version management per tenant
- Automated schema upgrades

### Analytics
- Cross-schema analytics strategies
- Aggregated reporting across tenants
- Performance monitoring per schema

### Operational Features
- Per-tenant backup automation
- Schema usage monitoring
- Automated cleanup policies

---

## Summary

The schema-per-tenant implementation provides strong data isolation with:
- ✅ Complete data separation per chama
- ✅ Transparent API behavior
- ✅ Backward compatibility with existing code
- ✅ Scalable to thousands of chamas
- ✅ Robust migration strategy
- ✅ Maintained security model
