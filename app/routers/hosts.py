from fastapi import APIRouter
from typing import List
from app.models.schemas import HostProfile, Listing
from .listings import _fetch_all_listings

router = APIRouter(prefix="/api/v1", tags=["hosts"])


@router.get("/hosts/{host_address}", response_model=HostProfile)
async def get_host(host_address: str):
    items: List[Listing] = await _fetch_all_listings()
    mine = [it for it in items if it.host_address.lower() == host_address.lower()]
    return HostProfile(host_address=host_address, listings=mine)
