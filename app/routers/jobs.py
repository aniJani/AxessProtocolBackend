# File: app/routers/jobs.py

import logging
from fastapi import APIRouter, HTTPException

# Import your shared components
from app.clients.aptos import aptos_client
from app.config import get_settings
from app.models.schemas import Job

# --- Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
router = APIRouter(prefix="/api/v1", tags=["jobs"])
SET = get_settings()


def _parse_raw_job(raw_job: dict) -> Job:
    """A helper function to transform raw on-chain job data into our Pydantic model."""
    # The on-chain data uses string representations for u64, so we cast them to int
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
    Gets the current state of an active or completed job by its ID
    by calling the on-chain view function `get_job`.
    """
    logging.info(f"Fetching details for Job ID: {job_id}")
    try:
        # This payload calls the `get_job` view function you added to escrow.move
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::escrow::get_job",
            "type_arguments": [],
            "arguments": [str(job_id)],  # Arguments to view functions must be strings
        }

        # The view function returns a list containing one element: the Job struct
        raw_job_payload = await aptos_client.view(payload)
        logging.info(f"Raw job payload from chain: {raw_job_payload}")

        raw_job = raw_job_payload[0]

        return _parse_raw_job(raw_job)

    except Exception as e:
        # The most common error is that the job ID doesn't exist, which will cause a 404
        logging.error(f"Failed to get job {job_id}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
