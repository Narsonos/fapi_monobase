#NOTE: Only lines not covered by broader tests are tested here. (probably due to pytest-cov bugs, idk)
import app.infrastructure.dependencies as ideps
import app.infrastructure.exceptions as iexc
import pytest
from redis.exceptions import RedisError
from redis import Redis

@pytest.fixture(scope='function')
def mgr():
    return ideps.RedisConnectionManager(**ideps.cache_args)

@pytest.mark.asyncio
async def test_redis_manager_connect(mgr: ideps.RedisConnectionManager):
    with pytest.raises(iexc.CustomStorageException):
        async with mgr.connect() as conn:
            raise RedisError
    
    async with mgr.connect() as conn:
        pong = await conn.ping()
        assert pong is not None

@pytest.mark.asyncio
async def test_redis_manager_close(mgr: ideps.RedisConnectionManager):
    async with mgr.connect() as conn:
        pong = await conn.ping()
        assert pong is not None
    await mgr.close()
    assert mgr._pool == None


@pytest.mark.asyncio
async def test_redis_wait_for_startup(mgr: ideps.RedisConnectionManager):
    await mgr.wait_for_startup()
    assert mgr._pool is not None
    #giving bad connection data to enforce error
    with pytest.raises(iexc.StorageBootError):
        mgr2 = ideps.RedisConnectionManager(host="localhost",port=63729,password='231231231',decode_responses=True,db=0)
        await mgr2.wait_for_startup(attempts=2, interval_sec=1)


@pytest.mark.asyncio
async def test_redis_initializer(mgr: ideps.RedisConnectionManager):
    #at the moment it does nothing but its nothing, yet its not 
    #a case of breaking 
    assert await mgr.initialize_data_structures() == None 

@pytest.mark.asyncio
async def test_redis_flush(mgr: ideps.RedisConnectionManager):
    
    async with mgr.connect() as conn:
        await conn.set('test','123')
        await mgr.flush_data(conn) #can use pooled client
        assert await conn.get('test') == None
    await mgr.flush_data() #can pool a client by itself
    await mgr.close()

    with pytest.raises(iexc.StorageNotInitialzied):
        await mgr.flush_data()
    

