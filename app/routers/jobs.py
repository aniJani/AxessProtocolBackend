from fastapi import APIRouter
from typing import Optional
from app.models.schemas import Job
from app.clients.aptos import aptos_client
from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["jobs"])
SET = get_settings()


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: int):
    # Expect a Move view function get_job(job_id) -> Job struct
    payload = {
        "function": f"{SET.APTOS_ESCROW_ADDRESS}::Escrow::get_job",
        "type_arguments": [],
        "arguments": [str(job_id)],
    }
    raw = await aptos_client.view(payload)
    row = raw[0] if isinstance(raw, list) and raw else raw
    if not row:
        raise RuntimeError("Job not found")
    # Map to our schema (adjust field names to match your Move struct layout)
    status = row.get("status", "active")
    return Job(
        id=int(row["id"]),
        renter_address=row["renter_address"],
        host_address=row["host_address"],
        listing_id=int(row["listing_id"]),
        start_time=int(row["start_time"]),
        max_duration_seconds=int(row["max_duration_seconds"]),
        price_per_second=int(row["price_per_second"]),
        total_escrow_amount=int(row["total_escrow_amount"]),
        claimed_amount=int(row.get("claimed_amount", 0)),
        status=status,
    )
