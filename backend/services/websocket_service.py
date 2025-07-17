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


def serialize_value(value: Any) -> Any:
    """Serialize any value to JSON-serializable format"""
    if isinstance(value, HttpUrl):
        return str(value)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, BaseModel):
        return serialize_value(value.model_dump())
    elif isinstance(value, dict):
        return {key: serialize_value(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [serialize_value(item) for item in value]
    else:
        return value


def serialize_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Pydantic types to JSON-serializable types (legacy wrapper)"""
    return serialize_value(data)


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

    async def broadcast_bulk_post_started(self, total_products: int, channels: List[Dict[str, Any]]) -> None:
        """Broadcast bulk post start event"""
        message = {
            "type": "bulk_post_started",
            "total_products": total_products,
            "channels": channels,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted bulk post started: {total_products} products to {len(channels)} channels")

    async def broadcast_bulk_post_product_start(self, product_index: int, product_id: int, 
                                              product_name: str, channels: List[str]) -> None:
        """Broadcast bulk post product start event"""
        message = {
            "type": "bulk_post_product_start",
            "product_index": product_index,
            "product_id": product_id,
            "product_name": product_name,
            "channels": channels,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted bulk post product start: {product_name} ({product_id})")

    async def broadcast_bulk_post_product_success(self, product_index: int, product_id: int,
                                                product_name: str, posts_created: int, channels_posted: int) -> None:
        """Broadcast bulk post product success event"""
        message = {
            "type": "bulk_post_product_success",
            "product_index": product_index,
            "product_id": product_id,
            "product_name": product_name,
            "posts_created": posts_created,
            "channels_posted": channels_posted,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted bulk post product success: {product_name} ({product_id})")

    async def broadcast_bulk_post_product_error(self, product_index: int, product_id: int,
                                              product_name: str, error: str) -> None:
        """Broadcast bulk post product error event"""
        message = {
            "type": "bulk_post_product_error",
            "product_index": product_index,
            "product_id": product_id,
            "product_name": product_name,
            "error": error,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted bulk post product error: {product_name} ({product_id})")

    async def broadcast_bulk_post_completed(self, total_products: int, posted_count: int,
                                          failed_count: int, channels_used: int) -> None:
        """Broadcast bulk post completed event"""
        message = {
            "type": "bulk_post_completed",
            "total_products": total_products,
            "posted_count": posted_count,
            "failed_count": failed_count,
            "channels_used": channels_used,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted bulk post completed: {posted_count} posted, {failed_count} failed")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
