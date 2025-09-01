from fastapi import APIRouter, Depends, Query
from app.clients.aptos import aptos_client, MARKETPLACE_LISTING_TYPE
from app.cache.memory_cache import cache_get, cache_set
from app.models.schemas import Listing, ListingsPage
from app.utils.pagination import paginate
from app.config import get_settings
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["listings"])

SET = get_settings()


async def _fetch_all_listings() -> List[Listing]:
    # For hackathon demo, you might keep an index of known host addresses in a view function.
    # Here we expect a Move `view` that returns a vector of (host_address, listing struct)
    cache_key = "all_listings_v1"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # Example view payload stub — replace with your real view function
    payload = {
        "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::Marketplace::get_all_listings",
        "type_arguments": [],
        "arguments": [],
    }
    try:
        raw = await aptos_client.view(payload)
    except Exception:
        raw = []

    items: List[Listing] = []
    for row in raw:
        # Expect: row = { id, host_address, listing_type, price_per_second, is_available, active_job_id, details{...} }
        lt = row.get("listing_type")
        details = row.get("details", {})
        items.append(
            Listing(
                id=int(row["id"]),
                host_address=row["host_address"],
                listing_type=lt,
                price_per_second=int(row["price_per_second"]),
                is_available=bool(row.get("is_available", True)),
                active_job_id=(
                    int(row["active_job_id"])
                    if row.get("active_job_id") is not None
                    else None
                ),
                cloud=details if lt == "Cloud" else None,
                physical=details if lt == "Physical" else None,
            )
        )
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
