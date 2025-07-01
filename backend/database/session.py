# Load environment variables from .env file FIRST
import os

from typing import Any
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./viparser.db")


# Database engine configuration with connection pooling


def create_database_engine(database_url: str = DATABASE_URL) -> Engine:
    """Create database engine with appropriate configuration for the database type."""

    if database_url.startswith("sqlite"):
        # SQLite configuration with connection pooling
        engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,  # 30 second timeout for busy database
            },
            poolclass=StaticPool,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL debugging
        )
    else:
        # PostgreSQL/MySQL configuration with connection pooling
        engine = create_engine(
            database_url,
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections when pool is full
            pool_timeout=30,  # Timeout when getting connection from pool
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before use
            echo=False,  # Set to True for SQL debugging
        )

    return engine


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Any:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
