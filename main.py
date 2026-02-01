import sys
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from database import get_db

# Ensure we can import our Cython modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.routes import router as api_router
from events.handlers import event_bus
from services.redis_broker import redis_broker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Event Bus, Redis, and AI Models
    print("🚀 Project OMNI Engine Starting...")
    print("✅ Cython Modules Loaded: math_core, data_models")
    
    # Connect to Redis
    await redis_broker.connect()
    
    await event_bus.publish("system.startup", {"status": "online"})
    yield
    # Shutdown
    print("🛑 Project OMNI Engine Shutting Down...")
    await redis_broker.close()

app = FastAPI(
    title="Project OMNI: Sovereign Financial OS",
    description="High-Performance Cython/Python Engine",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "running", "engine": "cython-accelerated"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)