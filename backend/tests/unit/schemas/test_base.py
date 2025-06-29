"""
Comprehensive unit tests for base schemas.

This module contains extensive tests for base Pydantic schemas including
APIResponse, PaginationInfo, and PaginatedResponse classes.
"""

import pytest
from typing import List, Optional
from pydantic import BaseModel, ValidationError

from schemas.base import APIResponse, PaginationInfo, PaginatedResponse


# Test models for generic testing
class SampleItem(BaseModel):
    id: int
    name: str


class TestAPIResponse:
    """Test suite for APIResponse schema."""

    def test_api_response_success_basic(self):
        """Test basic successful API response."""
        response = APIResponse[str](
            success=True,
            data="test data"
        )
        
        assert response.success is True
        assert response.data == "test data"
        assert response.message is None
        assert response.error is None

    def test_api_response_success_with_message(self):
        """Test successful API response with message."""
        response = APIResponse[str](
            success=True,
            message="Operation completed successfully",
            data="test data"
        )
        
        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert response.data == "test data"
        assert response.error is None

    def test_api_response_error_basic(self):
        """Test basic error API response."""
        response = APIResponse[None](
            success=False,
            error="Something went wrong"
        )
        
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.data is None
        assert response.message is None

    def test_api_response_error_with_message(self):
        """Test error API response with message."""
        response = APIResponse[None](
            success=False,
            message="Validation failed",
            error="Invalid input data"
        )
        
        assert response.success is False
        assert response.message == "Validation failed"
        assert response.error == "Invalid input data"
        assert response.data is None

    def test_api_response_with_complex_data(self):
        """Test API response with complex data type."""
        test_item = SampleItem(id=1, name="Test Item")
        response = APIResponse[SampleItem](
            success=True,
            data=test_item
        )
        
        assert response.success is True
        assert response.data == test_item
        assert response.data.id == 1
        assert response.data.name == "Test Item"

    def test_api_response_with_list_data(self):
        """Test API response with list data."""
        test_items = [
            SampleItem(id=1, name="Item 1"),
            SampleItem(id=2, name="Item 2")
        ]
        response = APIResponse[List[SampleItem]](
            success=True,
            data=test_items
        )
        
        assert response.success is True
        assert len(response.data) == 2
        assert response.data[0].id == 1
        assert response.data[1].name == "Item 2"

    def test_api_response_none_data(self):
        """Test API response with None data."""
        response = APIResponse[None](
            success=True,
            message="Operation completed"
        )
        
        assert response.success is True
        assert response.data is None
        assert response.message == "Operation completed"

    def test_api_response_serialization(self):
        """Test API response JSON serialization."""
        response = APIResponse[str](
            success=True,
            message="Success",
            data="test data"
        )
        
        json_data = response.model_dump()
        expected = {
            "success": True,
            "message": "Success",
            "data": "test data",
            "error": None
        }
        
        assert json_data == expected

    def test_api_response_deserialization(self):
        """Test API response JSON deserialization."""
        json_data = {
            "success": False,
            "error": "Error occurred",
            "message": "Failed",
            "data": None
        }
        
        response = APIResponse[None](**json_data)
        
        assert response.success is False
        assert response.error == "Error occurred"
        assert response.message == "Failed"
        assert response.data is None

    def test_api_response_generic_type_validation(self):
        """Test that generic type validation works correctly."""
        # Should work with correct type
        response = APIResponse[int](success=True, data=42)
        assert response.data == 42
        
        # Pydantic should handle type coercion
        response = APIResponse[int](success=True, data="42")
        assert response.data == 42

    def test_api_response_optional_fields(self):
        """Test that all optional fields work correctly."""
        # Minimal response
        response = APIResponse[str](success=True)
        assert response.message is None
        assert response.data is None
        assert response.error is None
        
        # With all fields
        response = APIResponse[str](
            success=True,
            message="Test",
            data="data",
            error="error"  # Unusual but valid
        )
        assert response.message == "Test"
        assert response.data == "data"
        assert response.error == "error"

    def test_api_response_required_field_validation(self):
        """Test that required field validation works."""
        with pytest.raises(ValidationError) as exc_info:
            APIResponse[str]()  # Missing required 'success' field
        
        assert "success" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)


