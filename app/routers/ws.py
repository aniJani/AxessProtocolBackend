import logging
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets import connection_manager
from .jobs import SESSION_CACHE, get_job_details  # reuse the same shared dict

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/{host_address}")
async def websocket_endpoint(websocket: WebSocket, host_address: str):
    # Register this host's WebSocket
    await connection_manager.connect(websocket, host_address)
    try:
        while True:
            # Receive one message at a time
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logging.warning(f"[WS] Non-JSON from {host_address}: {raw!r}")
                continue

            status = message.get("status")
            job_id_raw = message.get("job_id")

            # Normalize job_id (it can be 0; only skip if truly missing/invalid)
            try:
                job_id = int(job_id_raw)
            except (TypeError, ValueError):
                logging.warning(f"[WS] Missing/invalid job_id in message: {message}")
                continue

            logging.info(f"[WS] {host_address} -> status={status} job_id={job_id}")

            if status == "session_ready":
                public_url = message.get("public_url")
                token = message.get("token")

                # DEV LOG (contains token). Remove or redact in production.
                logging.info(
                    f"[WS] session_ready: job={job_id} url={public_url} token={token}"
                )

                if not public_url or not token:
                    logging.warning(
                        f"[WS] session_ready missing url/token for job {job_id}: {message}"
                    )
                    continue

                try:
                    # Validate job exists (and warm caches if you have any)
                    _ = await get_job_details(job_id)

                    # Store minimal session info; let HTTP layer compute billing.
                    SESSION_CACHE[job_id] = {
                        "public_url": public_url,
                        "token": token,
                        "stats": None,
                        # Clear any stale billing meta so jobs.py recomputes once.
                        "_billing_meta": None,
                        "session_start_time": int(time.time()),
                        "error": None,
                    }
                    logging.info(f"[WS] Cached session for job {job_id}")
                except Exception as e:
                    logging.error(
                        f"[WS] Failed to cache session for job {job_id}: {e}",
                        exc_info=True,
                    )

            elif status == "stats_update":
                session = SESSION_CACHE.get(job_id)
                if not session:
                    logging.debug(
                        f"[WS] Stats for unknown job {job_id}; waiting for session_ready."
                    )
                    continue

                # Only update stats; billing is computed in GET /jobs/{id}/session
                session["stats"] = message.get("stats")

            elif status == "session_stopped":
                if job_id in SESSION_CACHE:
                    SESSION_CACHE.pop(job_id, None)
                    logging.info(f"[WS] Removed session cache for job {job_id}")

            elif status == "session_error":
                err = message.get("message") or "host reported session_error"
                logging.warning(f"[WS] session_error for job {job_id}: {err}")
                SESSION_CACHE[job_id] = {
                    "public_url": None,
                    "token": None,
                    "stats": None,
                    "_billing_meta": None,
                    "session_start_time": None,
                    "error": err,
                }

            else:
                logging.debug(f"[WS] Ignoring message for job {job_id}: {message}")

    except WebSocketDisconnect:
        connection_manager.disconnect(host_address)
        logging.info(f"[WS] Disconnected: {host_address}")
