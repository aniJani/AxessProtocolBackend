from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    APTOS_NODE_URL: str = os.getenv(
        "APTOS_NODE_URL", "https://fullnode.testnet.aptoslabs.com/v1"
    )
    APTOS_MARKETPLACE_ADDRESS: str = os.getenv(
        "APTOS_MARKETPLACE_ADDRESS",
        "0xc6cb811e72af6ce5036b2d8812536ce2fd6213a403a892a8b6b7154443da19ba",
    )
    APTOS_ESCROW_ADDRESS: str = os.getenv("APTOS_ESCROW_ADDRESS", "0x...escrow")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    REDIS_URL: str | None = os.getenv("REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
