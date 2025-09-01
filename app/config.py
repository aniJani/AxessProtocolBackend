from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    APTOS_NODE_URL: str = os.getenv(
        "APTOS_NODE_URL", "https://fullnode.testnet.aptoslabs.com/v1"
    )
    APTOS_MARKETPLACE_ADDRESS: str = os.getenv(
        "APTOS_MARKETPLACE_ADDRESS",
        "0x04f63c38cdaa0b8a1e736ebf794844aaabf4f08414d4a26767ee690b7283f758",
    )
    APTOS_ESCROW_ADDRESS: str = os.getenv("APTOS_ESCROW_ADDRESS", "0x...escrow")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    REDIS_URL: str | None = os.getenv("REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
