"""
Comprehensive unit tests for migration utilities.

This module contains extensive tests for Alembic migration utilities including
get_alembic_config, get_database_url, check_database_exists, get_current_revision,
get_head_revision, run_migrations, and initialize_database_with_migrations.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

import pytest

from utils.migrations import (
    get_alembic_config,
    get_database_url,
    check_database_exists,
    get_current_revision,
    get_head_revision,
    run_migrations,
    create_initial_migration_if_needed,
    initialize_database_with_migrations
)


class TestGetAlembicConfig:
    """Test suite for get_alembic_config function."""

    def test_get_alembic_config_success(self):
        """Test successful Alembic config retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock alembic.ini file
            alembic_ini = Path(temp_dir) / "alembic.ini"
            alembic_ini.write_text("""
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///test.db
            """)
            
            # Create mock alembic directory
            alembic_dir = Path(temp_dir) / "alembic"
            alembic_dir.mkdir()
            
            with patch('utils.migrations.Path') as mock_path:
                # Mock the path resolution
                mock_path_instance = Mock()
                mock_path_instance.parent.parent = Path(temp_dir)
                mock_path.return_value = mock_path_instance
                
                config = get_alembic_config()
                
                assert isinstance(config, Config)

    def test_get_alembic_config_file_not_found(self):
        """Test Alembic config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('utils.migrations.Path') as mock_path:
                # Mock path that points to non-existent alembic.ini
                mock_path_instance = Mock()
                mock_path_instance.parent.parent = Path(temp_dir)
                mock_path.return_value = mock_path_instance
                
                with pytest.raises(FileNotFoundError) as exc_info:
                    get_alembic_config()
                
                assert "Alembic configuration not found" in str(exc_info.value)

    @patch('utils.migrations.Config')
    def test_get_alembic_config_sets_script_location(self, mock_config_class):
        """Test that script location is set correctly."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock alembic.ini
            alembic_ini = Path(temp_dir) / "alembic.ini"
            alembic_ini.write_text("[alembic]\nscript_location = alembic")
            
            with patch('utils.migrations.Path') as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.parent.parent = Path(temp_dir)
                mock_path.return_value = mock_path_instance
                
                get_alembic_config()
                
                # Should set script location
                mock_config.set_main_option.assert_called_once()
                call_args = mock_config.set_main_option.call_args
                assert call_args[0][0] == "script_location"
                assert "alembic" in call_args[0][1]


class TestGetDatabaseUrl:
    """Test suite for get_database_url function."""

    def test_get_database_url_from_environment(self):
        """Test getting database URL from environment variable."""
        test_url = "postgresql://user:pass@localhost/test_db"
        
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            url = get_database_url()
            assert url == test_url

    @patch('utils.migrations.get_alembic_config')
    def test_get_database_url_from_alembic_config(self, mock_get_config):
        """Test getting database URL from alembic config when env var not set."""
        mock_config = Mock()
        mock_config.get_main_option.return_value = "sqlite:///alembic.db"
        mock_get_config.return_value = mock_config
        
        with patch.dict(os.environ, {}, clear=True):
            url = get_database_url()
            
            assert url == "sqlite:///alembic.db"
            mock_config.get_main_option.assert_called_once_with("sqlalchemy.url")

    def test_get_database_url_environment_priority(self):
        """Test that environment variable takes priority over config."""
        env_url = "postgresql://env:pass@localhost/env_db"
        
        with patch.dict(os.environ, {"DATABASE_URL": env_url}):
            with patch('utils.migrations.get_alembic_config') as mock_get_config:
                mock_config = Mock()
                mock_config.get_main_option.return_value = "sqlite:///config.db"
                mock_get_config.return_value = mock_config
                
                url = get_database_url()
                
                assert url == env_url
                # Should not call config method
                mock_config.get_main_option.assert_not_called()


class TestCheckDatabaseExists:
    """Test suite for check_database_exists function."""

    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.create_engine')
    @patch('utils.migrations.inspect')
    def test_check_database_exists_with_tables(self, mock_inspect, mock_create_engine, mock_get_db_url):
        """Test database exists check when database has tables."""
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ["products", "images"]
        mock_inspect.return_value = mock_inspector
        
        result = check_database_exists()
        
        assert result is True
        mock_engine.dispose.assert_called_once()

    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.create_engine')
    @patch('utils.migrations.inspect')
    def test_check_database_exists_no_tables(self, mock_inspect, mock_create_engine, mock_get_db_url):
        """Test database exists check when database has no tables."""
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        result = check_database_exists()
        
        assert result is False
        mock_engine.dispose.assert_called_once()

    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.create_engine')
    @patch('utils.migrations.logger')
    def test_check_database_exists_exception(self, mock_logger, mock_create_engine, mock_get_db_url):
        """Test database exists check when exception occurs."""
        mock_get_db_url.return_value = "sqlite:///test.db"
        mock_create_engine.side_effect = Exception("Connection failed")
        
        result = check_database_exists()
        
        assert result is False
        mock_logger.warning.assert_called()
        assert "Could not check database existence" in str(mock_logger.warning.call_args)


