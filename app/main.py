from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from app.routers import health, listings, hosts, jobs
from app.logging_config import logger

app = FastAPI(
    title="Aptos Unified Compute — API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
)

app.include_router(health.router)
app.include_router(listings.router)
app.include_router(hosts.router)
app.include_router(jobs.router)


@app.on_event("startup")
async def on_startup():
    logger.info("FastAPI started.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("FastAPI shutting down.")
