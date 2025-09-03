import logging
from typing import List
from fastapi import APIRouter, HTTPException

# Import your existing components
from app.models.schemas import Listing # We don't need HostProfile for this endpoint
from app.clients.aptos import aptos_client
from app.config import get_settings
# Reuse the excellent parser from your listings router
from .listings import _parse_raw_listing 

router = APIRouter(prefix="/api/v1", tags=["hosts"])
SET = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

@router.get("/hosts/{host_address}/listings", response_model=List[Listing])
async def get_host_listings(host_address: str) -> List[Listing]:
    """
    Efficiently retrieves all machine listings for a specific host by calling
    the on-chain 'get_listings_by_host' view function.
    """
    logging.info(f"Fetching listings for host: {host_address} using view function.")
    try:
        # --- THE FIX ---
        # Instead of client.account_resource, we use client.view, which you've
        # proven works in your other routers.
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listings_by_host",
            "type_arguments": [],
            "arguments": [host_address], # Pass the host's address to the view function
        }
        
        # This returns a list containing one element: the vector of listings
        host_listings_raw_payload = await aptos_client.view(payload)
        host_listings_raw = host_listings_raw_payload[0]
        # --- END FIX ---
        
        # Parse each raw listing using your existing helper function
        parsed_listings = [
            _parse_raw_listing(raw_listing, host_address) for raw_listing in host_listings_raw
        ]
        
        return parsed_listings

    except Exception as e:
        # If the view function fails (e.g., host has no ListingManager),
        # it might raise an exception. We'll log it and return an empty list.
        logging.error(f"Failed to fetch listings for host {host_address} via view function.", exc_info=True)
        # It's better to return an empty list than a 500 error if the host simply has no listings.
        # However, if it's a different error, a 500 might be appropriate.
        # For a robust solution, you could inspect the error `e` more closely.
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while fetching on-chain data for host."
        )