class TestGetCurrentRevision:
    """Test suite for get_current_revision function."""

    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.create_engine')
    def test_get_current_revision_success(self, mock_create_engine, mock_get_db_url):
        """Test successful current revision retrieval."""
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_connection = Mock()
        # Create a proper context manager mock
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        
        mock_context = Mock()
        mock_context.get_current_revision.return_value = "abc123def456"
        
        with patch('utils.migrations.MigrationContext') as mock_migration_context:
            mock_migration_context.configure.return_value = mock_context
            
            revision = get_current_revision()
            
            assert revision == "abc123def456"
            mock_engine.dispose.assert_called_once()

    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.create_engine')
    @patch('utils.migrations.logger')
    def test_get_current_revision_exception(self, mock_logger, mock_create_engine, mock_get_db_url):
        """Test current revision retrieval when exception occurs."""
        mock_get_db_url.return_value = "sqlite:///test.db"
        mock_create_engine.side_effect = Exception("Database error")
        
        revision = get_current_revision()
        
        assert revision is None
        mock_logger.warning.assert_called()
        assert "Could not get current revision" in str(mock_logger.warning.call_args)


class TestGetHeadRevision:
    """Test suite for get_head_revision function."""

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.ScriptDirectory')
    def test_get_head_revision_success(self, mock_script_dir_class, mock_get_config):
        """Test successful head revision retrieval."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_script_dir = Mock()
        mock_script_dir.get_current_head.return_value = "xyz789abc123"
        mock_script_dir_class.from_config.return_value = mock_script_dir
        
        revision = get_head_revision()
        
        assert revision == "xyz789abc123"
        mock_script_dir_class.from_config.assert_called_once_with(mock_config)

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.ScriptDirectory')
    @patch('utils.migrations.logger')
    def test_get_head_revision_exception(self, mock_logger, mock_script_dir_class, mock_get_config):
        """Test head revision retrieval when exception occurs."""
        mock_get_config.side_effect = Exception("Config error")
        
        revision = get_head_revision()
        
        assert revision is None
        mock_logger.error.assert_called()
        assert "Could not get head revision" in str(mock_logger.error.call_args)


class TestRunMigrations:
    """Test suite for run_migrations function."""

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.get_current_revision')
    @patch('utils.migrations.get_head_revision')
    @patch('utils.migrations.command')
    @patch('utils.migrations.logger')
    def test_run_migrations_up_to_date(self, mock_logger, mock_command, mock_get_head, 
                                     mock_get_current, mock_get_db_url, mock_get_config):
        """Test run_migrations when database is already up to date."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        # Same revision for current and head
        mock_get_current.return_value = "abc123"
        mock_get_head.return_value = "abc123"
        
        result = run_migrations()
        
        assert result is True
        mock_logger.info.assert_called()
        assert "already up to date" in str(mock_logger.info.call_args)
        mock_command.upgrade.assert_not_called()

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.get_current_revision')
    @patch('utils.migrations.get_head_revision')
    @patch('utils.migrations.command')
    @patch('utils.migrations.logger')
    def test_run_migrations_upgrade_needed(self, mock_logger, mock_command, mock_get_head,
                                         mock_get_current, mock_get_db_url, mock_get_config):
        """Test run_migrations when upgrade is needed."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        # Different revisions
        mock_get_current.return_value = "abc123"
        mock_get_head.return_value = "def456"
        
        result = run_migrations()
        
        assert result is True
        mock_config.set_main_option.assert_called_once_with("sqlalchemy.url", "sqlite:///test.db")
        mock_command.upgrade.assert_called_once_with(mock_config, "head")
        mock_logger.info.assert_called()

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.get_current_revision')
    @patch('utils.migrations.get_head_revision')
    @patch('utils.migrations.command')
    @patch('utils.migrations.logger')
    def test_run_migrations_no_history(self, mock_logger, mock_command, mock_get_head,
                                     mock_get_current, mock_get_db_url, mock_get_config):
        """Test run_migrations when no migration history exists."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        # No current revision
        mock_get_current.return_value = None
        mock_get_head.return_value = "def456"
        
        result = run_migrations()
        
        assert result is True
        mock_command.upgrade.assert_called_once_with(mock_config, "head")
        mock_logger.info.assert_called()
        # Check for the specific log message about no migration history
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("No migration history found" in call for call in log_calls)

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.logger')
    def test_run_migrations_exception(self, mock_logger, mock_get_config):
        """Test run_migrations when exception occurs."""
        mock_get_config.side_effect = Exception("Migration failed")
        
        result = run_migrations()
        
        assert result is False
        mock_logger.error.assert_called()
        assert "Migration failed" in str(mock_logger.error.call_args)


