import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.clients.aptos import aptos_client
from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["reputation"])
SET = get_settings()

class ReputationScore(BaseModel):
    completed_jobs: int
    total_uptime_seconds: int

@router.get("/reputation/{host_address}", response_model=Optional[ReputationScore])
async def get_reputation(host_address: str):
    """
    Fetches the on-chain reputation score for a specific host.
    Correctly handles the case where a host has no reputation yet.
    """
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::reputation::get_host_reputation",
            "type_arguments": [],
            "arguments": [host_address],
        }
        response = await aptos_client.view(payload)

        # --- THE FIX IS HERE ---
        # 1. Check if the response and the nested 'vec' exist and are not empty.
        if response and response[0] and response[0].get('vec') and len(response[0]['vec']) > 0:
            # 2. Only if it's not empty, access the first element.
            return response[0]['vec'][0]
        else:
            # 3. If the host has no reputation (the 'vec' is empty), return None (or null in JSON).
            # This is the correct behavior for an Optional response model.
            return None
        # --- END FIX ---

    except Exception as e:
        logging.error(f"Failed to fetch reputation for {host_address}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching reputation data.")