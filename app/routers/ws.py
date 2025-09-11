import logging
import json
import time # <-- Add the time module
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets import connection_manager
from .jobs import SESSION_CACHE, get_job_details # <-- Import get_job_details

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/{host_address}")
async def websocket_endpoint(websocket: WebSocket, host_address: str):
    await connection_manager.connect(websocket, host_address)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            status = message.get("status")
            job_id = message.get("job_id")

            if not job_id:
                continue

            # --- UPDATED LOGIC for session_ready ---
            if status == "session_ready":
                try:
                    # Fetch the job's on-chain details ONCE when the session starts
                    job_details = await get_job_details(job_id)
                    price_per_second = job_details.price_per_second
                    
                    SESSION_CACHE[job_id] = {
                        "public_url": message.get("public_url"),
                        "token": message.get("token"),
                        "stats": None,
                        # --- NEW: Add billing and time fields ---
                        "price_per_second": price_per_second,
                        "session_start_time": time.time(), # Record start time as a Unix timestamp
                        "uptime_seconds": 0,
                        "current_cost_octas": 0,
                    }
                    logging.info(f"Stored initial session and billing details for job {job_id}")
                except Exception as e:
                    logging.error(f"Could not fetch job details for {job_id} on session start: {e}")

            # --- UPDATED LOGIC for stats_update ---
            elif status == "stats_update":
                if job_id in SESSION_CACHE:
                    session = SESSION_CACHE[job_id]
                    
                    # Calculate uptime and current cost
                    uptime = time.time() - session.get("session_start_time", time.time())
                    price = session.get("price_per_second", 0)
                    cost = int(uptime * price)

                    # Update the cache with all new information
                    session["stats"] = message.get("stats")
                    session["uptime_seconds"] = int(uptime)
                    session["current_cost_octas"] = cost

    except WebSocketDisconnect:
        connection_manager.disconnect(host_address)