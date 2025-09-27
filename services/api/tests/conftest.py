import pytest, typing as t, httpx, sqlmodel as sqlm, asyncio
import pytest_asyncio as pytestaio
from sqlalchemy.ext.asyncio import create_async_engine,AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker
import app.infrastructure.dependencies as ideps
import app.application.dependencies as adeps
import app.main as main
from app.common.config import Config
import app.domain.models as dmod

import logging
logger = logging.getLogger('app')

#
# RULE: You cannot AWAIT session scoped objects or o
#


@pytestaio.fixture(scope='session')
async def database_manager() -> t.AsyncGenerator[ideps.DatabaseManagerType, None]:
    mgr = ideps.DatabaseManagerType(Config.DB_URL, Config.DB_KWARGS)
    yield mgr
    await mgr.close()

@pytestaio.fixture(scope="session", autouse=True)
async def setup_database(database_manager: ideps.DatabaseManagerType):
    await database_manager.initialize_data_structures()
    yield
    await database_manager.flush_data()

@pytestaio.fixture(scope="function")
async def db_session(database_manager: ideps.DatabaseManagerType) -> t.AsyncGenerator[ideps.DatabaseManagerType, None]:
    async with database_manager._engine.connect() as connection:
        trans = await connection.begin()

        async with database_manager.session(bind=connection) as session:
            try:
                yield session 
            finally:
                await trans.rollback()  
                await session.close()
            
@pytestaio.fixture(scope='session')
async def cache_manager():
    mgr = ideps.CacheManagerType(cache_pool=True, **ideps.cache_args)
    yield mgr
    await mgr.close()
    
@pytestaio.fixture(scope='function')
async def cache_client(cache_manager: ideps.CacheManagerType) -> t.AsyncGenerator[ideps.CacheConnectionType, None]:
    async with cache_manager.connect() as client:
        yield client
        #Can't use yielded client anymore since its bound to test event loop by first await
        async with cache_manager.connect() as cleaner:
            await cleaner.flushall()

@pytestaio.fixture(scope="function")
async def uow(db_session: AsyncSession) -> t.AsyncIterator[ideps.UnitOfWork]:
    yield ideps.UnitOfWork(db_session)
        



async def build_user_repo(uow: ideps.UnitOfWork, cache_client: ideps.CacheConnectionType) -> ideps.UserRepository:
    db = ideps.UserDB(uow.session)
    return ideps.UserRepoDependency(user_db_repo=db, connection=cache_client, uow=uow)


async def build_sess_repo(cache_client: ideps.CacheConnectionType) -> ideps.SessionRepository:
    return ideps.SessionRepository(cache_client)


async def create_user(user_repo, uow, username='admin', password='password', id=555):
    user = dmod.User.create(
        username=username,
        password=password,
        role=dmod.Role.ADMIN.value,
        hasher=ideps.PasswordHasherType(),
    )
    user.id = id
    await user_repo.create(user)
    await uow.commit()

async def create_several_users(user_repo, uow):
    hasher = ideps.PasswordHasherType()
    users = [
        dmod.User.create('test1','12341234', dmod.Role.USER.value, hasher),
        dmod.User.create('test2','12341234', dmod.Role.ADMIN.value, hasher),
        dmod.User.create('test3','12341234', dmod.Role.USER.value, hasher),
    ]
    users[2].set_status('deactivated')
    for user in users:
        await user_repo.create(user)
    await uow.commit()




@pytestaio.fixture(scope='function')
async def async_client(uow: ideps. UnitOfWork, cache_client):
    
    async def override_get_cache():
        return cache_client
    
    async def override_get_uow():
        return uow

    main.app.dependency_overrides[ideps.get_cache] = override_get_cache
    main.app.dependency_overrides[ideps.get_uow] = override_get_uow
    
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://app:8000/api") as client:
        yield client
        
    del main.app.dependency_overrides[ideps.get_cache]
    del main.app.dependency_overrides[ideps.get_uow]



