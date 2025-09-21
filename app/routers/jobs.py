import logging
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Shared components
from app.clients.aptos import aptos_client
from app.config import get_settings
from app.models.schemas import Job
from app.websockets import connection_manager

# --- Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
router = APIRouter(prefix="/api/v1", tags=["jobs"])
SET = get_settings()

# In-memory cache populated by the WebSocket layer when the host agent reports
# {"status": "session_ready", "job_id": ..., "public_url": ..., "token": ...}
# The WS layer should import this SESSION_CACHE and mutate it directly.
SESSION_CACHE = {}  # { job_id(int): { public_url, token, stats?, _billing_meta? } }


def _parse_raw_job(raw_job: dict) -> Job:
    """
    Transform raw on-chain job data (from view function) into our Pydantic model.
    """
    return Job(
        job_id=int(raw_job["job_id"]),
        renter_address=raw_job["renter_address"],
        host_address=raw_job["host_address"],
        listing_id=int(raw_job["listing_id"]),
        start_time=int(raw_job["start_time"]),
        max_end_time=int(raw_job["max_end_time"]),
        total_escrow_amount=int(raw_job["total_escrow_amount"]),
        claimed_amount=int(raw_job["claimed_amount"]),
        is_active=raw_job["is_active"],
    )


async def _fetch_job(job_id: int) -> Job:
    """
    Thin helper around the Aptos view to get a job and parse it.
    """
    payload = {
        "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::escrow::get_job",
        "type_arguments": [],
        "arguments": [str(job_id)],
    }
    raw_job_payload = await aptos_client.view(payload)
    if not raw_job_payload:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    return _parse_raw_job(raw_job_payload[0])


def _cache_key(job_id: int):
    """
    Normalize how we access the cache. Prefer int keys; also check str fallback.
    """
    return job_id


def _get_cached(job_id: int):
    """
    Get details from SESSION_CACHE robustly (int or str key).
    """
    return SESSION_CACHE.get(job_id) or SESSION_CACHE.get(str(job_id))


def _set_cached(job_id: int, details: dict):
    """
    Set details using normalized int key (WS layer should ideally do this too).
    """
    SESSION_CACHE[_cache_key(job_id)] = details


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_details(job_id: int):
    """
    Get the current state of an active or completed job by its ID.
    """
    logging.info(f"Fetching details for Job ID: {job_id}")
    try:
        return await _fetch_job(job_id)
    except HTTPException:
        raise
    except Exception:
        logging.error(f"Failed to get job {job_id}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")


@router.post("/jobs/{job_id}/start", status_code=202)
async def start_gpu_session(job_id: int):
    """
    Tell the connected host agent (via WebSocket) to start a session for this job.
    Returns 202 immediately; the client should poll /jobs/{job_id}/session for readiness.

    Idempotency: if the session is already ready in cache, respond accordingly.
    """
    logging.info(f"Received request to START job {job_id}.")
    try:
        # If we already have a ready session, don't spam the agent again.
        existing = _get_cached(job_id)
        if existing:
            logging.info(f"[start] Session already ready for job {job_id}.")
            return JSONResponse(
                status_code=200,
                content={"status": "already_running", **existing},
                headers={"Cache-Control": "no-store"},
            )

        job_details = await _fetch_job(job_id)
        host_address = job_details.host_address

        command = {"action": "start_session", "job_id": job_id}
        await connection_manager.send_to_host(command, host_address)

        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "message": f"Start command sent to host for job {job_id}.",
            },
            headers={"Retry-After": "3", "Cache-Control": "no-store"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        # bubble up 404s from get_job_details/_fetch_job
        raise
    except Exception:
        logging.error(f"Failed to issue start command for job {job_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to issue start command.")


@router.post("/jobs/{job_id}/stop", status_code=202)
async def stop_gpu_session(job_id: int):
    """
    Tell the connected host agent (via WebSocket) to stop a session for this job.
    Also clears any cached session details.
    """
    logging.info(f"Received request to STOP job {job_id}.")
    try:
        job_details = await _fetch_job(job_id)
        host_address = job_details.host_address

        command = {"action": "stop_session", "job_id": job_id}
        await connection_manager.send_to_host(command, host_address)

        if _get_cached(job_id):
            details = SESSION_CACHE.pop(_cache_key(job_id), None)
            token = details.get("token") if isinstance(details, dict) else None
            if token:
                logging.info(
                    f"[stop] Removed session cache for job {job_id} (token: {token})"
                )
            else:
                logging.info(f"[stop] Removed session cache for job {job_id}")

        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "message": f"Stop command sent to host for job {job_id}.",
            },
            headers={"Retry-After": "1", "Cache-Control": "no-store"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=f"Host for job {job_id} is not connected. {e}"
        )
    except HTTPException:
        raise
    except Exception:
        logging.error(f"Failed to issue stop command for job {job_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to issue stop command.")


@router.get("/jobs/{job_id}/session")
async def get_session_details(job_id: int):
    """
    Returns session details once the host agent has reported them via WebSocket.
    Before it's ready, respond with 202 to avoid noisy 404s and guide client backoff.

    When ready, also include live billing fields expected by the frontend:
      - price_per_second (octas/s)
      - uptime_seconds
      - current_cost_octas
    We compute these once per job and cache metadata to avoid repeated chain calls.
    """
    details = _get_cached(job_id)
    if not details:
        return JSONResponse(
            status_code=202,
            content={"status": "pending", "message": "Session is initializing."},
            headers={"Retry-After": "3", "Cache-Control": "no-store"},
        )

    # Ensure we have a billing meta block cached; if not, fetch once and cache it.
    # _billing_meta = { start_time, max_end_time, total_escrow_amount, price_per_second }
    meta = details.get("_billing_meta")
    if not meta:
        try:
            job = await _fetch_job(job_id)
        except HTTPException:
            # If job is gone on-chain but we still have a session cached,
            # treat as pending to let the client re-try/refresh gracefully.
            return JSONResponse(
                status_code=202,
                content={"status": "pending", "message": "Session verifying..."},
                headers={"Retry-After": "3", "Cache-Control": "no-store"},
            )

        duration = max(0, job.max_end_time - job.start_time)
        price_per_second = (job.total_escrow_amount // duration) if duration > 0 else 0

        meta = {
            "start_time": job.start_time,
            "max_end_time": job.max_end_time,
            "total_escrow_amount": job.total_escrow_amount,
            "price_per_second": price_per_second,
        }
        details["_billing_meta"] = meta
        _set_cached(job_id, details)

    # Compute live numbers without extra chain calls
    now = int(time.time())
    start_time = int(meta["start_time"])
    max_end_time = int(meta["max_end_time"])
    total_escrow_amount = int(meta["total_escrow_amount"])
    price_per_second = int(meta["price_per_second"])

    claim_timestamp = min(max(now, start_time), max_end_time)
    uptime_seconds = max(0, claim_timestamp - start_time)
    current_cost_octas = min(total_escrow_amount, uptime_seconds * price_per_second)

    # Optional: log the token for debugging visibility
    token = details.get("token")
    if token:
        logging.info(f"[session] Job {job_id} is ready (token: {token})")

    payload = {
        "status": "ready",
        "public_url": details.get("public_url"),
        "token": token,
        "stats": details.get("stats") or None,  # may be updated by WS 'stats_update'
        "price_per_second": price_per_second,
        "uptime_seconds": uptime_seconds,
        "current_cost_octas": current_cost_octas,
    }

    return JSONResponse(
        status_code=200, content=payload, headers={"Cache-Control": "no-store"}
    )
