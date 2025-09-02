from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    APTOS_NODE_URL: str = os.getenv(
        "APTOS_NODE_URL", "https://fullnode.testnet.aptoslabs.com/v1"
    )
    APTOS_MARKETPLACE_ADDRESS: str = os.getenv(
        "APTOS_MARKETPLACE_ADDRESS",
        "0xd144f994fb413c68308e64805774d17ec9703cb4e125dfe19e655ffe209d18b4",
    )
    APTOS_ESCROW_ADDRESS: str = os.getenv("APTOS_ESCROW_ADDRESS", "0x...escrow")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    REDIS_URL: str | None = os.getenv("REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
