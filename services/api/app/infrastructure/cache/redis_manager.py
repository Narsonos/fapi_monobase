from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs
from redis.asyncio import ConnectionPool, Redis

import logging, asyncio, contextlib, typing as t




logger = logging.getLogger('app.storage')

class RedisConnectionManager(mgrs.ConnectionManagerInterface[Redis]):
    def __init__(self, cache_pool=True, **redis_kwargs):
        self._redis_kwargs = redis_kwargs
        self._pool = ConnectionPool(**redis_kwargs)
        self._cache_pool = cache_pool

    @contextlib.asynccontextmanager
    async def connect(self) -> t.AsyncIterator[Redis]:
        if self._cache_pool or self._pool is None:
            self._pool = ConnectionPool(**self._redis_kwargs)
        client = Redis(connection_pool=self._pool)
        try:
            yield client
        except Exception as e:
            raise exc.CustomStorageException(f'Redis got exception: {e}')
        finally:
            await client.aclose()
    
    async def close(self):
        if self._pool:
            logger.info('[Storage: Redis] Closing connection pool!')
            await self._pool.disconnect(inuse_connections=True)
            self._pool = None


    async def wait_for_startup(self, attempts:int = 5, interval_sec: int = 5):
            retries = 0
            while retries < attempts:
                try:
                    async with self.connect() as redis:
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
        if not self._pool:
            raise exc.StorageNotInitialzied(f'Redis pool closed! Value={self._pool}. Recreate the manage or pool')
        async with self.connect() as redis:
            await redis.flushall()
