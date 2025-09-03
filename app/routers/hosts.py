import logging
from typing import List
from fastapi import APIRouter, HTTPException

# Import your existing components
from app.models.schemas import HostProfile, Listing
from app.clients.aptos import aptos_client
from app.config import get_settings
# IMPORTANT: We will reuse the parser from your listings router
from .listings import _parse_raw_listing 

router = APIRouter(prefix="/api/v1", tags=["hosts"])
SET = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

@router.get("/hosts/{host_address}/listings", response_model=List[Listing])
async def get_host_listings(host_address: str) -> List[Listing]:
    """
    More efficiently retrieves all machine listings for a specific host by
    directly querying their on-chain ListingManager resource.
    """
    logging.info(f"Fetching listings for host: {host_address}")
    try:
        # Define the resource type we are looking for
        resource_type = f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::ListingManager"
        
        # Directly query the account resource for the host
        response = await aptos_client.account_resource(host_address, resource_type)
        
        # The listings are nested within the 'data' field
        listings_data = response.get("data", {}).get("listings", [])
        
        # Parse each raw listing using your existing helper function
        parsed_listings = [
            _parse_raw_listing(raw_listing, host_address) for raw_listing in listings_data
        ]
        
        return parsed_listings

    except Exception as e:
        # This is the expected error if the host has never listed a machine
        if "Resource not found" in str(e):
            logging.warning(f"ListingManager not found for host {host_address}. Returning empty list.")
            return [] # Return an empty list, which is valid for the response model
        
        # For all other errors, raise a 500
        logging.error(f"Failed to fetch listings for host {host_address}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while fetching on-chain data."
        )

# Remove or comment out the old get_host function if you no longer need the HostProfile model
# @router.get("/hosts/{host_address}", response_model=HostProfile) ...