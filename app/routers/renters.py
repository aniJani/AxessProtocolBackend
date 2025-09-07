# This entire file is now much cleaner and more efficient.
import logging
from typing import List
from fastapi import APIRouter
from app.models.schemas import Job # Assuming you have a Pydantic model for Job
from app.clients.aptos import aptos_client
from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["renters"])
SET = get_settings()

@router.get("/renters/{renter_address}/jobs", response_model=List[Job])
async def get_jobs_for_renter(renter_address: str):
    """
    Fetches all jobs for a specific renter using the efficient on-chain view function.
    """
    logging.info(f"Fetching jobs for renter: {renter_address}")
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::escrow::get_jobs_by_renter",
            "type_arguments": [],
            "arguments": [renter_address],
        }
        # The view function returns a list of Job structs
        jobs_raw = await aptos_client.view(payload)
        # Assuming you have a parser or that your Pydantic model matches
        return jobs_raw[0] 
    except Exception as e:
        logging.error(f"Failed to fetch jobs for renter {renter_address}", exc_info=True)
        return []