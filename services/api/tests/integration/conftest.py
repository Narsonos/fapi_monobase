import pytest, typing as t, httpx, sqlmodel as sqlm, asyncio
from sqlalchemy import event, NullPool
from functools import partial
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
import app.infrastructure.dependencies as ideps
import app.application.dependencies as adeps
import app.main as main
from app.common.config import Config

@pytest.fixture(scope="session")
async def db_engine() -> t.AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(Config.DB_URL, **Config.DB_KWARGS)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="session", autouse=True)
async def setup_database(db_engine: AsyncEngine):
    async with db_engine.begin() as conn:
        await conn.run_sync(sqlm.SQLModel.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(sqlm.SQLModel.metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> t.AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback() 

@pytest.fixture(scope="function")
async def uow(db_session: AsyncSession) -> t.AsyncIterator[ideps.UnitOfWork]:
    yield ideps.UnitOfWork(db_session)
        
@pytest.fixture(scope='function')
async def cache():
    mgr = ideps.CacheManagerType(**ideps.cache_args)
    yield mgr
    await mgr.flush_data()


@pytest.fixture(scope='function')
async def async_client(cache, uow):
    
    async def override_get_cache():
        #redis must be created by fastapi
        client = await cache.connect()
        return client
    
    async def override_get_uow():
        return uow

    main.app.dependency_overrides[ideps.CacheDependency] = override_get_cache
    main.app.dependency_overrides[ideps.UoWDependency] = override_get_uow
    
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://app:8000/api") as client:
        yield client
        
    del main.app.dependency_overrides[ideps.CacheDependency]
    del main.app.dependency_overrides[ideps.UoWDependency]