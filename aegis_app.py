import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


# Ensure we can import local modules (and optional Cython extensions).
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gateway.endpoints import router as gateway_router
from messaging.dispatch import event_bus
from fabric.bus import redis_broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Architect-OMNI-Ultimate Engine starting...")
    await redis_broker.connect()

    await event_bus.publish("system.startup", {"status": "online"})
    yield

    print("Architect-OMNI-Ultimate Engine shutting down...")
    await redis_broker.close()


app = FastAPI(
    title="Architect-OMNI-Ultimate",
    description="High-performance transaction pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(gateway_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "running", "engine": "Architect-OMNI-Ultimate"}


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
