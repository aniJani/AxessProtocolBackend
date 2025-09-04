import logging
from fastapi import APIRouter, HTTPException

# Import your shared components
from app.clients.aptos import aptos_client
from app.config import get_settings
from app.models.schemas import Job
from app.websockets import connection_manager

# --- This incorrect line has been removed ---
# from .jobs import get_job_details 

# --- Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
router = APIRouter(prefix="/api/v1", tags=["jobs"])
SET = get_settings()

# A simple in-memory cache for session details.
SESSION_CACHE = {}


def _parse_raw_job(raw_job: dict) -> Job:
    """A helper function to transform raw on-chain job data into our Pydantic model."""
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


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_details(job_id: int):
    """
    Gets the current state of an active or completed job by its ID.
    """
    logging.info(f"Fetching details for Job ID: {job_id}")
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::escrow::get_job",
            "type_arguments": [],
            "arguments": [str(job_id)],
        }
        raw_job_payload = await aptos_client.view(payload)
        raw_job = raw_job_payload[0]
        return _parse_raw_job(raw_job)

    except Exception as e:
        logging.error(f"Failed to get job {job_id}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")


@router.post("/jobs/{job_id}/start", status_code=202)
async def start_gpu_session(job_id: int):
    logging.info(f"Received request to START job {job_id}.")
    try:
        # Since get_job_details is in the same file, we can just call it directly.
        job_details = await get_job_details(job_id)
        host_address = job_details.host_address

        command = {"action": "start_session", "job_id": job_id}
        await connection_manager.send_to_host(command, host_address)
        
        return {"status": "pending", "message": f"Start command sent to host for job {job_id}."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Failed to issue start command for job {job_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to issue start command.")


@router.post("/jobs/{job_id}/stop", status_code=202)
async def stop_gpu_session(job_id: int):
    logging.info(f"Received request to STOP job {job_id}.")
    try:
        # Same here: just call the function directly.
        job_details = await get_job_details(job_id)
        host_address = job_details.host_address

        command = {"action": "stop_session", "job_id": job_id}
        await connection_manager.send_to_host(command, host_address)
        
        if job_id in SESSION_CACHE:
            del SESSION_CACHE[job_id]
            logging.info(f"Removed session details for job {job_id} from cache.")

        return {"status": "pending", "message": f"Stop command sent to host for job {job_id}."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Host for job {job_id} is not connected. {e}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Failed to issue stop command for job {job_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to issue stop command.")


@router.get("/jobs/{job_id}/session", status_code=200)
async def get_session_details(job_id: int):
    """
    Checks the cache for session details (port, token) reported by the host agent.
    """
    details = SESSION_CACHE.get(job_id)
    if not details:
        raise HTTPException(status_code=404, detail="Session not ready or not found.")
    return details