import pytest, typing as t, httpx, sqlmodel as sqlm, asyncio
import pytest_asyncio as pytestaio
from sqlalchemy import event, NullPool
from functools import partial
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
import app.infrastructure.dependencies as ideps
import app.application.dependencies as adeps
import app.main as main
from app.common.config import Config


import logging
logger = logging.getLogger('app')


@pytestaio.fixture(scope='session')
async def db_engine() -> t.AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(Config.DB_URL, **Config.DB_KWARGS)
    yield engine
    await engine.dispose()

@pytestaio.fixture(scope="session", autouse=True)
async def setup_database(db_engine: AsyncEngine):
    async with db_engine.begin() as conn:
        await conn.run_sync(sqlm.SQLModel.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(sqlm.SQLModel.metadata.drop_all)

@pytestaio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> t.AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            print(f'Exception caught in db_session fixture: {e}')
        finally:
            await session.rollback() 

@pytestaio.fixture(scope='function')
async def cache_manager():
    mgr = ideps.CacheManagerType(cache_pool=False, **ideps.cache_args)
    async with mgr.connect() as client:
        yield client
    
@pytestaio.fixture(scope='function')
async def cache_client(cache_manager: ideps.CacheManagerType) -> t.AsyncGenerator[ideps.CacheConnectionType, None]:
    return cache_manager

@pytestaio.fixture(scope='function', autouse=True)
async def clear_cache():
    yield 
    mgr = ideps.CacheManagerType(cache_pool=False, **ideps.cache_args)
    await mgr.flush_data()


@pytestaio.fixture(scope="function")
async def uow(db_session: AsyncSession) -> t.AsyncIterator[ideps.UnitOfWork]:
    yield ideps.UnitOfWork(db_session)
        



async def build_user_repo(uow: ideps.UnitOfWork, cache_client: ideps.CacheConnectionType) -> ideps.UserRepository:
    db = ideps.UserDB(uow.session)
    return ideps.UserRepoDependency(user_db_repo=db, connection=cache_client, uow=uow)


async def build_sess_repo(cache_client: ideps.CacheConnectionType) -> ideps.SessionRepository:
    return ideps.SessionRepository(cache_client)







@pytestaio.fixture(scope='function')
async def async_client(uow: ideps. UnitOfWork, cache_client):
    
    async def override_get_cache():
        return cache_client
    
    async def override_get_uow():
        return uow

    main.app.dependency_overrides[ideps.CacheDependency] = override_get_cache
    main.app.dependency_overrides[ideps.UoWDependency] = override_get_uow
    
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://app:8000/api") as client:
        yield client
        
    del main.app.dependency_overrides[ideps.CacheDependency]
    del main.app.dependency_overrides[ideps.UoWDependency]



