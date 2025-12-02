"""
Unit tests for schema management functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.schema_management import (
    create_tenant_schema,
    initialize_tenant_schema,
    setup_tenant_database,
    drop_tenant_schema,
    migrate_existing_chamas
)


@pytest.fixture
def mock_session():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine."""
    return MagicMock()


class TestCreateTenantSchema:
    """Test tenant schema creation functionality."""

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    @patch('backend.schema_management.os.getenv')
    def test_create_schema_postgresql_new_schema(self, mock_getenv, mock_get_schema_name, mock_admin_session):
        """Test creating a new schema in PostgreSQL."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"
        mock_getenv.return_value = "postgresql://user:pass@host:5432/db"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock schema doesn't exist
        mock_session_instance.execute.return_value.fetchone.return_value = None

        # Call function
        result = create_tenant_schema(123)

        # Assertions
        assert result is True
        mock_get_schema_name.assert_called_with(123)
        mock_session_instance.execute.assert_called()
        mock_session_instance.commit.assert_called()

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    @patch('backend.schema_management.os.getenv')
    def test_create_schema_postgresql_existing_schema(self, mock_getenv, mock_get_schema_name, mock_admin_session):
        """Test handling existing schema in PostgreSQL."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"
        mock_getenv.return_value = "postgresql://user:pass@host:5432/db"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock schema exists
        mock_session_instance.execute.return_value.fetchone.return_value = ["chama_123"]

        # Call function
        result = create_tenant_schema(123)

        # Assertions
        assert result is False
        mock_session_instance.execute.assert_called_once()  # Only the check query
        mock_session_instance.commit.assert_not_called()

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    @patch('backend.schema_management.os.getenv')
    def test_create_schema_non_postgresql(self, mock_getenv, mock_get_schema_name, mock_admin_session):
        """Test schema creation is skipped for non-PostgreSQL databases."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"
        mock_getenv.return_value = "sqlite:///test.db"

        # Call function
        result = create_tenant_schema(123)

        # Assertions
        assert result is True
        # Should not use database session for non-PostgreSQL
        mock_admin_session.assert_not_called()

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    @patch('backend.schema_management.os.getenv')
    def test_create_schema_database_error(self, mock_getenv, mock_get_schema_name, mock_admin_session):
        """Test handling database errors during schema creation."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"
        mock_getenv.return_value = "postgresql://user:pass@host:5432/db"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.execute.return_value.fetchone.return_value = None
        mock_session_instance.execute.side_effect = Exception("Database error")

        # Call function and expect exception
        with pytest.raises(Exception, match="Database error"):
            create_tenant_schema(123)


class TestInitializeTenantSchema:
    """Test tenant schema initialization functionality."""

    @patch('backend.schema_management.get_tenant_engine')
    @patch('backend.schema_management.Base')
    def test_initialize_schema_success(self, mock_base, mock_get_engine):
        """Test successful schema initialization."""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        # Call function
        initialize_tenant_schema(123)

        # Assertions
        mock_get_engine.assert_called_with(123)
        mock_metadata.create_all.assert_called_with(bind=mock_engine)

    @patch('backend.schema_management.get_tenant_engine')
    @patch('backend.schema_management.Base')
    def test_initialize_schema_engine_error(self, mock_base, mock_get_engine):
        """Test handling engine errors during schema initialization."""
        # Setup mocks
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata
        mock_metadata.create_all.side_effect = Exception("Engine error")

        # Call function and expect exception
        with pytest.raises(Exception, match="Engine error"):
            initialize_tenant_schema(123)


class TestSetupTenantDatabase:
    """Test complete tenant database setup functionality."""

    @patch('backend.schema_management.initialize_tenant_schema')
    @patch('backend.schema_management.create_tenant_schema')
    def test_setup_database_new_tenant(self, mock_create_schema, mock_init_schema):
        """Test setting up database for new tenant."""
        # Setup mocks
        mock_create_schema.return_value = True  # Schema was created

        # Call function
        setup_tenant_database(123)

        # Assertions
        mock_create_schema.assert_called_with(123)
        mock_init_schema.assert_called_with(123)

    @patch('backend.schema_management.initialize_tenant_schema')
    @patch('backend.schema_management.create_tenant_schema')
    def test_setup_database_existing_tenant(self, mock_create_schema, mock_init_schema):
        """Test setting up database for existing tenant."""
        # Setup mocks
        mock_create_schema.return_value = False  # Schema already exists

        # Call function
        setup_tenant_database(123)

        # Assertions
        mock_create_schema.assert_called_with(123)
        mock_init_schema.assert_not_called()  # Should not initialize if schema exists


