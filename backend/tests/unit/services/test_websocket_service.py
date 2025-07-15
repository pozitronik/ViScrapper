"""
Tests for websocket_service.py
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
from pydantic import BaseModel, HttpUrl
from fastapi import WebSocket

from services.websocket_service import (
    WebSocketManager,
    websocket_manager,
    serialize_for_json,
    serialize_value
)


class SampleModel(BaseModel):
    """Test Pydantic model for serialization tests"""
    name: str
    url: HttpUrl
    created_at: datetime


class TestSerializationFunctions:
    """Test serialization helper functions"""
    
    def test_serialize_value_http_url(self):
        """Test serializing HttpUrl"""
        url = HttpUrl("https://example.com")
        result = serialize_value(url)
        assert result == "https://example.com/"
    
    def test_serialize_value_datetime(self):
        """Test serializing datetime"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = serialize_value(dt)
        assert result == "2023-01-01T12:00:00"
    
    def test_serialize_value_date(self):
        """Test serializing date"""
        d = date(2023, 1, 1)
        result = serialize_value(d)
        assert result == "2023-01-01"
    
    def test_serialize_value_base_model(self):
        """Test serializing BaseModel"""
        model = SampleModel(
            name="test",
            url="https://example.com",
            created_at=datetime(2023, 1, 1, 12, 0, 0)
        )
        result = serialize_value(model)
        
        assert result["name"] == "test"
        assert result["url"] == "https://example.com/"
        assert result["created_at"] == "2023-01-01T12:00:00"
    
    def test_serialize_value_dict(self):
        """Test serializing dict"""
        data = {
            "url": HttpUrl("https://example.com"),
            "date": datetime(2023, 1, 1, 12, 0, 0)
        }
        result = serialize_value(data)
        
        assert result["url"] == "https://example.com/"
        assert result["date"] == "2023-01-01T12:00:00"
    
    def test_serialize_value_list(self):
        """Test serializing list"""
        data = [
            HttpUrl("https://example.com"),
            datetime(2023, 1, 1, 12, 0, 0),
            "string_value"
        ]
        result = serialize_value(data)
        
        assert result[0] == "https://example.com/"
        assert result[1] == "2023-01-01T12:00:00"
        assert result[2] == "string_value"
    
    def test_serialize_value_primitive(self):
        """Test serializing primitive values"""
        assert serialize_value("string") == "string"
        assert serialize_value(123) == 123
        assert serialize_value(True) is True
        assert serialize_value(None) is None
    
    def test_serialize_for_json_complex(self):
        """Test serializing complex nested data"""
        model = SampleModel(
            name="test",
            url="https://example.com",
            created_at=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        data = {
            "id": 1,
            "name": "Product",
            "url": HttpUrl("https://product.com"),
            "created_at": datetime(2023, 1, 1, 12, 0, 0),
            "model": model,
            "models": [model],
            "nested": {
                "url": HttpUrl("https://nested.com"),
                "date": date(2023, 1, 1)
            }
        }
        
        result = serialize_for_json(data)
        
        assert result["id"] == 1
        assert result["name"] == "Product"
        assert result["url"] == "https://product.com/"
        assert result["created_at"] == "2023-01-01T12:00:00"
        assert result["model"]["name"] == "test"
        assert result["model"]["url"] == "https://example.com/"
        assert len(result["models"]) == 1
        assert result["models"][0]["name"] == "test"
        assert result["nested"]["url"] == "https://nested.com/"
        assert result["nested"]["date"] == "2023-01-01"
    
    def test_serialize_for_json_list_with_models(self):
        """Test serializing list containing BaseModel instances"""
        model1 = SampleModel(
            name="test1",
            url="https://example1.com",
            created_at=datetime(2023, 1, 1, 12, 0, 0)
        )
        model2 = SampleModel(
            name="test2",
            url="https://example2.com",
            created_at=datetime(2023, 1, 2, 12, 0, 0)
        )
        
        data = {
            "models": [model1, model2, "string_item"]
        }
        
        result = serialize_for_json(data)
        
        assert len(result["models"]) == 3
        assert result["models"][0]["name"] == "test1"
        assert result["models"][1]["name"] == "test2"
        assert result["models"][2] == "string_item"


class TestWebSocketManager:
    """Test WebSocketManager class"""
    
    def test_init(self):
        """Test WebSocketManager initialization"""
        manager = WebSocketManager()
        assert manager.active_connections == []
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting a WebSocket"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        
        await manager.connect(websocket)
        
        websocket.accept.assert_called_once()
        assert websocket in manager.active_connections
        assert len(manager.active_connections) == 1
    
    def test_disconnect(self):
        """Test disconnecting a WebSocket"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        manager.active_connections.append(websocket)
        
        manager.disconnect(websocket)
        
        assert websocket not in manager.active_connections
        assert len(manager.active_connections) == 0
    
    def test_disconnect_not_in_list(self):
        """Test disconnecting a WebSocket not in the list"""
        manager = WebSocketManager()
        websocket1 = Mock(spec=WebSocket)
        websocket2 = Mock(spec=WebSocket)
        manager.active_connections.append(websocket1)
        
        # Try to disconnect websocket2 which is not in the list
        manager.disconnect(websocket2)
        
        # websocket1 should still be in the list
        assert websocket1 in manager.active_connections
        assert len(manager.active_connections) == 1
    
    @pytest.mark.asyncio
    async def test_send_personal_message_success(self):
        """Test sending personal message successfully"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        
        await manager.send_personal_message("test message", websocket)
        
        websocket.send_text.assert_called_once_with("test message")
    
    @pytest.mark.asyncio
    async def test_send_personal_message_exception(self):
        """Test sending personal message with exception"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock(side_effect=Exception("Connection error"))
        manager.active_connections.append(websocket)
        
        await manager.send_personal_message("test message", websocket)
        
        # WebSocket should be disconnected after exception
        assert websocket not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        """Test broadcasting with no active connections"""
        manager = WebSocketManager()
        message = {"type": "test", "data": "test"}
        
        # Should not raise exception
        await manager.broadcast(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_success(self):
        """Test successful broadcasting"""
        manager = WebSocketManager()
        websocket1 = Mock(spec=WebSocket)
        websocket1.send_text = AsyncMock()
        websocket2 = Mock(spec=WebSocket)
        websocket2.send_text = AsyncMock()
        
        manager.active_connections.extend([websocket1, websocket2])
        message = {"type": "test", "data": "test"}
        
        await manager.broadcast(message)
        
        expected_message = json.dumps(message)
        websocket1.send_text.assert_called_once_with(expected_message)
        websocket2.send_text.assert_called_once_with(expected_message)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_failures(self):
        """Test broadcasting with some connection failures"""
        manager = WebSocketManager()
        websocket1 = Mock(spec=WebSocket)
        websocket1.send_text = AsyncMock()
        websocket2 = Mock(spec=WebSocket)
        websocket2.send_text = AsyncMock(side_effect=Exception("Connection error"))
        websocket3 = Mock(spec=WebSocket)
        websocket3.send_text = AsyncMock()
        
        manager.active_connections.extend([websocket1, websocket2, websocket3])
        message = {"type": "test", "data": "test"}
        
        await manager.broadcast(message)
        
        expected_message = json.dumps(message)
        websocket1.send_text.assert_called_once_with(expected_message)
        websocket2.send_text.assert_called_once_with(expected_message)
        websocket3.send_text.assert_called_once_with(expected_message)
        
        # Failed connection should be removed
        assert websocket2 not in manager.active_connections
        assert websocket1 in manager.active_connections
        assert websocket3 in manager.active_connections
        assert len(manager.active_connections) == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_product_created(self):
        """Test broadcasting product created event"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        product_data = {
            "id": 1,
            "name": "Test Product",
            "url": HttpUrl("https://example.com"),
            "created_at": datetime(2023, 1, 1, 12, 0, 0)
        }
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0
            
            await manager.broadcast_product_created(product_data)
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "product_created"
            assert sent_message["data"]["id"] == 1
            assert sent_message["data"]["name"] == "Test Product"
            assert sent_message["data"]["url"] == "https://example.com/"
            assert sent_message["data"]["created_at"] == "2023-01-01T12:00:00"
            assert sent_message["timestamp"] == 1234567890.0
    
    @pytest.mark.asyncio
    async def test_broadcast_product_updated(self):
        """Test broadcasting product updated event"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        product_data = {
            "id": 1,
            "name": "Updated Product",
            "url": HttpUrl("https://updated.com"),
            "updated_at": datetime(2023, 1, 2, 12, 0, 0)
        }
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567891.0
            
            await manager.broadcast_product_updated(product_data)
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "product_updated"
            assert sent_message["data"]["id"] == 1
            assert sent_message["data"]["name"] == "Updated Product"
            assert sent_message["data"]["url"] == "https://updated.com/"
            assert sent_message["data"]["updated_at"] == "2023-01-02T12:00:00"
            assert sent_message["timestamp"] == 1234567891.0
    
    @pytest.mark.asyncio
    async def test_broadcast_product_deleted(self):
        """Test broadcasting product deleted event"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567892.0
            
            await manager.broadcast_product_deleted(42)
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "product_deleted"
            assert sent_message["data"]["id"] == 42
            assert sent_message["timestamp"] == 1234567892.0
    
    @pytest.mark.asyncio
    async def test_broadcast_scraping_status_with_details(self):
        """Test broadcasting scraping status with details"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        details = {
            "progress": 50,
            "total": 100,
            "current_url": "https://example.com/product/1"
        }
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567893.0
            
            await manager.broadcast_scraping_status("in_progress", details)
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "scraping_status"
            assert sent_message["data"]["status"] == "in_progress"
            assert sent_message["data"]["details"]["progress"] == 50
            assert sent_message["data"]["details"]["total"] == 100
            assert sent_message["data"]["details"]["current_url"] == "https://example.com/product/1"
            assert sent_message["timestamp"] == 1234567893.0
    
    @pytest.mark.asyncio
    async def test_broadcast_scraping_status_without_details(self):
        """Test broadcasting scraping status without details"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567894.0
            
            await manager.broadcast_scraping_status("completed")
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "scraping_status"
            assert sent_message["data"]["status"] == "completed"
            assert sent_message["data"]["details"] == {}
            assert sent_message["timestamp"] == 1234567894.0
    
    @pytest.mark.asyncio
    async def test_broadcast_scraping_status_none_details(self):
        """Test broadcasting scraping status with None details"""
        manager = WebSocketManager()
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        manager.active_connections.append(websocket)
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567895.0
            
            await manager.broadcast_scraping_status("failed", None)
            
            # Verify the message was sent
            websocket.send_text.assert_called_once()
            sent_message = json.loads(websocket.send_text.call_args[0][0])
            
            assert sent_message["type"] == "scraping_status"
            assert sent_message["data"]["status"] == "failed"
            assert sent_message["data"]["details"] == {}
            assert sent_message["timestamp"] == 1234567895.0


