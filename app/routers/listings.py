import logging
import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

# --- IMPORT THE CONNECTION MANAGER ---
from app.websockets import connection_manager
from app.clients.aptos import aptos_client
from app.config import get_settings
# --- Ensure your Pydantic models match the new contract ---
from app.models.schemas import Listing, ListingsPage, PhysicalSpecs 
from app.utils.pagination import paginate

# Basic Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

router = APIRouter(prefix="/api/v1", tags=["listings"])
SET = get_settings()


# --- NEW PARSER for the 'ListingView' struct ---
def _parse_listing_view(listing_view_data: dict, host_address: str) -> Listing:
    """
    A new parser for the single 'ListingView' resource model.
    It translates the raw on-chain JSON structure into our clean Pydantic model.
    """
    listing_type_data = listing_view_data.get("listing_type", {})
    
    listing_type_str: Optional[str] = None
    physical_details: Optional[PhysicalSpecs] = None
    # CloudDetails would be handled similarly if you add it back to the contract
    
    variant_name = listing_type_data.get('__variant__')
    variant_data = listing_type_data.get('_0', {})

    if variant_name == "Physical" and variant_data:
        listing_type_str = "Physical"
        physical_details = PhysicalSpecs(**variant_data)
    
    if not listing_type_str:
        raise ValueError(f"Could not parse listing_type for host {host_address}")

    active_job_id_vec = listing_view_data.get("active_job_id", {}).get("vec", [])
    active_job_id = int(active_job_id_vec[0]) if active_job_id_vec else None

    # This assumes your Pydantic Listing model in schemas.py has been updated
    # to match the new `Listing` struct (e.g., no `id`, has `is_rented`).
    return Listing(
        host_address=host_address,
        listing_type=listing_type_str,
        price_per_second=int(listing_view_data.get("price_per_second", 0)),
        is_available=listing_view_data.get("is_available", False),
        is_rented=listing_view_data.get("is_rented", True), # Default to rented for safety
        active_job_id=active_job_id,
        physical=physical_details,
        # The ListingView doesn't expose the public key, so we can omit it or
        # fetch the full Listing resource if needed. For the main list, this is fine.
    )


# --- REPLACED: _fetch_all_listings is now _fetch_online_listings ---
async def _fetch_online_listings() -> List[Listing]:
    """
    Fetches listings ONLY from hosts who are currently online.
    It gets the list of online hosts from the WebSocket manager and then
    fetches their on-chain data in parallel.
    """
    # 1. Get the list of agents that are currently connected via WebSocket. This is our liveness check.
    online_host_addresses = list(connection_manager.active_connections.keys())
    
    if not online_host_addresses:
        logging.info("No host agents are currently connected to the backend.")
        return []

    logging.info(f"Found {len(online_host_addresses)} online hosts. Fetching their on-chain listing views...")

    # 2. Create a list of promises to call the `get_listing_view` function for each online host.
    view_promises = [
        aptos_client.view({
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listing_view",
            "type_arguments": [],
            "arguments": [host_addr],
        }) for host_addr in online_host_addresses
    ]

    # 3. Execute all these requests in parallel.
    results = await asyncio.gather(*view_promises, return_exceptions=True)

    # 4. Parse the results and build the final list of listings.
    items: List[Listing] = []
    for i, res in enumerate(results):
        host_address = online_host_addresses[i]
        
        if isinstance(res, Exception) or not res or not res[0]:
            logging.warning(f"Could not fetch listing view for online host {host_address}. They may not be registered yet.")
            continue

        listing_view_data = res[0]
        
        # We only show listings that are both online (WebSocket connected) AND
        # have explicitly marked themselves as available on-chain.
        if listing_view_data.get("is_available"):
            try:
                parsed_listing = _parse_listing_view(listing_view_data, host_address)
                items.append(parsed_listing)
            except Exception as e:
                logging.error(f"Failed to parse listing view for host {host_address}: {e}")
    
    return items


# --- UPDATED: The main /listings endpoint now calls the new fetching logic ---
@router.get("/listings", response_model=ListingsPage)
async def list_listings(
    limit: int = Query(20, ge=1, le=100), cursor: Optional[int] = Query(None)
):
    """
    Lists all available and VERIFIABLY ONLINE compute listings with pagination.
    """
    items = await _fetch_online_listings()
    page, next_cursor = paginate(items, limit=limit, cursor=cursor)
    return ListingsPage(items=page, next_cursor=next_cursor, total=len(items))


# --- REPLACED: The old get_listing endpoint is updated for the new model ---
# It no longer needs a `listing_id`.
@router.get("/listings/{host_address}", response_model=Listing)
async def get_listing_by_host(host_address: str):
    """
    Gets the single listing view for a given host address.
    """
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listing_view",
            "type_arguments": [],
            "arguments": [host_address],
        }
        raw_listing_view_payload = await aptos_client.view(payload)
        
        if not raw_listing_view_payload or not raw_listing_view_payload[0]:
            raise HTTPException(status_code=404, detail="Listing not found for this host.")

        listing_view_data = raw_listing_view_payload[0]
        return _parse_listing_view(listing_view_data, host_address)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logging.error(f"Failed to get listing for host {host_address}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error fetching listing data."
        )