import logging
from fastapi import APIRouter, HTTPException

# Import the necessary components
from app.models.schemas import Listing  # The Pydantic model for the response
from app.clients.aptos import aptos_client
from app.config import get_settings

# --- THE FIX: Import the NEW, CORRECT parser from the updated listings.py ---
# Note: Ensure that the parser in your listings.py is named `_parse_listing_view`
# and is available for import (i.e., not nested inside another function).
from .listings import _parse_listing_view

router = APIRouter(prefix="/api/v1", tags=["hosts"])
SET = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')


# --- REFACTORED: The endpoint now gets a single listing, not a list ---
@router.get("/hosts/{host_address}", response_model=Listing)
async def get_host_listing(host_address: str):
    """
    Gets the single, unified listing for a specific host by calling
    the on-chain 'get_listing_view' function. This is used by the Host Dashboard.
    """
    logging.info(f"Fetching listing details for host: {host_address}")
    try:
        # Create the payload to call the new view function from your contract
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listing_view",
            "type_arguments": [],
            "arguments": [host_address],
        }
        
        # Call the view function
        response = await aptos_client.view(payload)

        # The view function returns a list with one item (the ListingView struct)
        # or an empty list if the host is not registered.
        if not response or not response[0]:
            raise HTTPException(status_code=44, detail="Host is not registered or has no listing.")

        listing_view_data = response[0]
        
        # Use the correct, existing parser from listings.py to transform the data
        return _parse_listing_view(listing_view_data, host_address)

    except Exception as e:
        # Handle errors gracefully
        if isinstance(e, HTTPException):
            raise e
        logging.error(f"Failed to fetch listing for host {host_address}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching host listing data.")