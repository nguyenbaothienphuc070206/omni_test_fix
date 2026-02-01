import asyncio
import json
from typing import Dict, List, Callable, Any
from services.redis_broker import redis_broker

class EventBus:
    """
    Lightweight Async Event Bus for Project OMNI.
    Decouples Ingestion, Validation, and AI Logic.
    Supports Redis Pub/Sub if available.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Any):
        # 1. Internal Handlers (In-Memory)
        if event_type in self.subscribers:
            callbacks = [handler(payload) for handler in self.subscribers[event_type]]
            await asyncio.gather(*callbacks)
            
        # 2. External Broker (Redis)
        # We serialize payload to JSON for the broker
        if redis_broker.client:
            try:
                message = json.dumps(payload)
                await redis_broker.publish(event_type, message)
            except Exception as e:
                print(f"Failed to publish to Redis: {e}")

# Global singleton
event_bus = EventBus()

# --- Standard Handlers ---

async def on_startup(payload):
    print(f"[Event] System Startup: {payload}")

async def on_transaction_validated(payload):
    # This is where we would trigger Phase 4 (PoI) or Phase 3 (Sharding)
    pass

# Register default handlers
event_bus.subscribe("system.startup", on_startup)