class TestGlobalWebSocketManager:
    """Test global websocket_manager instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert websocket_manager is not None
        assert isinstance(websocket_manager, WebSocketManager)
    
    def test_global_instance_is_singleton(self):
        """Test global instance behavior"""
        # Import again to ensure it's the same instance
        from services.websocket_service import websocket_manager as manager2
        assert websocket_manager is manager2
    
    @pytest.mark.asyncio
    async def test_global_instance_functionality(self):
        """Test global instance functionality"""
        # Clear any existing connections
        websocket_manager.active_connections.clear()
        
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # Test connecting
        await websocket_manager.connect(websocket)
        assert len(websocket_manager.active_connections) == 1
        
        # Test broadcasting
        message = {"type": "test", "data": "global_test"}
        await websocket_manager.broadcast(message)
        
        expected_message = json.dumps(message)
        websocket.send_text.assert_called_once_with(expected_message)
        
        # Test disconnecting
        websocket_manager.disconnect(websocket)
        assert len(websocket_manager.active_connections) == 0


class TestWebSocketManagerIntegration:
    """Integration tests for WebSocketManager"""
    
    @pytest.mark.asyncio
    async def test_multiple_connections_lifecycle(self):
        """Test lifecycle with multiple connections"""
        manager = WebSocketManager()
        
        # Create multiple mock websockets
        websockets = []
        for i in range(3):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
        
        # Connect all websockets
        for ws in websockets:
            await manager.connect(ws)
        
        assert len(manager.active_connections) == 3
        
        # Broadcast a message
        message = {"type": "test", "data": "integration_test"}
        await manager.broadcast(message)
        
        # Verify all received the message
        expected_message = json.dumps(message)
        for ws in websockets:
            ws.send_text.assert_called_once_with(expected_message)
        
        # Disconnect one websocket
        manager.disconnect(websockets[1])
        assert len(manager.active_connections) == 2
        assert websockets[1] not in manager.active_connections
        
        # Broadcast again
        message2 = {"type": "test2", "data": "integration_test2"}
        await manager.broadcast(message2)
        
        # Verify only remaining connections received the message
        expected_message2 = json.dumps(message2)
        websockets[0].send_text.assert_called_with(expected_message2)
        websockets[2].send_text.assert_called_with(expected_message2)
        
        # websockets[1] should not have received the second message
        assert websockets[1].send_text.call_count == 1  # Only the first message
    
    @pytest.mark.asyncio
    async def test_connection_failure_during_broadcast(self):
        """Test handling connection failures during broadcast"""
        manager = WebSocketManager()
        
        # Create websockets - one will fail
        working_ws = Mock(spec=WebSocket)
        working_ws.accept = AsyncMock()
        working_ws.send_text = AsyncMock()
        
        failing_ws = Mock(spec=WebSocket)
        failing_ws.accept = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        
        # Connect both
        await manager.connect(working_ws)
        await manager.connect(failing_ws)
        assert len(manager.active_connections) == 2
        
        # Broadcast - one should fail and be removed
        message = {"type": "test", "data": "failure_test"}
        await manager.broadcast(message)
        
        # Verify the failing connection was removed
        assert len(manager.active_connections) == 1
        assert working_ws in manager.active_connections
        assert failing_ws not in manager.active_connections
        
        # Verify the working connection still received the message
        expected_message = json.dumps(message)
        working_ws.send_text.assert_called_once_with(expected_message)
        failing_ws.send_text.assert_called_once_with(expected_message)