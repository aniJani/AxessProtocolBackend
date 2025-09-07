import logging
import asyncio
from typing import List
from fastapi import APIRouter, HTTPException

from app.models.schemas import Job
from .jobs import get_job_details
# --- IMPORT THE LISTING FETCHER ---
from .listings import _fetch_all_listings 

router = APIRouter(prefix="/api/v1", tags=["renters"])

@router.get("/renters/{renter_address}/jobs", response_model=List[Job])
async def get_jobs_for_renter(renter_address: str):
    """
    Finds a renter's jobs by fetching all listings, finding the active jobs,
    and then filtering by the renter's address.
    
    NOTE: This is a functional but less scalable approach than using an indexer.
    It is suitable for a demo or early-stage application.
    """
    logging.info(f"Fetching jobs for renter: {renter_address} by scanning all listings.")
    renter_address_lower = renter_address.lower()
    
    try:
        # 1. Fetch all listings on the entire marketplace.
        all_listings = await _fetch_all_listings()

        # 2. Find all the job IDs from listings that are currently rented.
        active_job_ids = []
        for listing in all_listings:
            if not listing.is_available and listing.active_job_id is not None:
                active_job_ids.append(listing.active_job_id)

        if not active_job_ids:
            return [] # No rented machines means no active jobs.

        # 3. Fetch the details for all those active jobs in parallel.
        job_promises = [get_job_details(job_id) for job_id in active_job_ids]
        job_results = await asyncio.gather(*job_promises, return_exceptions=True)

        # 4. Filter the results to find jobs that belong to the target renter.
        renter_jobs = []
        for job in job_results:
            if not isinstance(job, Exception) and job.renter_address.lower() == renter_address_lower:
                renter_jobs.append(job)
        
        # This will return a list of the renter's ACTIVE jobs.
        # It won't show their rental history yet.
        return renter_jobs

    except Exception as e:
        logging.error(f"Error fetching jobs for renter {renter_address}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve renter jobs.")