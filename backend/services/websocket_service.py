"""
WebSocket service for real-time updates
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from fastapi import WebSocket
from pydantic import BaseModel, HttpUrl
import logging

logger = logging.getLogger(__name__)


def serialize_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Pydantic types to JSON-serializable types"""
    serialized: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, HttpUrl):
            serialized[key] = str(value)
        elif isinstance(value, (datetime, date)):
            serialized[key] = value.isoformat()
        elif isinstance(value, BaseModel):
            serialized[key] = serialize_for_json(value.model_dump())
        elif isinstance(value, list):
            serialized[key] = [
                serialize_for_json(item.model_dump()) if isinstance(item, BaseModel)
                else serialize_value(item)
                for item in value
            ]
        elif isinstance(value, dict):
            serialized[key] = serialize_for_json(value)
        else:
            serialized[key] = serialize_value(value)
    return serialized


def serialize_value(value: Any) -> Any:
    """Serialize individual values"""
    if isinstance(value, HttpUrl):
        return str(value)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, BaseModel):
        return serialize_for_json(value.model_dump())
    elif isinstance(value, dict):
        return serialize_for_json(value)
    elif isinstance(value, list):
        return [serialize_value(item) for item in value]
    else:
        return value


class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self) -> None:
        # Store active connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def _send_safe(self, connection: WebSocket, message_str: str) -> Optional[Exception]:
        """Safely send message to a single connection, returning exception if failed"""
        try:
            await connection.send_text(message_str)
            return None
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            return e

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        
        # Send to all connections in parallel using asyncio.gather
        tasks = [self._send_safe(conn, message_str) for conn in self.active_connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Remove failed connections based on results
        disconnected = []
        for i, result in enumerate(results):
            if isinstance(result, Exception) or result is not None:
                disconnected.append(self.active_connections[i])
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_product_created(self, product_data: Dict[str, Any]) -> None:
        """Broadcast when a new product is created"""
        serialized_data = serialize_for_json(product_data)
        message = {
            "type": "product_created",
            "data": serialized_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted new product creation: ID {serialized_data.get('id')}")

    async def broadcast_product_updated(self, product_data: Dict[str, Any]) -> None:
        """Broadcast when a product is updated"""
        serialized_data = serialize_for_json(product_data)
        message = {
            "type": "product_updated",
            "data": serialized_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted product update: ID {serialized_data.get('id')}")

    async def broadcast_product_deleted(self, product_id: int) -> None:
        """Broadcast when a product is deleted"""
        message = {
            "type": "product_deleted",
            "data": {"id": product_id},
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted product deletion: ID {product_id}")

    async def broadcast_scraping_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Broadcast scraping status updates"""
        message = {
            "type": "scraping_status",
            "data": {
                "status": status,
                "details": details or {}
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted scraping status: {status}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
