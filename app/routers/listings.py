from fastapi import APIRouter, Depends, Query
from app.clients.aptos import aptos_client, MARKETPLACE_LISTING_TYPE
from app.cache.memory_cache import cache_get, cache_set
from app.models.schemas import CloudDetails, Listing, ListingsPage, PhysicalSpecs
from app.utils.pagination import paginate
from app.config import get_settings
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["listings"])

SET = get_settings()


# async def _fetch_all_listings() -> List[Listing]:
#     # For hackathon demo, you might keep an index of known host addresses in a view function.
#     # Here we expect a Move `view` that returns a vector of (host_address, listing struct)
#     cache_key = "all_listings_v1"
#     cached = cache_get(cache_key)
#     if cached is not None:
#         return cached

#     # Example view payload stub — replace with your real view function
#     payload = {
#         "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::Marketplace::get_all_listings",
#         "type_arguments": [],
#         "arguments": [],
#     }
#     try:
#         raw = await aptos_client.view(payload)
#     except Exception:
#         raw = []

#     items: List[Listing] = []
#     for row in raw:
#         # Expect: row = { id, host_address, listing_type, price_per_second, is_available, active_job_id, details{...} }
#         lt = row.get("listing_type")
#         details = row.get("details", {})
#         items.append(
#             Listing(
#                 id=int(row["id"]),
#                 host_address=row["host_address"],
#                 listing_type=lt,
#                 price_per_second=int(row["price_per_second"]),
#                 is_available=bool(row.get("is_available", True)),
#                 active_job_id=(
#                     int(row["active_job_id"])
#                     if row.get("active_job_id") is not None
#                     else None
#                 ),
#                 cloud=details if lt == "Cloud" else None,
#                 physical=details if lt == "Physical" else None,
#             )
#         )
#     cache_set(cache_key, items)
#     return items


async def _fetch_all_listings() -> List[Listing]:
    """
    Fetches all listings with the final parser and a fix for the
    'list index out of range' error on active_job_id.
    """
    cache_key = "all_listings_v1"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    KNOWN_HOSTS = [SET.APTOS_MARKETPLACE_ADDRESS]
    items: List[Listing] = []

    for host_address in KNOWN_HOSTS:
        try:
            resource = await aptos_client.get_resource(
                account=host_address,
                typ=MARKETPLACE_LISTING_TYPE,
            )

            if resource is None:
                print(f"[DEBUG] No listing resource found for host {host_address}. Skipping.")
                continue

            # --- NEW DEBUG LOG ---
            print(f"[DEBUG] Raw resource fetched from API: {resource}")

            raw_listing = resource.get("data", {})
            if not raw_listing:
                continue

            # --- NEW DEBUG LOG ---
            print(f"[DEBUG] Extracted 'data' field: {raw_listing}")

            listing_type_data = raw_listing.get("listing_type", {})
            listing_type = None
            physical_details = None
            cloud_details = None

            variant = listing_type_data.get("__variant__")

            if variant == "Physical":
                listing_type = "Physical"
                physical_details = PhysicalSpecs(**listing_type_data.get("_0", {}))
            elif variant == "Cloud":
                listing_type = "Cloud"
                cloud_details = CloudDetails(**listing_type_data.get("_0", {}))
            
            # --- THE CRITICAL BUG FIX IS HERE ---
            active_job_id_data = raw_listing.get("active_job_id", {}).get("vec", [])
            
            # --- NEW DEBUG LOG ---
            print(f"[DEBUG] 'active_job_id' vector data: {active_job_id_data}")

            # If the vector is not empty, get the first element. Otherwise, it's None.
            active_job_id = int(active_job_id_data[0]) if active_job_id_data else None
            # --- END OF BUG FIX ---

            if listing_type:
                items.append(
                    Listing(
                        host_address=raw_listing["host"],
                        listing_type=listing_type,
                        price_per_second=int(raw_listing["price_per_second"]),
                        is_available=raw_listing["is_available"],
                        active_job_id=active_job_id,
                        physical=physical_details,
                        cloud=cloud_details,
                    )
                )
                print(f"[SUCCESS] Successfully parsed and added listing for host {host_address}")

        except Exception as e:
            # This will now give us a much more detailed error trace
            import traceback
            print(f"[!!!] AN UNEXPECTED ERROR OCCURRED for host {host_address}:")
            traceback.print_exc()
            continue

    cache_set(cache_key, items)
    return items


@router.get("/listings", response_model=ListingsPage)
async def list_listings(
    limit: int = Query(20, ge=1, le=100), cursor: Optional[int] = Query(None)
):
    items = await _fetch_all_listings()
    page, next_cursor = paginate(items, limit=limit, cursor=cursor)
    return ListingsPage(items=page, next_cursor=next_cursor, total=len(items))


@router.get("/listings/{listing_id}", response_model=Listing)
async def get_listing(listing_id: int):
    items = await _fetch_all_listings()
    for it in items:
        if it.id == listing_id:
            return it
    # Fallback: optionally query a view like get_listing_by_id
    raise RuntimeError("Listing not found")
