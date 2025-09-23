from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs
from redis.asyncio.client import Redis

import logging, asyncio




logger = logging.getLogger('app.storage')

class RedisConnectionManager(mgrs.ConnectionManagerInterface[Redis]):
    def __init__(self, **redis_kwargs):
        self._redis_kwargs = redis_kwargs
        self.client: Redis | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> Redis:
        if self.client is None:
            self.client = Redis(**self._redis_kwargs)
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # no running loop (shouldn't happen in normal async use), leave None
                self._loop = None
        return self.client
    
    async def close(self):
        if self.client:
            # ensure we close on the loop where client was created
            if self._loop is None:
                await self.client.aclose()
            else:
                if asyncio.get_event_loop() is self._loop:
                    await self.client.aclose()
                else:
                    fut = asyncio.run_coroutine_threadsafe(self.client.aclose(), self._loop)
                    await asyncio.wrap_future(fut)
            self.client = None
            self._loop = None

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
    
    async def flush_data(self):
        if not self.client:
            return None

        # If we're on the same loop where client was created, call directly.
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._loop is None or current_loop is self._loop:
            await self.client.flushall()
        else:
            # schedule flushall on the original loop and await completion
            fut = asyncio.run_coroutine_threadsafe(self.client.flushall(), self._loop)
            await asyncio.wrap_future(fut)