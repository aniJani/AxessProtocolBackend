import logging
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps host_address -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, host_address: str):
        await websocket.accept()
        self.active_connections[host_address] = websocket
        logging.info(f"Host agent connected: {host_address}")

    def disconnect(self, host_address: str):
        if host_address in self.active_connections:
            del self.active_connections[host_address]
            logging.info(f"Host agent disconnected: {host_address}")

    async def send_to_host(self, message: dict, host_address: str):
        if host_address in self.active_connections:
            websocket = self.active_connections[host_address]
            await websocket.send_json(message)
            logging.info(f"Sent command to {host_address}: {message}")
        else:
            logging.warning(f"Attempted to send message to disconnected host: {host_address}")
            raise ValueError("Host is not connected")

# Create a single, globally accessible instance of the manager
connection_manager = ConnectionManager()