from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from app.clients.aptos import aptos_client
from app.config import get_settings
from app.models.schemas import Listing, ListingsPage, PhysicalSpecs, CloudDetails
from app.utils.pagination import paginate
from app.cache.memory_cache import (
    cache_get,
    cache_set,
)

# Basic Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

router = APIRouter(prefix="/api/v1", tags=["listings"])
SET = get_settings()


def _parse_raw_listing(raw_listing: dict, host_address: str) -> Listing:
    """
    A helper function to transform raw on-chain data into our Pydantic model.
    This version is corrected based on the actual log output.
    """
    listing_type_data = raw_listing.get("listing_type", {})

    listing_type = None
    physical_details = None
    cloud_details = None

    # --- THE FIX ---
    # 1. Get the variant name from the '__variant__' key.
    variant_name = listing_type_data.get('__variant__')

    # 2. Check the variant name and parse the data from the '_0' key.
    if variant_name == "Physical":
        listing_type = "Physical"
        # The data for the Physical variant is in the '_0' field
        physical_data = listing_type_data.get('_0', {})
        if physical_data:
            physical_details = PhysicalSpecs(**physical_data)
    elif variant_name == "Cloud":
        listing_type = "Cloud"
        # The data for the Cloud variant would also be in the '_0' field
        cloud_data = listing_type_data.get('_0', {})
        if cloud_data:
            cloud_details = CloudDetails(**cloud_data)
    # --- END FIX ---

    active_job_id_data = raw_listing.get("active_job_id", {}).get("vec", [])
    active_job_id = int(active_job_id_data[0]) if active_job_id_data else None

    if not listing_type:
        raise ValueError("Could not parse listing type from raw data")

    return Listing(
        id=int(raw_listing["id"]),
        host_address=host_address,
        listing_type=listing_type,
        price_per_second=int(raw_listing["price_per_second"]),
        is_available=raw_listing["is_available"],
        active_job_id=active_job_id,
        physical=physical_details,
        cloud=cloud_details,
    )


async def _fetch_all_listings() -> List[Listing]:
    """
    Fetches all listings by calling the `get_listings_by_host` view function
    for a list of known hosts.
    """
    cache_key = "all_listings_v2"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    KNOWN_HOSTS = [SET.APTOS_MARKETPLACE_ADDRESS]
    items: List[Listing] = []

    for host_address in KNOWN_HOSTS:
        try:
            payload = {
                "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listings_by_host",
                "type_arguments": [],
                "arguments": [host_address],
            }
            host_listings_raw_payload = await aptos_client.view(payload)
            host_listings_raw = host_listings_raw_payload[0]

            for raw_listing in host_listings_raw:
                parsed_listing = _parse_raw_listing(raw_listing, host_address)
                items.append(parsed_listing)

        except Exception as e:
            logging.error(f"Could not fetch listings for host {host_address}", exc_info=True)
            continue

    cache_set(cache_key, items)
    return items


@router.get("/listings", response_model=ListingsPage)
async def list_listings(
    limit: int = Query(20, ge=1, le=100), cursor: Optional[int] = Query(None)
):
    """Lists all available compute listings with pagination."""
    items = await _fetch_all_listings()
    page, next_cursor = paginate(items, limit=limit, cursor=cursor)
    return ListingsPage(items=page, next_cursor=next_cursor, total=len(items))


@router.get("/listings/{host_address}/{listing_id}", response_model=Listing)
async def get_listing(host_address: str, listing_id: int):
    """
    Gets a single listing by its host address and ID using an efficient on-chain view function.
    """
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::marketplace::get_listing_by_id",
            "type_arguments": [],
            "arguments": [host_address, str(listing_id)],
        }
        raw_listing_payload = await aptos_client.view(payload)
        raw_listing = raw_listing_payload[0]
        return _parse_raw_listing(raw_listing, host_address)

    except Exception as e:
        logging.error(f"Failed to get listing {listing_id} for host {host_address}", exc_info=True)
        raise HTTPException(
            status_code=404, detail="Listing not found or error fetching data."
        )