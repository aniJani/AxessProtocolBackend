# File: app/routers/renters.py

import logging
from typing import List
from fastapi import APIRouter
from app.models.schemas import Job
from .jobs import get_job_details # We can re-use our existing function

router = APIRouter(prefix="/api/v1", tags=["renters"])

# --- IMPORTANT NOTE ON FETCHING JOBS ---
# The Aptos blockchain does not currently provide a simple way to ask:
# "Give me all jobs created by this renter." Doing so would require an on-chain
# index that we haven't built.
#
# Production Solutions:
# 1. On-Chain: Add a resource to the renter's account that stores a list of their job IDs.
# 2. Off-Chain (Recommended): Use an Aptos Indexer to listen for `rent_machine` events
#    and store the `(renter_address, job_id)` mapping in a traditional database.
#
# For our current demo, we will simulate this by having the frontend tell us
# which job IDs to look up, or we will use a mock list.

# For now, we will keep a simple mock list. The frontend will be updated
# to show how a real implementation would work.
MOCK_RENTER_JOBS = {
    # Replace with a real renter address from your tests
    "0xRENTER_ADDRESS_HERE": [123, 124] 
}

@router.get("/renters/{renter_address}/jobs", response_model=List[Job])
async def get_jobs_for_renter(renter_address: str):
    """
    Fetches the details for all jobs associated with a specific renter.
    (Currently using a mock list of job IDs for the demo).
    """
    logging.info(f"Fetching jobs for renter: {renter_address}")
    
    # In a real system, you would get these IDs from your indexer database.
    job_ids = MOCK_RENTER_JOBS.get(renter_address.lower(), [])
    
    if not job_ids:
        return []

    # Fetch details for each job ID in parallel
    job_details_list = []
    for job_id in job_ids:
        try:
            # Re-use the function we already built!
            job_details = await get_job_details(job_id)
            job_details_list.append(job_details)
        except Exception:
            logging.warning(f"Could not find details for job {job_id} for renter {renter_address}")
            continue
            
    return job_details_list