class TestCreateInitialMigration:
    """Test suite for create_initial_migration_if_needed function."""

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.ScriptDirectory')
    @patch('utils.migrations.logger')
    def test_create_initial_migration_already_exists(self, mock_logger, mock_script_dir_class, mock_get_config):
        """Test create_initial_migration when migrations already exist."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_script_dir = Mock()
        # Mock existing revisions
        mock_script_dir.walk_revisions.return_value = [Mock(), Mock()]
        mock_script_dir_class.from_config.return_value = mock_script_dir
        
        result = create_initial_migration_if_needed()
        
        assert result is True
        mock_logger.debug.assert_called()
        assert "Migrations already exist" in str(mock_logger.debug.call_args)

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.ScriptDirectory')
    @patch('utils.migrations.check_database_exists')
    @patch('utils.migrations.logger')
    def test_create_initial_migration_no_database(self, mock_logger, mock_check_db, mock_script_dir_class, mock_get_config):
        """Test create_initial_migration when no database exists."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_script_dir = Mock()
        mock_script_dir.walk_revisions.return_value = []  # No existing migrations
        mock_script_dir_class.from_config.return_value = mock_script_dir
        
        mock_check_db.return_value = False  # No database
        
        result = create_initial_migration_if_needed()
        
        assert result is True
        mock_logger.debug.assert_called()
        assert "No existing database found" in str(mock_logger.debug.call_args)

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.ScriptDirectory')
    @patch('utils.migrations.check_database_exists')
    @patch('utils.migrations.get_database_url')
    @patch('utils.migrations.command')
    @patch('utils.migrations.logger')
    def test_create_initial_migration_success(self, mock_logger, mock_command, mock_get_db_url,
                                            mock_check_db, mock_script_dir_class, mock_get_config):
        """Test successful initial migration creation."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_script_dir = Mock()
        mock_script_dir.walk_revisions.return_value = []  # No existing migrations
        mock_script_dir_class.from_config.return_value = mock_script_dir
        
        mock_check_db.return_value = True  # Database exists
        mock_get_db_url.return_value = "sqlite:///test.db"
        
        result = create_initial_migration_if_needed()
        
        assert result is True
        mock_config.set_main_option.assert_called_once_with("sqlalchemy.url", "sqlite:///test.db")
        mock_command.revision.assert_called_once()
        mock_command.stamp.assert_called_once_with(mock_config, "head")
        mock_logger.info.assert_called()

    @patch('utils.migrations.get_alembic_config')
    @patch('utils.migrations.logger')
    def test_create_initial_migration_exception(self, mock_logger, mock_get_config):
        """Test create_initial_migration when exception occurs."""
        mock_get_config.side_effect = Exception("Creation failed")
        
        result = create_initial_migration_if_needed()
        
        assert result is False
        mock_logger.error.assert_called()
        assert "Failed to create initial migration" in str(mock_logger.error.call_args)


class TestInitializeDatabaseWithMigrations:
    """Test suite for initialize_database_with_migrations function."""

    @patch.dict(os.environ, {"AUTO_MIGRATE": "false"})
    @patch('utils.migrations.logger')
    def test_initialize_database_auto_migrate_disabled(self, mock_logger):
        """Test initialize_database when auto-migrate is disabled."""
        result = initialize_database_with_migrations()
        
        assert result is True
        mock_logger.info.assert_called()
        assert "Automated migrations disabled" in str(mock_logger.info.call_args)

    @patch.dict(os.environ, {"AUTO_MIGRATE": "true"})
    @patch('utils.migrations.create_initial_migration_if_needed')
    @patch('utils.migrations.run_migrations')
    @patch('utils.migrations.logger')
    def test_initialize_database_success(self, mock_logger, mock_run_migrations, mock_create_initial):
        """Test successful database initialization."""
        mock_create_initial.return_value = True
        mock_run_migrations.return_value = True
        
        result = initialize_database_with_migrations()
        
        assert result is True
        mock_create_initial.assert_called_once()
        mock_run_migrations.assert_called_once()
        mock_logger.info.assert_called()

    @patch.dict(os.environ, {"AUTO_MIGRATE": "true"})
    @patch('utils.migrations.create_initial_migration_if_needed')
    @patch('utils.migrations.logger')
    def test_initialize_database_initial_migration_fails(self, mock_logger, mock_create_initial):
        """Test database initialization when initial migration fails."""
        mock_create_initial.return_value = False
        
        result = initialize_database_with_migrations()
        
        assert result is False
        mock_create_initial.assert_called_once()

    @patch.dict(os.environ, {"AUTO_MIGRATE": "true"})
    @patch('utils.migrations.create_initial_migration_if_needed')
    @patch('utils.migrations.run_migrations')
    @patch('utils.migrations.logger')
    def test_initialize_database_run_migrations_fails(self, mock_logger, mock_run_migrations, mock_create_initial):
        """Test database initialization when run_migrations fails."""
        mock_create_initial.return_value = True
        mock_run_migrations.return_value = False
        
        result = initialize_database_with_migrations()
        
        assert result is False
        mock_create_initial.assert_called_once()
        mock_run_migrations.assert_called_once()

    @patch.dict(os.environ, {"AUTO_MIGRATE": "true"})
    @patch('utils.migrations.create_initial_migration_if_needed')
    @patch('utils.migrations.logger')
    def test_initialize_database_exception(self, mock_logger, mock_create_initial):
        """Test database initialization when exception occurs."""
        mock_create_initial.side_effect = Exception("Initialization failed")
        
        result = initialize_database_with_migrations()
        
        assert result is False
        mock_logger.error.assert_called()
        assert "Database initialization failed" in str(mock_logger.error.call_args)

    def test_initialize_database_auto_migrate_variations(self):
        """Test various AUTO_MIGRATE environment variable values."""
        # Test truthy values
        truthy_values = ["true", "1", "yes", "on", "TRUE", "Yes", "ON"]
        
        for value in truthy_values:
            with patch.dict(os.environ, {"AUTO_MIGRATE": value}):
                with patch('utils.migrations.create_initial_migration_if_needed', return_value=True):
                    with patch('utils.migrations.run_migrations', return_value=True):
                        result = initialize_database_with_migrations()
                        assert result is True
        
        # Test falsy values
        falsy_values = ["false", "0", "no", "off", "", "FALSE", "No", "OFF"]
        
        for value in falsy_values:
            with patch.dict(os.environ, {"AUTO_MIGRATE": value}):
                with patch('utils.migrations.logger') as mock_logger:
                    result = initialize_database_with_migrations()
                    assert result is True
                    mock_logger.info.assert_called()
                    assert "Automated migrations disabled" in str(mock_logger.info.call_args)


class TestMigrationsIntegration:
    """Integration tests for migration utilities working together."""

    def test_migration_workflow_no_database(self):
        """Test complete migration workflow when no database exists."""
        with patch('utils.migrations.get_alembic_config') as mock_get_config:
            with patch('utils.migrations.ScriptDirectory') as mock_script_dir_class:
                with patch('utils.migrations.check_database_exists', return_value=False):
                    with patch('utils.migrations.run_migrations', return_value=True):
                        mock_config = Mock()
                        mock_get_config.return_value = mock_config
                        
                        mock_script_dir = Mock()
                        mock_script_dir.walk_revisions.return_value = []
                        mock_script_dir_class.from_config.return_value = mock_script_dir
                        
                        with patch.dict(os.environ, {"AUTO_MIGRATE": "true"}):
                            result = initialize_database_with_migrations()
                        
                        assert result is True

    def test_migration_workflow_existing_migrations(self):
        """Test complete migration workflow when migrations exist."""
        with patch('utils.migrations.get_alembic_config') as mock_get_config:
            with patch('utils.migrations.ScriptDirectory') as mock_script_dir_class:
                with patch('utils.migrations.run_migrations', return_value=True):
                    mock_config = Mock()
                    mock_get_config.return_value = mock_config
                    
                    mock_script_dir = Mock()
                    mock_script_dir.walk_revisions.return_value = [Mock()]  # Existing migrations
                    mock_script_dir_class.from_config.return_value = mock_script_dir
                    
                    with patch.dict(os.environ, {"AUTO_MIGRATE": "true"}):
                        result = initialize_database_with_migrations()
                    
                    assert result is True

    def test_error_propagation_through_migration_chain(self):
        """Test that errors propagate correctly through migration chain."""
        with patch('utils.migrations.get_alembic_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")
            
            with patch.dict(os.environ, {"AUTO_MIGRATE": "true"}):
                result = initialize_database_with_migrations()
            
            assert result is False

    def test_migration_state_consistency(self):
        """Test migration state consistency across function calls."""
        with patch('utils.migrations.get_alembic_config') as mock_get_config:
            with patch('utils.migrations.get_database_url', return_value="sqlite:///test.db"):
                with patch('utils.migrations.get_current_revision', return_value="abc123"):
                    with patch('utils.migrations.get_head_revision', return_value="abc123"):
                        mock_config = Mock()
                        mock_get_config.return_value = mock_config
                        
                        # Should not attempt upgrade when revisions match
                        result = run_migrations()
                        
                        assert result is True
                        # Verify config was still prepared
                        mock_config.set_main_option.assert_called_once_with("sqlalchemy.url", "sqlite:///test.db")