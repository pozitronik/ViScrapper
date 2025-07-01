"""
Delete mode enumeration for soft and hard delete operations
"""
from enum import Enum


class DeleteMode(str, Enum):
    """Enumeration for different delete modes"""
    SOFT = "soft"  # Default: Mark as deleted but keep in database
    HARD = "hard"  # Permanently remove from database and filesystem

    def __str__(self) -> str:
        return self.value
