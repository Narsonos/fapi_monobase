from app.common.config import Config
import app.infrastructure.interfaces as mgrs
from redis.asyncio.client import Redis


class RedisConnectionManager(mgrs.ConnectionManagerInterface[Redis]):
    def __init__(self, **redis_kwargs):
        self.client = Redis(**redis_kwargs)

    def connect(self) -> Redis:
        return self.client
    
    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None




