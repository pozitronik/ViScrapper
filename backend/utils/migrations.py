"""
Automatic migration utilities for VIParser application.
Handles running Alembic migrations on application startup.
"""

import os
from pathlib import Path
from typing import Optional
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from utils.logger import get_logger

logger = get_logger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Get the backend directory (where alembic.ini is located)
    backend_dir = Path(__file__).parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    
    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic configuration not found at {alembic_ini_path}")
    
    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini_path))
    
    # Set the script location to be relative to the backend directory
    script_location = backend_dir / "alembic"
    alembic_cfg.set_main_option("script_location", str(script_location))
    
    return alembic_cfg


def get_database_url() -> str:
    """Get database URL from environment or config."""
    # Try environment variable first
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Fallback to alembic.ini configuration
    alembic_cfg = get_alembic_config()
    config_url = alembic_cfg.get_main_option("sqlalchemy.url")
    if config_url:
        return config_url

    # Final fallback to default SQLite database
    return "sqlite:///./viparser.db"


def check_database_exists() -> bool:
    """Check if database exists and has tables."""
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        
        # Check if database exists and has tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        engine.dispose()
        return len(tables) > 0
        
    except Exception as e:
        logger.warning(f"Could not check database existence: {e}")
        return False


def get_current_revision() -> Optional[str]:
    """Get current database revision."""
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
        engine.dispose()
        return current_rev
        
    except Exception as e:
        logger.warning(f"Could not get current revision: {e}")
        return None


def get_head_revision() -> Optional[str]:
    """Get the latest migration revision."""
    try:
        alembic_cfg = get_alembic_config()
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        return script_dir.get_current_head()
        
    except Exception as e:
        logger.error(f"Could not get head revision: {e}")
        return None


def run_migrations() -> bool:
    """
    Run Alembic migrations to upgrade database to latest version.
    
    Returns:
        bool: True if migrations ran successfully, False otherwise
    """
    try:
        logger.info("Starting automatic database migration...")
        
        # Get Alembic configuration
        alembic_cfg = get_alembic_config()
        
        # Set the database URL in the config
        db_url = get_database_url()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Check current state
        current_rev = get_current_revision()
        head_rev = get_head_revision()
        
        if current_rev is None:
            logger.info("No migration history found. Running initial migration...")
        elif current_rev == head_rev:
            logger.info(f"Database is already up to date (revision: {current_rev})")
            return True
        else:
            logger.info(f"Upgrading database from {current_rev} to {head_rev}")
        
        # Run the upgrade
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def create_initial_migration_if_needed() -> bool:
    """
    Create initial migration if none exist and we have an existing database.
    This handles the case where someone has been using create_all() before migrations.
    """
    try:
        alembic_cfg = get_alembic_config()
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        # Check if we have any migrations
        revisions = list(script_dir.walk_revisions())
        if len(revisions) > 0:
            logger.debug("Migrations already exist, skipping initial migration creation")
            return True
        
        # Check if database exists with tables
        if not check_database_exists():
            logger.debug("No existing database found, will create from migrations")
            return True
        
        logger.info("Existing database found without migration history. Creating initial migration...")
        
        # Set the database URL
        db_url = get_database_url()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Create initial migration
        command.revision(
            alembic_cfg,
            message="Initial migration from existing schema",
            autogenerate=True
        )
        
        # Stamp the database with the new revision (without running it)
        command.stamp(alembic_cfg, "head")
        
        logger.info("Initial migration created and database stamped")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create initial migration: {e}")
        return False


def initialize_database_with_migrations() -> bool:
    """
    Initialize database using Alembic migrations instead of create_all().
    
    This function:
    1. Checks if migrations exist
    2. Creates initial migration if needed (for existing databases)
    3. Runs migrations to bring database up to latest version
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    # Check if automated migrations are enabled
    auto_migrate = os.getenv("AUTO_MIGRATE", "false").lower() in ("true", "1", "yes", "on")
    
    if not auto_migrate:
        logger.info("Automated migrations disabled (AUTO_MIGRATE=false). Manual migration expected.")
        return True
    
    try:
        logger.info("Initializing database with Alembic migrations...")
        
        # First, handle case where database exists but no migrations
        if not create_initial_migration_if_needed():
            return False
        
        # Run migrations to latest version
        if not run_migrations():
            return False
        
        logger.info("Database initialization with migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False