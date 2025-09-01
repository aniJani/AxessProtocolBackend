from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    APTOS_NODE_URL: str = os.getenv(
        "APTOS_NODE_URL", "https://fullnode.testnet.aptoslabs.com/v1"
    )
    APTOS_MARKETPLACE_ADDRESS: str = os.getenv(
        "APTOS_MARKETPLACE_ADDRESS",
        "0x3fb9d35ce83b7cc58d9b3202eaf58dc4014e569529fea6b62750f5f4f7d7cf91",
    )
    APTOS_ESCROW_ADDRESS: str = os.getenv("APTOS_ESCROW_ADDRESS", "0x...escrow")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    REDIS_URL: str | None = os.getenv("REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
