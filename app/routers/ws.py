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
            status = message.get("status")
            job_id = message.get("job_id")

            if status == "session_ready":
                if job_id is not None:
                    SESSION_CACHE[job_id] = {
                        "public_url": message.get("public_url"),
                        "token": message.get("token"),
                        "stats": None # Initialize stats as null
                    }
                    logging.info(f"Stored secure session details for job {job_id}")
            
            # --- NEW: Handle stats updates ---
            elif status == "stats_update":
                if job_id is not None and job_id in SESSION_CACHE:
                    # Update the stats for the existing session
                    SESSION_CACHE[job_id]["stats"] = message.get("stats")

    except WebSocketDisconnect:
        connection_manager.disconnect(host_address)