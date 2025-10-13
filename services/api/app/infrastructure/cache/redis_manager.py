from app.common.config import Config
import app.infrastructure.exceptions as exc
import app.infrastructure.interfaces as mgrs
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError
import logging, asyncio, contextlib, typing as t




logger = logging.getLogger('app')

class RedisConnectionManager(mgrs.ConnectionManagerInterface[Redis]):
    def __init__(self, **redis_kwargs):
        self._redis_kwargs = redis_kwargs
        self._pool = ConnectionPool(**redis_kwargs)
        self._client: Redis | None = None

    @contextlib.asynccontextmanager
    async def connect(self) -> t.AsyncIterator[Redis]:
        if self._pool is None:
            self._pool = ConnectionPool(**self._redis_kwargs)
        if self._client is None:
            self._client = Redis(connection_pool=self._pool)
        try:
            yield self._client
        except RedisError as e:
            raise exc.CustomStorageException("Redis got exception!") from e
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
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
                except exc.CustomStorageException as e:
                    logger.debug(e)
                    logger.info(f"[WAIT FOR REDIS] Redis not ready yet, retrying ({retries}/{attempts})...")
                    retries += 1
                    await asyncio.sleep(interval_sec)

            logger.error(f"[WAIT FOR REDIS] Redis failed to respond after {attempts} attempts")
            raise exc.StorageBootError(f"Redis failed to boot within {retries * interval_sec} sec!")


    async def initialize_data_structures(self):
        """
        Initialization of key structures.
        Example: setting default counters, roles, or TTL keys.
        Not used so far, but usage is considered very possible in the future.
        """
        return None
    
    async def flush_data(self, conn: Redis = None):
        if not self._pool:
            raise exc.StorageNotInitialzied(f'Redis pool closed! Value={self._pool}. Recreate the manage or pool')
        if conn:
            await conn.flushall()
            return 
        async with self.connect() as conn:
            await conn.flushall()
