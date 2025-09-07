import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets import connection_manager
import json
from .jobs import SESSION_CACHE

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/{host_address}")
async def websocket_endpoint(websocket: WebSocket, host_address: str):
    await connection_manager.connect(websocket, host_address)
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message from {host_address}: {data}")
            
            message = json.loads(data)
            if message.get("status") == "session_ready":
                job_id = message.get("job_id")
                # --- UPDATED: Store the public_url instead of IP/port ---
                SESSION_CACHE[job_id] = {
                    "public_url": message.get("public_url"),
                    "token": message.get("token")
                }
                logging.info(f"Stored secure session details for job {job_id}")

    except WebSocketDisconnect:
        connection_manager.disconnect(host_address)