class TestPaginationInfo:
    """Test suite for PaginationInfo schema."""

    def test_pagination_info_basic(self):
        """Test basic pagination info creation."""
        pagination = PaginationInfo(
            total=100,
            skip=20,
            limit=10,
            has_more=True
        )
        
        assert pagination.total == 100
        assert pagination.skip == 20
        assert pagination.limit == 10
        assert pagination.has_more is True

    def test_pagination_info_no_more_items(self):
        """Test pagination info with no more items."""
        pagination = PaginationInfo(
            total=25,
            skip=20,
            limit=10,
            has_more=False
        )
        
        assert pagination.total == 25
        assert pagination.skip == 20
        assert pagination.limit == 10
        assert pagination.has_more is False

    def test_pagination_info_first_page(self):
        """Test pagination info for first page."""
        pagination = PaginationInfo(
            total=100,
            skip=0,
            limit=20,
            has_more=True
        )
        
        assert pagination.total == 100
        assert pagination.skip == 0
        assert pagination.limit == 20
        assert pagination.has_more is True

    def test_pagination_info_last_page(self):
        """Test pagination info for last page."""
        pagination = PaginationInfo(
            total=95,
            skip=80,
            limit=20,
            has_more=False
        )
        
        assert pagination.total == 95
        assert pagination.skip == 80
        assert pagination.limit == 20
        assert pagination.has_more is False

    def test_pagination_info_zero_total(self):
        """Test pagination info with zero total items."""
        pagination = PaginationInfo(
            total=0,
            skip=0,
            limit=10,
            has_more=False
        )
        
        assert pagination.total == 0
        assert pagination.skip == 0
        assert pagination.limit == 10
        assert pagination.has_more is False

    def test_pagination_info_type_validation(self):
        """Test pagination info type validation."""
        # Should accept numeric strings and convert them
        pagination = PaginationInfo(
            total="100",
            skip="20",
            limit="10",
            has_more=True
        )
        
        assert pagination.total == 100
        assert pagination.skip == 20
        assert pagination.limit == 10

    def test_pagination_info_negative_values(self):
        """Test pagination info with negative values."""
        # Pydantic allows negative values by default
        pagination = PaginationInfo(
            total=-1,
            skip=-5,
            limit=-10,
            has_more=False
        )
        
        assert pagination.total == -1
        assert pagination.skip == -5
        assert pagination.limit == -10

    def test_pagination_info_serialization(self):
        """Test pagination info JSON serialization."""
        pagination = PaginationInfo(
            total=50,
            skip=10,
            limit=20,
            has_more=True
        )
        
        json_data = pagination.model_dump()
        expected = {
            "total": 50,
            "skip": 10,
            "limit": 20,
            "has_more": True
        }
        
        assert json_data == expected

    def test_pagination_info_deserialization(self):
        """Test pagination info JSON deserialization."""
        json_data = {
            "total": 75,
            "skip": 30,
            "limit": 15,
            "has_more": False
        }
        
        pagination = PaginationInfo(**json_data)
        
        assert pagination.total == 75
        assert pagination.skip == 30
        assert pagination.limit == 15
        assert pagination.has_more is False

    def test_pagination_info_required_fields(self):
        """Test that all pagination fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationInfo()
        
        error_str = str(exc_info.value)
        assert "total" in error_str
        assert "skip" in error_str
        assert "limit" in error_str
        assert "has_more" in error_str

    def test_pagination_info_boolean_validation(self):
        """Test boolean validation for has_more field."""
        # Should accept boolean values
        pagination = PaginationInfo(total=10, skip=0, limit=5, has_more=True)
        assert pagination.has_more is True
        
        # Should accept truthy/falsy values
        pagination = PaginationInfo(total=10, skip=0, limit=5, has_more=1)
        assert pagination.has_more is True
        
        pagination = PaginationInfo(total=10, skip=0, limit=5, has_more=0)
        assert pagination.has_more is False


class TestPaginatedResponse:
    """Test suite for PaginatedResponse schema."""

    def test_paginated_response_basic(self):
        """Test basic paginated response creation."""
        test_items = [
            SampleItem(id=1, name="Item 1"),
            SampleItem(id=2, name="Item 2")
        ]
        pagination = PaginationInfo(
            total=10,
            skip=0,
            limit=2,
            has_more=True
        )
        
        response = PaginatedResponse[SampleItem](
            success=True,
            data=test_items,
            pagination=pagination
        )
        
        assert response.success is True
        assert len(response.data) == 2
        assert response.data[0].id == 1
        assert response.data[1].name == "Item 2"
        assert response.pagination.total == 10
        assert response.message is None

    def test_paginated_response_with_message(self):
        """Test paginated response with message."""
        response = PaginatedResponse[SampleItem](
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, skip=0, limit=10, has_more=False),
            message="No items found"
        )
        
        assert response.success is True
        assert response.data == []
        assert response.message == "No items found"

    def test_paginated_response_empty_data(self):
        """Test paginated response with empty data."""
        pagination = PaginationInfo(
            total=0,
            skip=0,
            limit=10,
            has_more=False
        )
        
        response = PaginatedResponse[SampleItem](
            success=True,
            data=[],
            pagination=pagination
        )
        
        assert response.success is True
        assert response.data == []
        assert response.pagination.total == 0
        assert response.pagination.has_more is False

    def test_paginated_response_error_case(self):
        """Test paginated response for error cases."""
        pagination = PaginationInfo(
            total=0,
            skip=0,
            limit=10,
            has_more=False
        )
        
        response = PaginatedResponse[SampleItem](
            success=False,
            data=[],
            pagination=pagination,
            message="Failed to retrieve data"
        )
        
        assert response.success is False
        assert response.data == []
        assert response.message == "Failed to retrieve data"

    def test_paginated_response_large_dataset(self):
        """Test paginated response with large dataset simulation."""
        # Simulate page 3 of a large dataset
        test_items = [SampleItem(id=i, name=f"Item {i}") for i in range(21, 31)]
        pagination = PaginationInfo(
            total=1000,
            skip=20,
            limit=10,
            has_more=True
        )
        
        response = PaginatedResponse[SampleItem](
            success=True,
            data=test_items,
            pagination=pagination
        )
        
        assert response.success is True
        assert len(response.data) == 10
        assert response.data[0].id == 21
        assert response.data[-1].id == 30
        assert response.pagination.total == 1000
        assert response.pagination.skip == 20
        assert response.pagination.has_more is True

    def test_paginated_response_string_data(self):
        """Test paginated response with string data."""
        string_data = ["apple", "banana", "cherry"]
        pagination = PaginationInfo(
            total=3,
            skip=0,
            limit=10,
            has_more=False
        )
        
        response = PaginatedResponse[str](
            success=True,
            data=string_data,
            pagination=pagination
        )
        
        assert response.success is True
        assert response.data == ["apple", "banana", "cherry"]
        assert len(response.data) == 3

    def test_paginated_response_serialization(self):
        """Test paginated response JSON serialization."""
        test_items = [SampleItem(id=1, name="Test")]
        pagination = PaginationInfo(total=1, skip=0, limit=10, has_more=False)
        
        response = PaginatedResponse[SampleItem](
            success=True,
            data=test_items,
            pagination=pagination,
            message="Success"
        )
        
        json_data = response.model_dump()
        
        assert json_data["success"] is True
        assert json_data["message"] == "Success"
        assert len(json_data["data"]) == 1
        assert json_data["data"][0]["id"] == 1
        assert json_data["data"][0]["name"] == "Test"
        assert json_data["pagination"]["total"] == 1
        assert json_data["pagination"]["has_more"] is False

    def test_paginated_response_deserialization(self):
        """Test paginated response JSON deserialization."""
        json_data = {
            "success": True,
            "data": [{"id": 1, "name": "Test"}],
            "pagination": {
                "total": 1,
                "skip": 0,
                "limit": 10,
                "has_more": False
            },
            "message": "Retrieved successfully"
        }
        
        response = PaginatedResponse[SampleItem](**json_data)
        
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].id == 1
        assert response.data[0].name == "Test"
        assert response.pagination.total == 1
        assert response.message == "Retrieved successfully"

    def test_paginated_response_generic_type_validation(self):
        """Test generic type validation in paginated response."""
        # Should work with correct types
        int_data = [1, 2, 3]
        pagination = PaginationInfo(total=3, skip=0, limit=10, has_more=False)
        
        response = PaginatedResponse[int](
            success=True,
            data=int_data,
            pagination=pagination
        )
        
        assert response.data == [1, 2, 3]

    def test_paginated_response_required_fields(self):
        """Test required fields validation."""
        # Missing success field
        with pytest.raises(ValidationError) as exc_info:
            PaginatedResponse[str](
                data=[],
                pagination=PaginationInfo(total=0, skip=0, limit=10, has_more=False)
            )
        
        assert "success" in str(exc_info.value)

        # Missing data field
        with pytest.raises(ValidationError) as exc_info:
            PaginatedResponse[str](
                success=True,
                pagination=PaginationInfo(total=0, skip=0, limit=10, has_more=False)
            )
        
        assert "data" in str(exc_info.value)

        # Missing pagination field
        with pytest.raises(ValidationError) as exc_info:
            PaginatedResponse[str](
                success=True,
                data=[]
            )
        
        assert "pagination" in str(exc_info.value)

    def test_paginated_response_data_type_mismatch(self):
        """Test data type mismatch in paginated response."""
        pagination = PaginationInfo(total=1, skip=0, limit=10, has_more=False)
        
        # This should work due to Pydantic's type coercion
        response = PaginatedResponse[int](
            success=True,
            data=["1", "2", "3"],  # Strings that can be converted to ints
            pagination=pagination
        )
        
        assert response.data == [1, 2, 3]


class TestSchemaIntegration:
    """Test integration between different base schemas."""

    def test_api_response_wrapping_paginated_response(self):
        """Test APIResponse wrapping a PaginatedResponse."""
        test_items = [SampleItem(id=1, name="Item 1")]
        pagination = PaginationInfo(total=1, skip=0, limit=10, has_more=False)
        
        paginated = PaginatedResponse[SampleItem](
            success=True,
            data=test_items,
            pagination=pagination
        )
        
        # Wrap paginated response in API response
        api_response = APIResponse[PaginatedResponse[SampleItem]](
            success=True,
            data=paginated,
            message="Data retrieved successfully"
        )
        
        assert api_response.success is True
        assert api_response.message == "Data retrieved successfully"
        assert api_response.data.success is True
        assert len(api_response.data.data) == 1
        assert api_response.data.pagination.total == 1

    def test_api_response_with_pagination_info(self):
        """Test APIResponse containing just PaginationInfo."""
        pagination = PaginationInfo(total=100, skip=50, limit=25, has_more=True)
        
        response = APIResponse[PaginationInfo](
            success=True,
            data=pagination,
            message="Pagination info retrieved"
        )
        
        assert response.success is True
        assert response.data.total == 100
        assert response.data.skip == 50
        assert response.data.has_more is True

    def test_nested_complex_response(self):
        """Test deeply nested response structures."""
        # Create a complex nested structure
        inner_items = [SampleItem(id=i, name=f"Item {i}") for i in range(1, 4)]
        pagination = PaginationInfo(total=3, skip=0, limit=10, has_more=False)
        
        paginated = PaginatedResponse[SampleItem](
            success=True,
            data=inner_items,
            pagination=pagination
        )
        
        # Nest it further
        wrapper = APIResponse[PaginatedResponse[SampleItem]](
            success=True,
            data=paginated
        )
        
        # Test serialization/deserialization of nested structure
        json_data = wrapper.model_dump()
        recreated = APIResponse[PaginatedResponse[SampleItem]](**json_data)
        
        assert recreated.success is True
        assert recreated.data.success is True
        assert len(recreated.data.data) == 3
        assert recreated.data.data[0].id == 1
        assert recreated.data.pagination.total == 3

    def test_error_propagation(self):
        """Test error propagation through nested schemas."""
        # Create an error at the inner level
        pagination = PaginationInfo(total=0, skip=0, limit=10, has_more=False)
        
        paginated = PaginatedResponse[SampleItem](
            success=False,
            data=[],
            pagination=pagination,
            message="No data found"
        )
        
        # Wrap in outer success
        wrapper = APIResponse[PaginatedResponse[SampleItem]](
            success=True,
            data=paginated,
            message="Request processed"
        )
        
        # Outer level successful, inner level failed
        assert wrapper.success is True
        assert wrapper.message == "Request processed"
        assert wrapper.data.success is False
        assert wrapper.data.message == "No data found"

    def test_schema_validation_edge_cases(self):
        """Test edge cases in schema validation."""
        # Test with None data in APIResponse
        response = APIResponse[None](success=True, data=None)
        assert response.data is None
        
        # Test with empty list in PaginatedResponse
        pagination = PaginationInfo(total=0, skip=0, limit=10, has_more=False)
        paginated = PaginatedResponse[SampleItem](
            success=True,
            data=[],
            pagination=pagination
        )
        assert paginated.data == []
        
        # Test serialization/deserialization maintains types
        json_data = paginated.model_dump()
        recreated = PaginatedResponse[SampleItem](**json_data)
        assert recreated.data == []
        assert isinstance(recreated.data, list)