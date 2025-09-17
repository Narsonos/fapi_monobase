from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs
from redis.asyncio.client import Redis

import logging, asyncio




logger = logging.getLogger('app.storage')

class RedisConnectionManager(mgrs.ConnectionManagerInterface[Redis]):
    def __init__(self, **redis_kwargs):
        self.client = Redis(**redis_kwargs)

    def connect(self) -> Redis:
        return self.client
    
    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None

    async def wait_for_startup(self, attempts:int = 5, interval_sec: int = 5):
        retries = 0
        redis = await self.connect()
        while retries < attempts:
            try:
                pong = await redis.ping()
                if pong:
                    logger.info("[WAIT FOR REDIS] PONG received -> Redis is ready!")
                    return
            except Exception as e:
                logger.debug(e)
                logger.info(f"[WAIT FOR REDIS] Redis not ready yet, retrying ({retries}/{attempts})...")
                retries += 1
                await asyncio.sleep(interval_sec)

        logger.error(f"[WAIT FOR REDIS] Redis failed to respond after {attempts} attempts")
        raise exc.StorageBootError(f"Redis failed to boot within {retries * interval_sec} sec!")


    async def initialize_data_structures(self):
        """
        Optional initialization of key structures.
        Example: setting default counters, roles, or TTL keys.
        """
        return None