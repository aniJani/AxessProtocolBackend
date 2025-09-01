from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx
from loguru import logger
from app.config import get_settings

SET = get_settings()

# Types stored on-chain (adjust to your deployed module addresses)
MARKETPLACE_LISTING_TYPE = f"{SET.APTOS_MARKETPLACE_ADDRESS}::Marketplace::Listing"
JOB_TYPE = f"{SET.APTOS_ESCROW_ADDRESS}::Escrow::Job"


class AptosClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or SET.APTOS_NODE_URL
        self.http = httpx.AsyncClient(base_url=self.base_url, timeout=10)

    async def get_account_resources(self, account: str) -> List[Dict[str, Any]]:
        url = f"/accounts/{account}/resources"
        r = await self.http.get(url)
        r.raise_for_status()
        return r.json()

    async def get_resource(self, account: str, typ: str) -> Optional[Dict[str, Any]]:
        url = f"/accounts/{account}/resource/{typ}"
        r = await self.http.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    async def view(self, payload: Dict[str, Any]) -> Any:
        # Aptos view functions endpoint
        r = await self.http.post("/view", json=payload)
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self.http.aclose()


aptos_client = AptosClient()