class TestDropTenantSchema:
    """Test tenant schema dropping functionality."""

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    def test_drop_schema_existing_schema(self, mock_get_schema_name, mock_admin_session):
        """Test dropping an existing schema."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock schema exists
        mock_session_instance.execute.return_value.fetchone.return_value = ["chama_123"]

        # Call function
        drop_tenant_schema(123)

        # Assertions
        mock_get_schema_name.assert_called_with(123)
        assert mock_session_instance.execute.call_count == 2  # Check + drop queries
        mock_session_instance.commit.assert_called()

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    def test_drop_schema_nonexistent_schema(self, mock_get_schema_name, mock_admin_session):
        """Test dropping a non-existent schema."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock schema doesn't exist
        mock_session_instance.execute.return_value.fetchone.return_value = None

        # Call function
        drop_tenant_schema(123)

        # Assertions
        mock_session_instance.execute.assert_called_once()  # Only the check query
        mock_session_instance.commit.assert_not_called()

    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    def test_drop_schema_database_error(self, mock_get_schema_name, mock_admin_session):
        """Test handling database errors during schema drop."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"

        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock schema exists but drop fails
        mock_session_instance.execute.return_value.fetchone.return_value = ["chama_123"]
        mock_session_instance.execute.side_effect = [Mock(), Exception("Drop error")]

        # Call function and expect exception
        with pytest.raises(Exception, match="Drop error"):
            drop_tenant_schema(123)


class TestMigrateExistingChamas:
    """Test migration utility for existing chamas."""

    @patch('backend.schema_management.setup_tenant_database')
    @patch('backend.schema_management.AdminSessionLocal')
    def test_migrate_existing_chamas(self, mock_admin_session, mock_setup_db):
        """Test migrating existing chamas to schemas."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock existing chamas
        mock_chama_rows = [Mock(), Mock()]
        mock_chama_rows[0].__getitem__.return_value = 1
        mock_chama_rows[1].__getitem__.return_value = 2
        mock_session_instance.execute.return_value.fetchall.return_value = mock_chama_rows

        # Call function
        migrate_existing_chamas()

        # Assertions
        mock_session_instance.execute.assert_called_once()
        assert mock_setup_db.call_count == 2
        mock_setup_db.assert_any_call(1)
        mock_setup_db.assert_any_call(2)

    @patch('backend.schema_management.setup_tenant_database')
    @patch('backend.schema_management.AdminSessionLocal')
    def test_migrate_existing_chamas_empty(self, mock_admin_session, mock_setup_db):
        """Test migrating when no existing chamas."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock no existing chamas
        mock_session_instance.execute.return_value.fetchall.return_value = []

        # Call function
        migrate_existing_chamas()

        # Assertions
        mock_setup_db.assert_not_called()

    @patch('backend.schema_management.setup_tenant_database')
    @patch('backend.schema_management.AdminSessionLocal')
    def test_migrate_existing_chamas_database_error(self, mock_admin_session, mock_setup_db):
        """Test handling database errors during migration."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance

        # Mock database error
        mock_session_instance.execute.side_effect = Exception("Migration error")

        # Call function and expect exception
        with pytest.raises(Exception, match="Migration error"):
            migrate_existing_chamas()


class TestSchemaManagementIntegration:
    """Integration tests for schema management workflows."""

    @patch('backend.schema_management.initialize_tenant_schema')
    @patch('backend.schema_management.create_tenant_schema')
    @patch('backend.schema_management.AdminSessionLocal')
    @patch('backend.schema_management.get_schema_name')
    @patch('backend.schema_management.os.getenv')
    def test_complete_tenant_lifecycle(self, mock_getenv, mock_get_schema_name,
                                     mock_admin_session, mock_create_schema, mock_init_schema):
        """Test complete tenant database lifecycle."""
        # Setup mocks
        mock_get_schema_name.return_value = "chama_123"
        mock_getenv.return_value = "postgresql://user:pass@host:5432/db"
        mock_create_schema.return_value = True

        # Test setup
        setup_tenant_database(123)
        mock_create_schema.assert_called_with(123)
        mock_init_schema.assert_called_with(123)

        # Reset mocks for drop test
        mock_session_instance = Mock()
        mock_admin_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.execute.return_value.fetchone.return_value = ["chama_123"]

        # Test drop
        drop_tenant_schema(123)
        mock_session_instance.commit.assert_called()
