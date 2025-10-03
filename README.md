# AxessProtocol — FastAPI Backend

This is part of a 4 repo project:

SmartContracts: https://github.com/Nishan30/AxessProtocol

Frontend: https://github.com/Nishan30/AxessProtocolFrontend

Backend: https://github.com/aniJani/AxessProtocolBackend

Oracle Agent: https://github.com/aniJani/oracleAgent

A thin caching/API layer for the marketplace dApp. Pulls data from Aptos fullnode REST and exposes clean, paginated endpoints.

## Endpoints
- `GET /healthz`
- `GET /api/v1/listings?limit=20&cursor=0`
- `GET /api/v1/listings/{listing_id}`
- `GET /api/v1/hosts/{host_address}`
- `GET /api/v1/jobs/{job_id}`

## Configure
Copy `.env.example` to `.env` and set module addresses for Marketplace/Escrow once deployed.

## Activate python environment
source .venv/bin/activate      

## Run
```bash
uvicorn app.main:app --reload --port 8000
