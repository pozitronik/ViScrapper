"""
Unit tests for delete_mode enum.

This module contains comprehensive tests for the DeleteMode enumeration,
covering all enum values, string representation, and edge cases.
"""

import pytest
from enum import Enum

from enums.delete_mode import DeleteMode


class TestDeleteMode:
    """Test suite for DeleteMode enumeration."""

    def test_delete_mode_is_enum(self):
        """Test that DeleteMode is an enumeration class."""
        assert issubclass(DeleteMode, Enum)
        assert issubclass(DeleteMode, str)

    def test_delete_mode_values(self):
        """Test that DeleteMode has the expected enum values."""
        assert DeleteMode.SOFT == "soft"
        assert DeleteMode.HARD == "hard"

    def test_delete_mode_members(self):
        """Test all enum members are present."""
        expected_members = {"SOFT", "HARD"}
        actual_members = set(DeleteMode.__members__.keys())
        assert actual_members == expected_members

    def test_delete_mode_value_types(self):
        """Test that enum values are strings."""
        for member in DeleteMode:
            assert isinstance(member.value, str)

    def test_string_representation(self):
        """Test string representation via __str__ method."""
        assert str(DeleteMode.SOFT) == "soft"
        assert str(DeleteMode.HARD) == "hard"

    def test_enum_iteration(self):
        """Test iteration over enum members."""
        values = [member.value for member in DeleteMode]
        assert "soft" in values
        assert "hard" in values
        assert len(values) == 2

    def test_enum_membership(self):
        """Test membership testing of enum values."""
        assert "soft" in [member.value for member in DeleteMode]
        assert "hard" in [member.value for member in DeleteMode]
        assert "invalid" not in [member.value for member in DeleteMode]

    def test_enum_comparison(self):
        """Test comparison operations between enum members."""
        # Test equality
        assert DeleteMode.SOFT == DeleteMode.SOFT
        assert DeleteMode.HARD == DeleteMode.HARD
        assert DeleteMode.SOFT != DeleteMode.HARD

        # Test equality with string values
        assert DeleteMode.SOFT == "soft"
        assert DeleteMode.HARD == "hard"
        assert DeleteMode.SOFT != "hard"
        assert DeleteMode.HARD != "soft"

    def test_enum_construction_by_value(self):
        """Test constructing enum instances by value."""
        soft_mode = DeleteMode("soft")
        hard_mode = DeleteMode("hard")
        
        assert soft_mode == DeleteMode.SOFT
        assert hard_mode == DeleteMode.HARD

    def test_enum_construction_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError, match="'invalid' is not a valid DeleteMode"):
            DeleteMode("invalid")

    def test_enum_representation(self):
        """Test the repr representation of enum members."""
        assert repr(DeleteMode.SOFT) == "<DeleteMode.SOFT: 'soft'>"
        assert repr(DeleteMode.HARD) == "<DeleteMode.HARD: 'hard'>"

    def test_enum_name_attribute(self):
        """Test the name attribute of enum members."""
        assert DeleteMode.SOFT.name == "SOFT"
        assert DeleteMode.HARD.name == "HARD"

    def test_enum_value_attribute(self):
        """Test the value attribute of enum members."""
        assert DeleteMode.SOFT.value == "soft"
        assert DeleteMode.HARD.value == "hard"

    def test_enum_hash(self):
        """Test that enum members are hashable."""
        # Should be hashable and usable in sets/dicts
        mode_set = {DeleteMode.SOFT, DeleteMode.HARD}
        assert len(mode_set) == 2

        mode_dict = {DeleteMode.SOFT: "soft_delete", DeleteMode.HARD: "hard_delete"}
        assert mode_dict[DeleteMode.SOFT] == "soft_delete"
        assert mode_dict[DeleteMode.HARD] == "hard_delete"

    def test_enum_boolean_context(self):
        """Test enum members in boolean context."""
        assert bool(DeleteMode.SOFT) is True
        assert bool(DeleteMode.HARD) is True

    def test_enum_str_inheritance(self):
        """Test that DeleteMode inherits from str."""
        assert isinstance(DeleteMode.SOFT, str)
        assert isinstance(DeleteMode.HARD, str)

    def test_enum_case_sensitivity(self):
        """Test case sensitivity of enum values."""
        with pytest.raises(ValueError):
            DeleteMode("SOFT")  # Wrong case
        with pytest.raises(ValueError):
            DeleteMode("Soft")  # Wrong case
        with pytest.raises(ValueError):
            DeleteMode("HARD")  # Wrong case
        with pytest.raises(ValueError):
            DeleteMode("Hard")  # Wrong case

    def test_enum_json_serialization(self):
        """Test JSON serialization behavior."""
        import json
        
        # Test that enum can be JSON serialized as string
        soft_json = json.dumps(DeleteMode.SOFT)
        hard_json = json.dumps(DeleteMode.HARD)
        
        assert soft_json == '"soft"'
        assert hard_json == '"hard"'

    def test_enum_all_members_tested(self):
        """Ensure we've tested all enum members to catch future additions."""
        # This test will fail if new enum members are added without updating tests
        all_members = list(DeleteMode)
        expected_count = 2
        
        assert len(all_members) == expected_count, (
            f"Expected {expected_count} enum members, found {len(all_members)}. "
            f"Update tests when adding new DeleteMode members."
        )

    def test_enum_use_cases(self):
        """Test realistic use cases for the enum."""
        # Test using enum in conditional logic
        def perform_delete(mode: DeleteMode):
            if mode == DeleteMode.SOFT:
                return "soft_delete_performed"
            elif mode == DeleteMode.HARD:
                return "hard_delete_performed"
            else:
                raise ValueError("Invalid delete mode")

        assert perform_delete(DeleteMode.SOFT) == "soft_delete_performed"
        assert perform_delete(DeleteMode.HARD) == "hard_delete_performed"

        # Test using enum in dictionary lookup
        delete_handlers = {
            DeleteMode.SOFT: lambda: "soft_handler",
            DeleteMode.HARD: lambda: "hard_handler"
        }
        
        assert delete_handlers[DeleteMode.SOFT]() == "soft_handler"
        assert delete_handlers[DeleteMode.HARD]() == "hard_handler"

    def test_enum_immutability(self):
        """Test that enum members are immutable."""
        with pytest.raises(AttributeError):
            DeleteMode.SOFT.value = "modified"  # Should not be able to modify

    def test_enum_default_behavior(self):
        """Test which mode might be considered default (SOFT)."""
        # Based on the comment in the enum, SOFT is the default
        # This tests the assumption that SOFT is the preferred default
        modes = list(DeleteMode)
        assert DeleteMode.SOFT in modes
        
        # Test that SOFT comes first (if ordering matters)
        first_mode = next(iter(DeleteMode))
        assert first_mode == DeleteMode.SOFT