import os
import redis.asyncio as redis

class RedisBroker:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = None

    async def connect(self):
        try:
            self.client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            await self.client.ping()
            print(f"✅ Connected to Redis at {self.redis_url}")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}. Falling back to in-memory only.")
            self.client = None

    async def publish(self, channel: str, message: str):
        if self.client:
            await self.client.publish(channel, message)

    async def close(self):
        if self.client:
            await self.client.close()

# Singleton
redis_broker = RedisBroker()
