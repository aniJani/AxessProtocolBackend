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
    """
    try:
        payload = {
            "function": f"{SET.APTOS_MARKETPLACE_ADDRESS}::reputation::get_host_reputation",
            "type_arguments": [],
            "arguments": [host_address],
        }
        # This view function returns an Option<ReputationScore>, which is a list with 0 or 1 elements
        response = await aptos_client.view(payload)
        if response and response[0]:
            # The data is inside the 'vec'[0] for an Option::Some
            return response[0]['vec'][0]
        return None
    except Exception as e:
        logging.error(f"Failed to fetch reputation for {host_address}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching reputation data.")