from pydantic import BaseModel, Field
from typing import Literal, Optional, List


class CloudDetails(BaseModel):
    provider: Literal["AWS"]
    instance_id: str
    instance_type: str
    region: str


class PhysicalSpecs(BaseModel):
    gpu_model: str
    cpu_cores: int
    ram_gb: int


class Listing(BaseModel):
    id: int
    listing_type: Literal["Cloud", "Physical"]
    cloud: Optional[CloudDetails] = None
    physical: Optional[PhysicalSpecs] = None
    price_per_second: int
    is_available: bool = True
    active_job_id: Optional[int] = None
    host_address: str = Field(..., description="Account that owns the listing")


class ListingsPage(BaseModel):
    items: List[Listing]
    next_cursor: Optional[str] = None
    total: Optional[int] = None


class HostProfile(BaseModel):
    host_address: str
    listings: List[Listing]


class Job(BaseModel):
    id: int
    renter_address: str
    host_address: str
    listing_id: int
    start_time: int
    max_duration_seconds: int
    price_per_second: int
    total_escrow_amount: int
    claimed_amount: int
    status: Literal["active", "terminated", "completed"] = "active"


# These models should mirror the structs in your Move contract
class PhysicalSpecs(BaseModel):
    gpu_model: str
    cpu_cores: int
    ram_gb: int


class CloudDetails(BaseModel):
    provider: str
    instance_id: str
    instance_type: str
    region: str


class Listing(BaseModel):
    host_address: str
    listing_type: str  # "Physical" or "Cloud"
    price_per_second: int
    is_available: bool
    active_job_id: Optional[int] = None
    physical: Optional[PhysicalSpecs] = None
    cloud: Optional[CloudDetails] = None


class ListingsPage(BaseModel):
    items: List[Listing]
    total: int
    next_cursor: Optional[int] = None
